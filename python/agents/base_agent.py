from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from models.schemas import AgentResult

logger = structlog.get_logger()


class BaseAgent(ABC):
    """所有Agent基类: 重试、超时、降级处理机制。
    
    特性:
    - 使用 settings 中的动态超时/重试配置
    - 指数退避重试策略: backoff_factor=0.5, max=4s
    - 电路断路器计划 (简化版: 跟踪调用计数)
    """

    def __init__(self, name: str, timeout: float = 10.0):
        settings = get_settings()
        self.name = name
        self.timeout = timeout
        # 从 settings 获取重试配置
        self.max_retries = settings.agent_max_retries
        self.retry_backoff_factor = settings.agent_retry_backoff_factor
        self.retry_backoff_max = settings.agent_retry_backoff_max
        
        # 电路断路器状态 (简化版)
        self._call_count = 0
        self._error_count = 0
        self._circuit_breaker_enabled = settings.circuit_breaker_enabled
        self._circuit_breaker_threshold = settings.circuit_breaker_failure_threshold
        self._circuit_breaker_window = settings.circuit_breaker_window_seconds
        self._error_timestamps: list[float] = []  # 用于跟踪错误时间窗口

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> AgentResult:
        """核心逻辑，由具体的Agent实现。"""

    async def run(self, **kwargs: Any) -> AgentResult:
        """公共入口: 包装 _execute，添加计时、重试、降级处理。"""
        start = time.perf_counter()
        self._call_count += 1

        # 检查电路断路器状态
        if self._is_circuit_breaker_open():
            logger.warning("agent.circuit_breaker_open", agent=self.name)
            latency_ms = (time.perf_counter() - start) * 1000
            return self._fallback(latency_ms, Exception("Circuit breaker open"))

        try:
            result = await self._retry_execute(**kwargs)
            result.latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "agent.success",
                agent=self.name,
                latency_ms=round(result.latency_ms, 1),
            )
            return result
        except Exception as exc:
            self._error_count += 1
            self._error_timestamps.append(time.time())
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("agent.failed", agent=self.name, error=str(exc))
            return self._fallback(latency_ms, exc)

    async def _retry_execute(self, **kwargs: Any) -> AgentResult:
        """应用指数退避重试策略 (从 settings 读取参数)."""
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self.retry_backoff_factor,
                min=self.retry_backoff_factor,
                max=self.retry_backoff_max,
            ),
            reraise=True,
        )
        async def _inner():
            return await self._execute(**kwargs)

        return await _inner()

    def _is_circuit_breaker_open(self) -> bool:
        """检查电路断路器是否打开。
        
        规则: 如果时间窗口内错误数 >= 阈值，打开断路器。
        """
        if not self._circuit_breaker_enabled:
            return False
        
        now = time.time()
        # 清理时间窗口外的错误记录
        self._error_timestamps = [
            ts for ts in self._error_timestamps
            if now - ts < self._circuit_breaker_window
        ]
        
        # 检查是否达到阈值
        if len(self._error_timestamps) >= self._circuit_breaker_threshold:
            return True
        return False

    def _fallback(self, latency_ms: float, exc: Exception) -> AgentResult:
        """Agent失败时返回降级结果."""
        return AgentResult(
            agent_name=self.name,
            success=False,
            latency_ms=latency_ms,
            error=str(exc),
            confidence=0.0,
        )

    @property
    def error_rate(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._error_count / self._call_count
