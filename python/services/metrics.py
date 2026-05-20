"""
监控指标收集与 Prometheus 集成
- Prometheus 指标: 请求延迟、QPS、Agent 耗时、错误率、缓存命中率
- 业务事件: CTR / CVR / GMV (采样 + 循环缓冲区)
- A/B 测试指标
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from prometheus_client import Counter, Histogram, REGISTRY, generate_latest

requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
)
request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["endpoint", "method"],
)
agent_duration_seconds = Histogram(
    "agent_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_name"],
)
agent_errors_total = Counter(
    "agent_errors_total",
    "Agent errors by type",
    ["agent_name", "error_type"],
)


class ErrorType(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    EXTERNAL = "external"
    UNKNOWN = "unknown"

    @classmethod
    def categorize(cls, error: str) -> "ErrorType":
        text = error.lower()
        if "timeout" in text or "timed out" in text:
            return cls.TIMEOUT
        if "rate" in text or "429" in text:
            return cls.RATE_LIMIT
        if "validation" in text or "invalid" in text:
            return cls.VALIDATION
        if "http" in text or "connection" in text or "api" in text:
            return cls.EXTERNAL
        return cls.UNKNOWN


cache_hits_total = Counter("cache_hits_total", "Cache hits", ["cache_name"])
cache_misses_total = Counter("cache_misses_total", "Cache misses", ["cache_name"])


@dataclass
class AgentMetric:
    call_count: int = 0
    success_count: int = 0
    total_latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.success_count / self.call_count if self.call_count else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.call_count if self.call_count else 0.0


class MetricsCollector:
    """
    In-memory metrics collector + Prometheus 暴露.
    
    特性:
    - 保留现有业务事件采样机制
    - 循环缓冲区防止内存泄漏 (max_events=1000)
    - 每 100 次请求采样 1 条业务事件
    """

    def __init__(self, max_business_events: int = 1000, sampling_rate: int = 100):
        self._agent_metrics: dict[str, AgentMetric] = defaultdict(AgentMetric)
        # 循环缓冲区: 固定大小，新事件覆盖旧事件
        self._business_events: deque[dict[str, Any]] = deque(maxlen=max_business_events)
        self._sampling_rate = sampling_rate
        self._request_count = 0

    def record_agent_call(self, agent_name: str, success: bool, latency_ms: float, error: str = ""):
        """记录 Agent 调用，同时更新 Prometheus 指标."""
        m = self._agent_metrics[agent_name]
        m.call_count += 1
        if success:
            m.success_count += 1
        m.total_latency_ms += latency_ms
        if error:
            m.errors.append(error)
        
        # 更新 Prometheus
        agent_duration_seconds.labels(agent_name=agent_name).observe(latency_ms / 1000.0)
        if error:
            error_type = ErrorType.categorize(error)
            agent_errors_total.labels(agent_name=agent_name, error_type=error_type.value).inc()

    def record_business_event(self, event_type: str, **kwargs: Any):
        """
        记录业务事件 (CTR/CVR/GMV)。
        
        采样: 每 sampling_rate 次请求记录 1 条事件，防止内存溢出。
        """
        self._request_count += 1
        # 采样：每 N 次请求采 1 次
        if self._request_count % self._sampling_rate == 0:
            self._business_events.append({
                "type": event_type,
                "timestamp": time.time(),
                **kwargs,
            })

    def get_agent_stats(self) -> dict[str, dict[str, Any]]:
        result = {}
        for name, m in self._agent_metrics.items():
            result[name] = {
                "call_count": m.call_count,
                "success_rate": round(m.success_rate, 4),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "recent_errors": m.errors[-5:],
            }
        return result

    def get_business_stats(self) -> dict[str, Any]:
        """返回业务事件统计."""
        if not self._business_events:
            return {}
        by_type: dict[str, list[dict]] = defaultdict(list)
        for e in self._business_events:
            by_type[e["type"]].append(e)
        stats = {}
        for t, events in by_type.items():
            stats[t] = {"count": len(events)}
        return stats

    def get_prometheus_metrics(self) -> bytes:
        """获取 Prometheus 格式的指标数据."""
        return generate_latest(REGISTRY)
