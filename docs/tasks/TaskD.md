# Multi-Agent 电商推荐系统 — 性能优化与可观测性

---

## 目录

1. [优化总览](#1-优化总览)
2. [断路器机制](#2-断路器机制--base_agentpy)
3. [配置外部化](#3-配置外部化--configpy)
4. [LLM 懒加载与本地降级](#4-llm-懒加载与本地降级)
5. [多级缓存体系](#5-多级缓存体系)
6. [正则预编译优化](#6-正则预编译优化--marketing_copy_agentpy)
7. [请求级超时中间件](#7-请求级超时中间件--mainpy)
8. [可观测性与监控集成](#8-可观测性与监控集成--servicesmetricspy--mainpy)
9. [压测体系搭建](#9-压测体系搭建)
10. [优化关联总览](#10-优化关联总览)

---

## 1. 优化总览

| # | 文件 | 类型 | 核心优化 |
|---|------|------|----------|
| 1 | `agents/base_agent.py` | 修改 | 三态断路器、配置外部化、重试参数化 |
| 2 | `config.py` | 修改 | 新增断路器 / 重试 / 缓存 / 指标采样配置项 |
| 3 | `agents/marketing_copy_agent.py` | 修改 | LLM 懒加载、正则预编译、本地 fallback 文案 |
| 4 | `agents/product_rec_agent.py` | 修改 | LLM 懒加载、`lru_cache` 类目缓存、本地 fallback 排序 |
| 5 | `agents/user_profile_agent.py` | 修改 | L1/L2 两级缓存、LLM 懒加载、本地 fallback 画像 |
| 6 | `main.py` | 修改 | 请求超时中间件、Prometheus 计时中间件、`/metrics` 端点 |
| 7 | `services/metrics.py` | 修改 | Prometheus 正式集成、ErrorType 枚举、循环缓冲区采样 |
| 8 | `reports/generate_perf_report.py` | 新增 | Locust JSON → HTML 可视化报告 |
| 9 | `tests/load_test_locust.py` | 新增 | 混合流量压测脚本、P50/P95/P99 采集 |
| 10 | `run_performance_test.sh` | 新增 | 一键压测自动化脚本 |

---

## 2. 断路器机制 — `base_agent.py`

原版 `BaseAgent` 仅有指数退避重试，下游 LLM 或 Redis 持续故障时会产生大量无效重试，拖慢整体响应。

#### 2.1 三态断路器状态机

新增 `CircuitBreakerState` 枚举，定义三种状态：

```
CLOSED（正常）→ OPEN（故障，快速失败）→ HALF_OPEN（恢复探测）→ CLOSED
```

状态转移规则如下：

| 当前状态 | 触发条件 | 目标状态 |
|----------|----------|----------|
| `CLOSED` | 时间窗口内错误数 ≥ 阈值 | `OPEN` |
| `OPEN` | 等待时间 ≥ `window_seconds` | `HALF_OPEN` |
| `HALF_OPEN` | 探测请求成功 | `CLOSED` |
| `HALF_OPEN` | 探测请求失败或超过最大尝试次数（3次） | `OPEN` |

#### 2.2 关键实现

- `_error_timestamps` 滑动时间窗口：只统计最近 `window_seconds` 内的失败，避免历史错误永久累积
- `OPEN` 状态下直接返回 `_fallback()`，跳过重试，响应时间 < 1ms
- `HALF_OPEN` 状态最多允许 3 次探测请求，避免恢复期流量冲击

#### 2.3 配置外部化

原先硬编码 `max_retries=2`、`multiplier=0.5` 等参数，优化后全部从 `settings` 读取：

```python
# 优化前
def __init__(self, name: str, timeout: float = 10.0, max_retries: int = 2):
    ...

# 优化后
def __init__(self, name: str, timeout: float = 10.0):
    settings = get_settings()
    self.max_retries = settings.agent_max_retries
    self.retry_backoff_factor = settings.agent_retry_backoff_factor
    self.retry_backoff_max = settings.agent_retry_backoff_max
```

---

## 3. 配置外部化 — `config.py`

各 Agent 的重试参数、缓存 TTL、断路器阈值等均为硬编码，无法在不重新部署的情况下调整。

#### 3.1 请求级超时 & 重试

```python
request_timeout_seconds: float = 12.0
agent_max_retries: int = 2
agent_retry_backoff_factor: float = 0.5
agent_retry_backoff_max: float = 4.0
```

#### 3.2 断路器

```python
circuit_breaker_enabled: bool = True
circuit_breaker_failure_threshold: int = 3   # 时间窗口内允许的最大失败次数
circuit_breaker_window_seconds: int = 60      # 滑动时间窗口（秒）
```

#### 3.3 缓存配置

```python
cache_user_profile_ttl_seconds: int = 3600   # Redis L2 TTL：1 小时
cache_user_profile_local_ttl_seconds: int = 60  # 本地 L1 TTL：1 分钟
cache_product_recall_ttl_seconds: int = 300  # 产品推荐缓存：5 分钟
cache_local_maxsize: int = 128               # lru_cache 容量上限
```

#### 3.4 指标采样

```python
metrics_business_event_max_size: int = 1000  # 循环缓冲区容量
metrics_business_event_sampling_rate: int = 100  # 每 100 次请求采样 1 条
```

所有配置均支持通过环境变量覆盖（前缀 `ECOM_`），适配容器化部署场景。

---

## 4. LLM 懒加载与本地降级

三个 Agent（`marketing_copy_agent`、`product_rec_agent`、`user_profile_agent`）统一采用相同的降级模式。

### 4.1 LLM 懒加载

开发 / 测试环境无需配置 LLM Key，服务可正常启动并提供降级结果。

```python
# 优化前：无论 API Key 是否配置，始终初始化 LLM 客户端
self.llm = ChatOpenAI(api_key=settings.llm_api_key, ...)

# 优化后：仅在 Key 有效时才初始化
self.llm_enabled = bool(settings.llm_api_key and settings.llm_api_key.strip())
self.llm: ChatOpenAI | None = None
if self.llm_enabled:
    self.llm = ChatOpenAI(...)
```

### 4.2 各 Agent 本地 Fallback 策略

| Agent | Fallback 方法 | 逻辑 |
|-------|--------------|------|
| `MarketingCopyAgent` | `_fallback_copy()` | 按用户分层（5 种 Segment）填充模板文案，经合规检查后返回，`confidence=0.7` |
| `ProductRecAgent` | `_fallback_rerank()` | 五元组本地排序：偏好类目命中 → 价格区间 → 新品加权 → 库存 → 价格偏离距离 |
| `UserProfileAgent` | `_fallback_profile()` | 基于行为数据（浏览记录、购买次数、客单价）规则推断分群，动态计算价格区间上限 |

---

## 5. 多级缓存体系

#### 5.1 用户画像缓存（`user_profile_agent.py`）

实现 L1 → L2 → 生成 的三层降级读取，写入时同步回填两级缓存。

```
请求
 │
 ├─► L1 本地 TTLCache（TTL=60s, maxsize=128）
 │       命中 → 直接返回
 │       未命中 ↓
 ├─► L2 Redis（TTL=3600s）
 │       命中 → 回填 L1 → 返回
 │       未命中 ↓
 └─► LLM 生成 / 本地 Fallback → 回填 L1 + L2 → 返回
```

**Redis 异步化**：Redis 为同步客户端，通过 `ThreadPoolExecutor(max_workers=2)` + `loop.run_in_executor()` 包装，避免阻塞 asyncio 事件循环。

**Redis 不可用降级**：初始化时 `ping()` 失败则静默置 `redis_client = None`，仅使用 L1 缓存继续服务。

#### 5.2 产品类目缓存（`product_rec_agent.py`）

```python
@lru_cache(maxsize=50)
def _get_products_by_category(self, category: str) -> tuple:
    return tuple(p for p in self._product_catalog if p.category == category)
```

- 初始化时将 `MOCK_PRODUCTS` 转为不可变 `tuple`，避免每次召回重新构造列表
- 按类目缓存过滤结果，召回时优先取前 3 个偏好类目的缓存数据，再补充其他类目
- 同步上报 Prometheus `cache_hits_total` / `cache_misses_total`

---

## 6. 正则预编译优化 — `marketing_copy_agent.py`

`_compliance_check()` 每次调用都对 `FORBIDDEN_WORDS` 中的每个词执行 `re.compile()`，在高并发场景下产生大量重复编译开销。优化后在模块加载时一次性编译所有禁词正则，存储为模块级常量：

```python
# 优化前：每次调用都重新编译
def _compliance_check(self, copy_item):
    for word in FORBIDDEN_WORDS:
        text = re.sub(re.escape(word), "***", text)

# 优化后：启动时预编译，运行时直接复用
_FORBIDDEN_WORDS_PATTERNS = {
    word: re.compile(re.escape(word)) for word in FORBIDDEN_WORDS
}

def _compliance_check(self, copy_item):
    for word, pattern in _FORBIDDEN_WORDS_PATTERNS.items():
        text = pattern.sub("***", text)
```

**收益**：禁词数量为 10 个，每次文案生成调用节省 10 次 `re.compile()` 开销，在批量文案场景下效果显著。

---

## 7. 请求级超时中间件 — `main.py`

原版无请求级超时控制，LLM 调用超时时请求会无限等待，占用连接资源。

#### 7.1 超时中间件

```python
@app.middleware("http")
async def request_timeout_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1/recommend"):
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=settings.request_timeout_seconds,  # 默认 12s
            )
        except asyncio.TimeoutError:
            return JSONResponse(status_code=503, content={
                "error": "Request timeout",
                "message": f"请求超过 {settings.request_timeout_seconds}s 限制，请稍后重试",
            })
```

- 使用路径前缀匹配（`startswith`），兼容后续 API 版本扩展
- 超时返回 HTTP **503**，区别于业务错误的 500
- 超时时长读取自 `settings.request_timeout_seconds`，支持热配置

#### 7.2 计时中间件

```python
@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    request_duration_seconds.labels(endpoint=..., method=...).observe(latency)
    requests_total.labels(endpoint=..., method=..., status=...).inc()
    return response
```

对所有请求自动记录延迟并上报到 Prometheus，无需在每个路由中手动埋点。

---

## 8. 可观测性与监控集成 — `services/metrics.py` & `main.py`

#### 8.1 Prometheus 指标体系

新增全局 `CollectorRegistry`，定义以下指标：

| 指标名 | 类型 | 标签 | 说明 |
|--------|------|------|------|
| `request_duration_seconds` | Histogram | `endpoint`, `method` | HTTP 请求延迟 |
| `requests_total` | Counter | `endpoint`, `method`, `status` | HTTP 请求总数 |
| `agent_duration_seconds` | Histogram | `agent_name` | Agent 执行耗时 |
| `agent_errors_total` | Counter | `agent_name`, `error_type` | Agent 错误计数 |
| `cache_hits_total` | Counter | `cache_name` | 缓存命中数 |
| `cache_misses_total` | Counter | `cache_name` | 缓存未命中数 |

#### 8.2 ErrorType 枚举

防止错误消息直接作为 Prometheus label 导致高基数（Cardinality）问题，通过关键词匹配将错误归类为五种类型：

```
TIMEOUT | LLM_ERROR | REDIS_ERROR | VALIDATION_ERROR | UNKNOWN
```

#### 8.3 业务事件内存安全

```python
# 优化前：无界 list，高并发下持续增长
self._business_events: list[dict] = []

# 优化后：固定大小循环缓冲区 + 采样
self._business_events: deque = deque(maxlen=1000)  # 新事件覆盖旧事件
# 每 100 次请求仅采样 1 条
if self._request_count % self._sampling_rate == 0:
    self._business_events.append(event)
```

---

## 9. 压测体系搭建

#### 9.1 压测脚本 — `tests/load_test_locust.py`

模拟两类用户的混合流量：

| 用户类型 | 行为 | 请求比例 |
|----------|------|----------|
| `RecommendationUser` | 推荐接口 `/api/v1/recommend` | ~90% |
| `RecommendationUser` | 指标接口 `/api/v1/metrics` | ~10% |
| `PrometheusMetricsUser` | Prometheus 抓取 `/metrics`（2s 固定间隔） | 独立 |

压测结束后自动采集 P50 / P95 / P99 延迟，序列化为 `reports/baseline.json`。

#### 9.2 HTML 报告生成器 — `reports/generate_perf_report.py`

将 `baseline.json` 转换为可交互的 HTML 可视化报告，包含：

- 关键指标卡片（总请求数、失败数、错误率、平均延迟）
- 端点延迟对比图（平均 vs P95，Chart.js 柱状图）
- 端点错误率分布图（绿 < 1% / 橙 1~5% / 红 > 5% 动态着色）
- 详细指标表格（P50 / P95 / P99 逐端点展示）

```bash
python reports/generate_perf_report.py reports/baseline.json reports/baseline_report.html
```

#### 9.3 一键压测脚本 — `run_performance_test.sh`

六步自动化流水线，覆盖从环境准备到报告输出的完整链路：

```
Step 1  启动服务（端口检测 + 后台启动 + 健康轮询）
Step 2  健康验证（/health）
Step 3  Prometheus 指标预览（/metrics 格式校验）
Step 4  API 冒烟测试（单次推荐请求）
Step 5  Locust 压测（50 用户 / 30s / headless）
Step 6  HTML 报告生成（baseline.json → baseline_report.html）
```

