from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from models.schemas import AgentResult

logger = structlog.get_logger()


# 断路器状态枚举
class CircuitBreakerState(str, Enum):
    """电路断路器状态机。"""
    CLOSED = "closed"           # 正常
    OPEN = "open"               # 故障，快速失败
    HALF_OPEN = "half_open"     # 恢复中，允许探测请求


class BaseAgent(ABC):
    """所有Agent基类: 重试、超时、降级处理机制。
    
    特性:
    - 使用 settings 中的动态超时/重试配置
    - 指数退避重试策略: backoff_factor=0.5, max=4s
    - 三态断路器（CLOSED -> OPEN -> HALF_OPEN -> CLOSED）
    """

    def __init__(self, name: str, timeout: float = 10.0):
        settings = get_settings()
        self.name = name
        self.timeout = timeout
        # 从 settings 获取重试配置
        self.max_retries = settings.agent_max_retries
        self.retry_backoff_factor = settings.agent_retry_backoff_factor
        self.retry_backoff_max = settings.agent_retry_backoff_max
        
        self._circuit_breaker_state = CircuitBreakerState.CLOSED
        self._circuit_breaker_enabled = settings.circuit_breaker_enabled
        self._circuit_breaker_threshold = settings.circuit_breaker_failure_threshold
        self._circuit_breaker_window = settings.circuit_breaker_window_seconds
        self._error_timestamps: list[float] = []  # 用于跟踪错误时间窗口
        self._half_open_attempts = 0              # 半开状态下的探测次数
        self._half_open_max_attempts = 3          # 允许最多 3 次探测请求
        self._last_state_change = time.time()     # 上次状态改变时间
        
        # 统计
        self._call_count = 0
        self._error_count = 0

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> AgentResult:
        """核心逻辑，由具体的Agent实现。"""

    async def run(self, **kwargs: Any) -> AgentResult:
        """公共入口: 包装 _execute，添加计时、重试、降级处理。
        
        支持三态断路器，允许系统自愈。
        """
        start = time.perf_counter()
        self._call_count += 1

        # 检查三态断路器
        if self._circuit_breaker_state == CircuitBreakerState.OPEN:
            logger.warning(
                "agent.circuit_breaker_open",
                agent=self.name,
                state=self._circuit_breaker_state,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            return self._fallback(latency_ms, Exception("Circuit breaker OPEN"))
        
        # 半开状态：允许有限的探测请求
        if self._circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            if self._half_open_attempts >= self._half_open_max_attempts:
                logger.warning(
                    "agent.half_open_max_attempts",
                    agent=self.name,
                    attempts=self._half_open_attempts,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                return self._fallback(latency_ms, Exception("Circuit breaker HALF_OPEN, max attempts reached"))

        try:
            result = await self._retry_execute(**kwargs)
            result.latency_ms = (time.perf_counter() - start) * 1000
            
            # 成功请求，尝试关闭断路器
            if self._circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                logger.info(
                    "agent.circuit_breaker_closed",
                    agent=self.name,
                    reason="half_open_probe_succeeded",
                )
                self._circuit_breaker_state = CircuitBreakerState.CLOSED
                self._error_timestamps.clear()
                self._half_open_attempts = 0
            
            logger.info(
                "agent.success",
                agent=self.name,
                latency_ms=round(result.latency_ms, 1),
                state=self._circuit_breaker_state,
            )
            return result
        except Exception as exc:
            self._error_count += 1
            self._error_timestamps.append(time.time())
            
            # 检查是否需要打开断路器
            if self._circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
                self._half_open_attempts += 1
            
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "agent.failed",
                agent=self.name,
                error=str(exc),
                state=self._circuit_breaker_state,
            )
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
        """三态断路器状态机。
        
        状态流转:
          CLOSED -> OPEN (错误达到阈值)
          OPEN -> HALF_OPEN (等待 window_seconds 后)
          HALF_OPEN -> CLOSED (探测请求成功)
          HALF_OPEN -> OPEN (探测请求失败或超过最大尝试次)
        """
        if not self._circuit_breaker_enabled:
            return False
        
        now = time.time()
        
        # 清理时间窗口外的错误记录
        self._error_timestamps = [
            ts for ts in self._error_timestamps
            if now - ts < self._circuit_breaker_window
        ]
        
        # 状态转移逻辑
        if self._circuit_breaker_state == CircuitBreakerState.CLOSED:
            # CLOSED -> OPEN：错误达到阈值
            if len(self._error_timestamps) >= self._circuit_breaker_threshold:
                logger.warning(
                    "agent.circuit_breaker_opened",
                    agent=self.name,
                    error_count=len(self._error_timestamps),
                    threshold=self._circuit_breaker_threshold,
                )
                self._circuit_breaker_state = CircuitBreakerState.OPEN
                self._last_state_change = now
                return True
        
        elif self._circuit_breaker_state == CircuitBreakerState.OPEN:
            # OPEN -> HALF_OPEN：等待足够时间后进入恢复阶段
            if now - self._last_state_change >= self._circuit_breaker_window:
                logger.info(
                    "agent.circuit_breaker_half_open",
                    agent=self.name,
                    wait_seconds=now - self._last_state_change,
                )
                self._circuit_breaker_state = CircuitBreakerState.HALF_OPEN
                self._half_open_attempts = 0
                self._error_timestamps.clear()
                return False  # HALF_OPEN 允许请求通过
            else:
                return True  # 继续保持 OPEN，快速失败
        
        # HALF_OPEN 状态由 run() 方法处理，基于请求结果转移
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
