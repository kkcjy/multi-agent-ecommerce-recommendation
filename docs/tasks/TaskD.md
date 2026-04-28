# Multi-Agent 电商系统 — 代码改进分析报告

## 📊 改进概览

```
稳定性层（Stability）
  ├─ BaseAgent: 重试 + 断路器
  └─ Config: 参数中枢

性能层（Performance）
  ├─ UserProfileAgent: L1+L2 缓存
  ├─ ProductRecAgent: 产品目录 + LRU 缓存
  └─ MarketingCopyAgent: 正则预编译

可观测性层（Observability）
  ├─ main.py: 超时中间件
  ├─ metrics.py: Prometheus 指标
  └─ load_test_locust.py: 性能基线

分析层（Analysis）
  └─ generate_perf_report.py: 报告可视化
```

---

## 1. `base_agent.py` — 重试与熔断机制升级

### 修改内容

#### 配置外部化（硬编码 → `get_settings()`）

| 参数 | 原版 | 优化后 |
|---|---|---|
| `max_retries` | 构造函数参数，默认 `2` | `settings.agent_max_retries` |
| 退避系数 | `_retry_execute` 里写死 `multiplier=0.5, max=4` | `self.retry_backoff_factor / max` 来自 settings |

无需改代码即可调整所有 Agent 行为，适合多环境部署（dev/staging/prod）。

---

#### 电路断路器（Circuit Breaker）

```python
# 滑动时间窗口内错误计数
self._error_timestamps: list[float] = []

def _is_circuit_breaker_open(self) -> bool:
    now = time.time()
    self._error_timestamps = [ts for ts in self._error_timestamps
                               if now - ts < self._circuit_breaker_window]
    return len(self._error_timestamps) >= self._circuit_breaker_threshold
```

- ✅ 防止雪崩：下游故障时快速失败，不堆积重试
- ✅ 窗口自动清理过期记录，避免内存泄漏

---

## 2. `product_rec_agent.py` — 召回层缓存优化

### 修改内容

#### 产品目录预加载

```python
self._product_catalog = self._get_product_catalog()   # 不可变 tuple
self._product_by_id = {p.product_id: p for p in self._product_catalog}
```

原版每次 `_recall` 都执行 `list(MOCK_PRODUCTS)` 创建新列表。优化后在初始化时固化为 `tuple`，防止被意外修改。

---

#### 类目级 LRU 缓存

```python
@lru_cache(maxsize=50)
def _get_products_by_category(self, category: str) -> tuple:
    return tuple(p for p in self._product_catalog if p.category == category)
```

对高频类目（手机/耳机）避免重复遍历。

---

#### 召回逻辑重构

| | 原版 | 优化后 |
|---|---|---|
| 策略 | 全量加载再 sort | 偏好类目先取缓存，再补其他类目 |
| 排序 key | `(category in preferred, stock>0, random)` | `(stock>0, random)` |

将"偏好类目"从排序条件提升为召回过滤条件，逻辑更清晰。但原版排序 key 更完整（同时考虑偏好权重 + 库存 + 随机性），新版丢掉了偏好权重在排序中的作用。

---

## 3. `user_profile_agent.py` — 两层缓存架构（优化后）

### 修改内容

#### 整体架构：L1 → L2 → LLM 三级降级

```
请求 → L1 本地内存（hit?）→ L2 Redis（hit?）→ LLM 生成 → 回写 L1+L2
```

原版每次请求都调用 LLM，优化后 将热点用户的画像请求拦截在内存层，显著降低 LLM 调用成本。

---

#### Redis 接入（L2 缓存）

```python
try:
    self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    self.redis_client.ping()
except Exception:
    self.redis_client = None  # 降级：Redis 不可用时退化为无 L2
```

降级处理优雅，Redis 挂了不影响主流程。

---

#### L1 本地缓存：空实现问题

```python
@lru_cache(maxsize=128)
def _get_local_cache(self, user_id: str) -> UserProfile | None:
    return None  # 永远返回 None

def _set_local_cache(self, user_id: str, profile: UserProfile):
    pass  # 什么都不做
```

L1 缓存**完全不工作**，每次都穿透到 Redis 或 LLM。`lru_cache` 无法手动 `set`，应用 `cachetools.TTLCache` 替代：

```python
from cachetools import TTLCache
self._local_cache = TTLCache(maxsize=128, ttl=60)

def _get_local_cache(self, user_id):
    return self._local_cache.get(user_id)

def _set_local_cache(self, user_id, profile):
    self._local_cache[user_id] = profile
```

---

#### `_execute` 可观测性退步

| | 原版 | 优化后 |
|---|---|---|
| `data` 字段 | `{"raw_analysis": response.content}` | `{"source": "cache_or_llm"}` |

`source` 字段无法区分命中哪层缓存，调试时无法判断数据新鲜度。建议改为 `"l1_cache"` / `"l2_redis"` / `"llm_generated"` 三值枚举。

---

## 4. `config.py` — 配置中枢扩展

### 修改内容

#### 新增字段分组

**请求超时 & 重试：**

```python
request_timeout_seconds: float = 8.0
agent_max_retries: int = 2
agent_retry_backoff_factor: float = 0.5
agent_retry_backoff_max: float = 4.0
```

`request_timeout_seconds=8.0` 与 `agent_timeout_product_rec=8.0` 数值相同但语义不同，两者应满足 `agent_timeout < request_timeout`，当前边界模糊。

**电路断路器：**

```python
circuit_breaker_enabled: bool = True       # 可全局关闭（如压测场景）
circuit_breaker_failure_threshold: int = 5
circuit_breaker_window_seconds: int = 300
```

`threshold=5` 在 300s 窗口内触发，对高 QPS 服务可能太宽松，建议同时支持错误率阈值（如 50%）。

**缓存配置（对应优化后/2B）：**

```python
cache_user_profile_ttl_seconds: int = 3600   # L2 Redis TTL
cache_user_profile_local_ttl_seconds: int = 60  # L1 本地（目前未被消费）
cache_product_recall_ttl_seconds: int = 300
cache_local_maxsize: int = 128
```

TTL 层次清晰（L1 < L2），`cache_user_profile_local_ttl_seconds` 是"配置孤岛"，待 L1 缓存修复后才会生效。

**指标采样配置（对应 `metrics.py`）：**

```python
metrics_business_event_max_size: int = 1000
metrics_business_event_sampling_rate: int = 100
```

---

#### 设计问题

| 问题 | 说明 |
|---|---|
| 缺少字段校验 | `agent_retry_backoff_factor` 应 `> 0`，`circuit_breaker_failure_threshold` 应 `>= 1` |
| `cache_local_maxsize` 语义模糊 | `ProductRecAgent` 的 `lru_cache(maxsize=50)` 是硬编码值，与此配置不一致 |
| 原有字段无阶段标注 | 新增字段有 `(新增: 阶段 X)` 注释，旧字段没有，混合后可读性下降 |

建议加入 pydantic 校验守卫：

```python
from pydantic import field_validator

@field_validator("agent_retry_backoff_factor", "agent_retry_backoff_max")
@classmethod
def must_be_positive(cls, v: float) -> float:
    if v <= 0:
        raise ValueError("backoff 参数必须为正数")
    return v
```

---

## 5. `main.py` — 超时中间件与 Prometheus 端点（优化后）

### 修改内容

#### 请求级超时中间件

```python
@app.middleware("http")
async def request_timeout_middleware(request: Request, call_next):
    if request.url.path in ["/api/v1/recommend", "/api/v1/recommend/graph"]:
        try:
            response = await asyncio.wait_for(
                call_next(request), timeout=settings.request_timeout_seconds
            )
        except asyncio.TimeoutError:
            return JSONResponse(status_code=503, ...)
```

是 `BaseAgent` 单 Agent 超时的上层兜底。

**问题：**
1. FastAPI 的 `call_next` 在某些版本中 `asyncio.wait_for` 取消不干净（内部任务继续运行但响应已返回 503）。更可靠的做法是在 `SupervisorOrchestrator` 层控制超时
2. 路径列表硬编码，建议改为前缀匹配：`request.url.path.startswith("/api/v1/recommend")`

---

#### HTTP 请求计时中间件

```python
@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    ...
    request_duration_seconds.labels(...).observe(latency)
    requests_total.labels(...).inc()
```

**中间件顺序（隐蔽但重要）：** FastAPI 中间件后注册先执行（栈结构）。当前顺序使 `timing` 能正确捕获超时的 503 状态码，顺序恰好正确但属于隐式依赖，建议加注释说明。

**高基数 label 风险：** `endpoint=request.url.path` 若路径含变量（如 `/users/12345`），会产生无限基数 label，导致 Prometheus 内存爆炸。建议改为路由模板。

---

#### 新增 Prometheus 原生端点

```python
@app.get("/metrics")
async def get_prometheus_metrics():
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4")
```

原版仅有 `/api/v1/metrics`（JSON，供人读），优化后 新增 `/metrics`（text/plain，供 Prometheus scrape）。

**安全提示：** `/metrics` 在生产环境应加鉴权或限制为内网访问，否则任何人都能获取系统内部指标。

---

#### 其他变更

| 变更 | 说明 |
|---|---|
| 端口 `8000` → `8866` | 避免与常见服务冲突 |
| 新增 `import time, asyncio` | 配合新中间件 |
| `/api/v1/metrics` 注释加 "(JSON 格式)" | 与 `/metrics` 端点区分，可读性提升 |

---

## 6. `metrics.py` — Prometheus 集成与内存安全（优化后）

### 修改内容

#### Prometheus 指标层（全新引入）

新增五个 Prometheus 指标对象：

| 指标 | 类型 | 用途 |
|---|---|---|
| `request_duration_seconds` | Histogram | HTTP 请求延迟分布 |
| `requests_total` | Counter | HTTP 请求计数（含状态码） |
| `agent_duration_seconds` | Histogram | Agent 执行延迟 |
| `agent_errors_total` | Counter | Agent 错误计数 |
| `cache_hits_total / misses_total` | Counter | 缓存命中率 |

使用 `Histogram` 而非 `Gauge` 记录延迟，支持 P50/P99 分位数查询，是排查超时问题的核心工具。

**自定义 Registry 的陷阱：**
```python
REGISTRY = CollectorRegistry()  # 独立 registry
```
若任意指标定义时漏传 `registry=REGISTRY`，该指标将不出现在 `/metrics` 端点且**不会有任何报错**，是隐蔽的配置陷阱。

---

#### 内存安全：`list` → `deque(maxlen=1000)`

| | 原版 | 优化后 |
|---|---|---|
| 存储结构 | `list`，无限增长 | `deque(maxlen=1000)`，自动淘汰最旧条目 |
| 内存上限 | 无（OOM 风险） | 固定 1000 条 |

---

#### 采样机制

```python
if self._request_count % self._sampling_rate == 0:  # 每 100 次采 1 条
    self._business_events.append(...)
```

与 `deque` 配合形成双重保护：采样控制写入频率，`deque` 控制最大存量。

**问题：**
1. 多 worker 部署时（`uvicorn --workers 4`），每个进程有独立计数器，总体采样率翻倍，Prometheus Counter 同样有此问题
2. `error_type=error` 直接用异常消息字符串作为 label，若消息包含变量内容（user_id、IP 等）会产生**无限基数 label**，导致 Prometheus 内存爆炸。应枚举化为 `"timeout"` / `"llm_error"` / `"unknown"` 等固定值

---

#### `record_agent_call` 双路写入

```python
def record_agent_call(self, ...):
    # 写内存（供 /api/v1/metrics JSON 端点）
    m = self._agent_metrics[agent_name]
    ...
    # 写 Prometheus（供 /metrics scrape 端点）
    agent_duration_seconds.labels(...).observe(latency_ms / 1000.0)  # ms → s
```

一次调用同步写两个存储，接口不变，调用方零改动，是干净的渐进式升级。注意 `latency_ms / 1000.0` 做了单位转换，内存侧存毫秒、Prometheus 侧存秒，建议加注释防止混淆。

---

### 建议（最高优先）

`error_type` label 值做枚举化，防止高基数导致 Prometheus 内存问题——这是唯一一个可能在生产环境造成连锁故障的问题。

---

## 7. `marketing_copy_agent.py` — 文案生成优化（优化后）

### 修改内容

#### 正则表达式预编译

```python
# 预编译正则表达式 (优化后)
_FORBIDDEN_WORDS_PATTERNS = {
    word: re.compile(re.escape(word)) for word in FORBIDDEN_WORDS
}

def _compliance_check(self, copy_item: dict[str, str]) -> dict[str, str]:
    """过滤违反广告法的禁用词汇。
    
    优化 (优化后): 使用预编译的正则表达式，避免每次都重新编译。
    """
    text = copy_item.get("copy", "")
    for word, pattern in _FORBIDDEN_WORDS_PATTERNS.items():
        text = pattern.sub("***", text)
    copy_item["copy"] = text
    return copy_item
```

**优化意义：**
- ✅ 原版每次 `_compliance_check` 都重新编译 50+ 个禁用词的正则表达式
- ✅ 优化后在模块加载时编译一次，避免重复计算
- ✅ 高频调用场景（每生成文案都检查一遍）性能提升明显，特别是在营销活动高峰期

**复杂度对比：**

| | 原版 | 优化后 |
|---|---|---|
| `_compliance_check` 调用 | 创建 50+ 个 `re.escape()` 对象 | 直接查表取预编译 pattern |
| 内存占用 | 每次零散分配 | 一次性固定分配 |
| 时间复杂度 | O(n_words × str_len) 编译 | O(n_words) 查表 |

---

## 8. `generate_perf_report.py` — 性能报告生成（新增）

### 功能定位

性能测试数据可视化工具，用于将 Locust 压测的 JSON 输出转换为 HTML 仪表盘。这是 **度量循环** 的最后一环：

```
Locust 压测 → JSON 原始数据 → generate_perf_report.py → HTML 报告 → 性能分析决策
```

### 工作流程

```
1. 运行 Locust 压测脚本 (load_test_locust.py)
   ↓
2. Locust 生成 JSON 报告并保存到 reports/baseline.json
   ↓
3. 执行 python reports/generate_perf_report.py reports/baseline.json reports/baseline_report.html
   ↓
4. 用浏览器打开 HTML 文件查看:
   - 总体指标 (吞吐量、错误率、延迟分布)
   - 端点级别对比 (哪个 API 瓶颈最严重)
   - Chart.js 实时图表
```

### 技术要点

| 特性 | 说明 |
|---|---|
| 模板化 HTML 生成 | 避免手写 HTML，通过 f-string 模板拼装 |
| Chart.js 集成 | 使用 CDN，无需本地依赖 |
| 梯度背景 | 视觉吸引力，专业化外观 |
| 端点级指标分解 | 支持按 endpoint 对比性能，识别单点故障 |

---

## 9. `load_test_locust.py` — 性能基线压测（新增）

### 设计理念

双用户类模型，模拟真实流量多样性：

```
RecommendationUser       (90%)  - 推荐请求 + 指标查询
    ↓
PrometheusMetricsUser   (10%)  - 监控 scraper，高频周期查询
```

### 核心任务集

#### `RecommendationUser` 任务分布

| 任务 | 权重 | 频率 | 模拟对象 |
|---|---|---|---|
| `recommend_api` | 10 | 主任务（90%） | 真实用户推荐请求 |
| `metrics_api` | 1 | 次任务（10%） | 监控系统实时查询 |

```python
@task(10)
def recommend_api(self):
    """主要任务: 发起推荐请求 (占 90% 的请求)."""
    payload = {
        "user_id": self.user_id,
        "scene": self.scene,
        "num_items": 10,
        "context": {
            "device": random.choice(["mobile", "pc", "tablet"]),
            "referrer": random.choice(["search", "homepage", "cart"]),
        },
    }
    # ...
```

**设计细节：**
- ✅ 动态 `user_id`（user_1000 ~ user_9999）避免缓存穿透
- ✅ 多种 `scene`（home/search/category）测试不同推荐场景
- ✅ `context` 字段包含设备、来源等元数据，接近真实请求

#### `PrometheusMetricsUser` 监控模拟

```python
class PrometheusMetricsUser(HttpUser):
    wait_time = constant_pacing(2)  # 每 2s 查询一次 ← 模拟 Prometheus 抓取频率
    
    @task
    def scrape_prometheus_metrics(self):
        """持续抓取 Prometheus 指标."""
        with self.client.get("/metrics", catch_response=True) as resp:
            # 验证 Prometheus text/plain 格式
            if "# HELP" in content and "# TYPE" in content:
                resp.success()
```

- ✅ 固定 2s 周期（`constant_pacing`），模拟 Prometheus 真实 scrape 间隔
- ✅ 检验 `# HELP` 和 `# TYPE` 行，验证 Prometheus 格式合规

### 测试场景（启动参数）

```bash
# 场景 1: 正常流量 (100 用户, 2 RPS, 60s)
locust -f load_test_locust.py --host=http://localhost:8866 \
  --users=100 --spawn-rate=2 --run-time=60s

# 场景 2: 峰值突刺 (500 用户, 10 RPS, 30s)
locust -f load_test_locust.py --host=http://localhost:8866 \
  --users=500 --spawn-rate=10 --run-time=30s

# 场景 3: 管理接口并发 (50 用户，全速，30s)
locust -f load_test_locust.py --host=http://localhost:8866 \
  --users=50 --run-time=30s
```

### 可观测性

**Locust 仪表盘：** `http://localhost:8089`
- 实时吞吐量、响应时间、错误率
- 按端点聚合统计

**Prometheus 指标：** `http://localhost:8866/metrics`
- Locust 压测结果与系统 metrics 端点同步采集
- 便于后续关联分析

---

## 10. 文件修改统计

### kkcjy 提交的 Python 文件改动

| 文件 | 修改类型 | 关键更新 | 优先级 |
|---|---|---|---|
| `base_agent.py` | ✏️ 修改 | 断路器 + 配置外部化 | P0 |
| `product_rec_agent.py` | ✏️ 修改 | 产品目录缓存 + LRU 优化 | P1 |
| `user_profile_agent.py` | ✏️ 修改 | L1+L2 缓存架构 | P0 |
| `marketing_copy_agent.py` | ✏️ 修改 | 正则预编译 (优化后) | P2 |
| `config/settings.py` | ✏️ 修改 | 配置中枢扩展 | P1 |
| `main.py` | ✏️ 修改 | 超时中间件 + Prometheus 端点 | P0 |
| `metrics.py` | ✏️ 修改 | Prometheus 集成 | P1 |
| `generate_perf_report.py` | ✨ 新增 | 性能报告可视化 | P2 |
| `load_test_locust.py` | ✨ 新增 | 性能基线压测 | P2 |

---

## 全局演进路径总结

```
Settings（配置中枢）
    ├─ 提供参数给各 Agent
    ↓
BaseAgent（重试 + 断路器）       ← 优化后：稳定性
    ├─ 继承、错误隔离
    ↓
┌─ UserProfileAgent（L1+L2 缓存） ← 优化后：性能
├─ ProductRecAgent（分类缓存）   ← 优化后：性能
└─ MarketingCopyAgent（文案优化） ← 优化后：文案
    ↓ 被编排
SupervisorOrchestrator
    ↓
main.py（超时中间件 + Prometheus）← 优化后：可观测性
    ├─ 系统级超时兜底
    └─ 指标导出（/metrics）
        ↓
metrics.py（指标收集）             ← 优化后：基础设施
    └─ Prometheus 指标定义
        ↓
load_test_locust.py（性能基线）   ← 度量循环：验证优化效果
    ↓
generate_perf_report.py（可视化） ← 输出分析报告
```

### 当前最薄弱的五个环节（优先级排序）

| 优先级 | 问题 | 文件 | 风险 | 修复建议 |
|---|---|---|---|---|
| **P0** | `error_type` label 高基数 | `metrics.py` | Prometheus OOM，连锁故障 | label 值枚举化（timeout/llm_error/unknown） |
| **P0** | 同步 Redis 阻塞事件循环 | `user_profile_agent.py` | 高并发下请求堆积 | 改用 aioredis 或异步库 |
| **P0** | L1 缓存空实现 | `user_profile_agent.py` | 缓存层完全失效 | 改用 cachetools.TTLCache |
| **P1** | 断路器无半开状态 | `base_agent.py` | 下游恢复后系统无法自愈 | 添加 HALF_OPEN 状态 + 探测机制 |
| **P2** | 中间件超时取消不干净 | `main.py` | 503 后内部任务仍在运行 | 在编排层控制超时，而非中间件 |
---

## 📝 附录：技术债清单

### 立即行动（Within 1 sprint）

- [ ] **metrics.py**: 将 `error_type` 改为枚举，防止 label 爆炸
- [ ] **user_profile_agent.py**: 改用 aioredis，避免同步 Redis 阻塞
- [ ] **user_profile_agent.py**: 修复 L1 缓存，改用 cachetools.TTLCache

### 近期规划（Within 2 sprints）

- [ ] **base_agent.py**: 添加断路器半开状态 + 探测机制
- [ ] **config/settings.py**: 添加 pydantic 校验，防止配置错误
- [ ] **load_test_locust.py**: 运行性能基线，建立对标指标
- [ ] **main.py**: 在编排层实现超时控制，而非中间件

### 长期优化（Backlog）

- [ ] 增加分布式链路追踪（Jaeger/Tempo）
- [ ] 实现 Agent 级别 SLA 配置
- [ ] 添加灰度发布机制（金丝雀/蓝绿）

---

## 🎯 快速导航

| 场景 | 相关文件 | 关键概念 |
|---|---|---|
| **要稳定？** | [BaseAgent](#1-base_agentpy) + [Settings](#4-configpy---配置中枢扩展) | 断路器、重试、配置外部化 |
| **要快速？** | [UserProfileAgent](#3-user_profile_agentpy) + [ProductRecAgent](#2-product_rec_agentpy) | 多层缓存、LRU、预热 |
| **要对标？** | [load_test_locust.py](#9-load_test_locustpy---性能基线压测新增) + [generate_perf_report.py](#8-generate_perf_reportpy---性能报告生成新增) | 基线、可视化、趋势分析 |
| **要监控？** | [metrics.py](#6-metricspy---prometheus-集成与内存安全阶段-1) + [main.py](#5-mainpy---超时中间件与-prometheus-端点阶段-4) | Prometheus、Grafana、告警 |

---

**报告完成** | 下一步：[关闭高优先级问题](https://github.com/xxx/issues) | [查看完整代码diff](https://github.com/xxx/commit/4b1cff2)