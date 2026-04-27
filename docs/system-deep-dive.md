# 多 Agent 电商推荐系统 - 深度解析

> 本文档详细解析系统每个文件的作用、模块间协作关系、以及测试策略

---

## 一、系统整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户请求 (HTTP)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  main.py (FastAPI 入口)                                          │
│  - /api/v1/recommend (Supervisor 模式)                           │
│  - /api/v1/recommend/graph (LangGraph 模式)                      │
└──────────────┬──────────────────────┬───────────────────────────┘
               │                      │
               ▼                      ▼
    ┌──────────┴──────┐      ┌───────┴────────┐
    │   Supervisor    │      │   LangGraph    │
    │  Orchestrator   │      │    Pipeline    │
    └────────┬────────┘      └────────┬───────┘
             │                        │
             └───────────┬────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ UserProfile │ │ ProductRec  │ │  Inventory  │
│   Agent     │ │   Agent     │ │   Agent     │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       │               ▼               │
       │      ┌─────────────────┐      │
       │      │  AppContainer   │      │
       │      │ (依赖注入容器)   │      │
       │      └────────┬────────┘      │
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│FeatureStore │ │ProductRepo  │ │InventoryDB  │
│VectorStore  │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## 二、文件详解

### 2.1 入口层

#### `python/main.py` - FastAPI 应用入口

**职责**：
- 创建 FastAPI 应用实例
- 初始化全局依赖注入容器 (AppContainer)
- 注册 API 路由
- 配置 CORS 和静态文件

**核心代码流程**：
```python
# 1. 初始化全局容器
container = AppContainer(settings=settings)

# 2. 创建编排器
supervisor = SupervisorOrchestrator(container=container, ab_engine=ab_engine)

# 3. 注册路由
@app.post("/api/v1/recommend")
async def recommend(request):
    return await supervisor.recommend(request)
```

**关键依赖**：
- `AppContainer` - 依赖注入容器
- `SupervisorOrchestrator` - 编排器
- `ABTestEngine` - A/B 测试引擎

---

#### `python/config/settings.py` - 配置管理

**职责**：
- 使用 pydantic-settings 管理环境变量
- 提供统一的配置访问接口

**配置项**：
```python
class Settings(BaseSettings):
    # LLM 配置
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    
    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"
    
    # Milvus 配置
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    
    # 数据库配置
    database_url: str = "sqlite:///./ecommerce.db"
    
    # Agent 超时设置
    agent_timeout_user_profile: float = 5.0
    agent_timeout_product_rec: float = 8.0
```

**使用方式**：
```python
from config import get_settings
settings = get_settings()  # 从环境变量读取
```

---

### 2.2 数据模型层

#### `python/models/schemas.py` - Pydantic 数据模型

**核心类**：

| 类名 | 用途 | 关键字段 |
|------|------|----------|
| `UserProfile` | 用户画像 | `user_id`, `segments`, `preferred_categories`, `price_range` |
| `Product` | 商品信息 | `product_id`, `name`, `category`, `price`, `explain` |
| `RecommendationRequest` | 推荐请求 | `user_id`, `scene`, `num_items` |
| `RecommendationResponse` | 推荐响应 | `request_id`, `products`, `experiment_group` |
| `AgentResult` | Agent 执行结果 | `agent_name`, `success`, `latency_ms` |

**设计要点**：
- `explain` 字段：支持推荐结果可解释性
- 所有 Agent 结果继承 `AgentResult`，统一返回格式

---

### 2.3 Agent 层

#### `python/agents/base_agent.py` - Agent 基类

**职责**：
- 提供统一的 Agent 接口
- 实现重试机制（tenacity）
- 实现超时和降级处理
- 统计错误率

**核心方法**：
```python
async def run(self, **kwargs) -> AgentResult:
    """公共入口：包装_execute，提供重试和降级"""
    
async def _execute(self, **kwargs) -> AgentResult:
    """子类实现具体逻辑"""
    
def _fallback(self, latency_ms, exc) -> AgentResult:
    """失败时返回降级结果"""
```

**设计模式**：
- **模板方法模式**：`run()` 定义流程，`_execute()` 由子类实现
- **重试模式**：使用 tenacity 实现指数退避重试

---

#### `python/agents/user_profile_agent.py` - 用户画像 Agent

**职责**：
- 分析用户行为数据
- 生成用户画像（分群、偏好类目、价格区间）
- 计算 RFM 分数

**工作流程**：
```
1. 收集用户行为 (从 FeatureStore 或 context)
   ↓
2. 调用 LLM 分析行为数据
   ↓
3. 解析 LLM 返回的 JSON
   ↓
4. 构建 UserProfile 对象
```

**LLM Prompt**：
```python
SYSTEM_PROMPT = """你是一个电商用户画像分析专家...
输出 JSON 格式：
{
  "segments": ["new_user", "active"],
  "preferred_categories": ["手机", "耳机"],
  "price_range": [最低价，最高价],
  "rfm_score": {"recency": 0.5, "frequency": 0.3, "monetary": 0.8}
}
"""
```

---

#### `python/agents/product_rec_agent.py` - 商品推荐 Agent

**职责**：
- 多策略召回商品
- LLM 重排序
- 生成推荐解释

**召回策略**：
```python
async def _recall(self, profile, limit):
    # 策略 1: 向量召回 (Milvus)
    if self.vector_store.is_available():
        candidates.extend(await vector_search())
    
    # 策略 2: 类目召回 (用户偏好类目)
    if profile.preferred_categories:
        candidates.extend(await category_search())
    
    # 策略 3: 热门商品兜底
    candidates.extend(await hot_products())
    
    return candidates
```

**重排序**：
- 使用 LLM 根据用户画像对候选商品排序
- 保证类目多样性
- 失败时降级为原始顺序

**解释生成**：
```python
def _build_explain(self, product, profile, recall_source):
    return {
        "recall_source": recall_source,  # 召回来源
        "matched_category": True/False,  # 是否命中偏好类目
        "price_matched": True/False,     # 价格是否匹配
        "matched_tags": ["旗舰", "新品"]  # 命中的标签
    }
```

---

#### `python/agents/marketing_copy_agent.py` - 营销文案 Agent

**职责**：
- 根据用户分群生成个性化文案
- 广告法合规检查

**模板选择策略**：
```python
def _select_template(self, profile):
    priority = [
        UserSegment.NEW_USER,        # 新客：热情友好
        UserSegment.HIGH_VALUE,      # VIP: 品质尊享
        UserSegment.CHURN_RISK,      # 流失风险：情感唤回
        UserSegment.PRICE_SENSITIVE, # 价格敏感：突出性价比
        UserSegment.ACTIVE           # 活跃用户：场景共鸣
    ]
```

**合规检查**：
```python
FORBIDDEN_WORDS = ["最好", "第一", "国家级", "绝对", "100%"]
def _compliance_check(self, copy_item):
    for word in FORBIDDEN_WORDS:
        text = re.sub(word, "***", text)
```

---

#### `python/agents/inventory_agent.py` - 库存决策 Agent

**职责**：
- 检查商品库存状态
- 生成低库存预警
- 计算限购数量

**决策逻辑**：
```python
async def _execute(self, products):
    for product in products:
        stock = await self._check_stock(product_id)
        
        # 库存为 0，过滤
        if stock <= 0:
            continue
        
        # 低库存预警
        if stock <= SAFETY_STOCK_THRESHOLD:
            alerts.append({"level": "critical"})
        
        # 计算限购
        limit = self._calc_purchase_limit(product, stock)
```

---

### 2.4 编排层

#### `python/orchestrator/supervisor.py` - Supervisor 编排器

**职责**：
- 协调 4 个 Agent 的执行
- 实现三阶段并行流水线

**执行流程**：
```
Phase 1 (并行):
├─ UserProfileAgent → 用户画像
└─ ProductRecAgent → 候选商品召回

Phase 2 (并行):
├─ ProductRecAgent → LLM 重排
└─ InventoryAgent → 库存过滤

Phase 3:
└─ MarketingCopyAgent → 文案生成
```

**代码结构**：
```python
async def recommend(self, request):
    # Phase 1
    profile_result, rec_result = await asyncio.gather(
        self.user_profile_agent.run(...),
        self.product_rec_agent.run(...)
    )
    
    # Phase 2
    rerank_result, inventory_result = await asyncio.gather(
        self.product_rec_agent.run(user_profile=profile),
        self.inventory_agent.run(products=raw_products)
    )
    
    # Phase 3
    copy_result = await self.marketing_copy_agent.run(...)
    
    return RecommendationResponse(...)
```

---

#### `python/orchestrator/graph.py` - LangGraph 状态图

**职责**：
- 使用 LangGraph 实现状态机编排
- 与 Supervisor 功能对齐，提供另一种编排方式

**状态定义**：
```python
class PipelineState(TypedDict, total=False):
    request_id: str
    user_id: str
    user_profile: UserProfile | None
    raw_products: list[Product]
    ranked_products: list[Product]
    final_products: list[Product]
```

**节点设计**：
```python
async def init_node(state): ...
async def user_profile_node(state): ...
async def product_recall_node(state): ...
async def rerank_node(state): ...
async def inventory_node(state): ...
async def filter_node(state): ...
async def marketing_copy_node(state): ...
async def aggregate_node(state): ...
```

**图结构**：
```
init → parallel_phase1 → parallel_phase2 → filter → marketing_copy → aggregate → END
```

---

### 2.5 依赖注入层

#### `python/containers/app_container.py` - 依赖注入容器

**职责**：
- 集中管理服务生命周期
- 提供懒加载能力
- 支持服务替换（测试时使用）

**核心设计**：
```python
class AppContainer:
    def __init__(self, settings=None):
        self._settings = settings
        self._product_repo = None
        self._vector_store = None
        self._inventory_db = None
        self._feature_store = None
    
    @property
    def product_repo(self) -> ProductRepository:
        if self._product_repo is None:
            self._product_repo = InMemoryProductRepository()
        return self._product_repo
```

**测试注入**：
```python
container = AppContainer()
container.set_product_repo(mock_repo)  # 注入 Mock
```

---

### 2.6 仓库层

#### `python/repositories/product_repository.py` - 产品仓库抽象

**职责**：
- 定义产品数据访问接口
- 实现 Repository 模式

**接口定义**：
```python
class ProductRepository(ABC):
    @abstractmethod
    async def get_by_ids(self, ids: list[str]) -> list[Product]: ...
    
    @abstractmethod
    async def get_by_category(self, category: str, limit: int) -> list[Product]: ...
    
    @abstractmethod
    async def get_by_price_range(...) -> list[Product]: ...
    
    @abstractmethod
    async def get_hot_products(self, limit: int) -> list[Product]: ...
```

---

#### `python/repositories/in_memory_product_repository.py` - 内存实现

**职责**：
- 使用 Mock 数据实现产品仓库
- 用于开发和降级场景

**数据结构**：
```python
MOCK_PRODUCTS = [
    Product(product_id="P001", name="iPhone 16 Pro", ...),
    Product(product_id="P002", name="华为 Mate 70", ...),
    ...
]
```

**索引优化**：
```python
self._id_index = {p.product_id: p for p in self._products}
self._category_index = {category: [products] for each category}
```

---

### 2.7 服务层

#### `python/services/vector_store.py` - 向量检索服务

**职责**：
- 商品向量相似度搜索
- 支持降级（无 Milvus 时返回空列表）

**设计原则**：
```python
async def search_by_vector(self, query_vector, limit):
    if not self._client:  # 降级
        return []
    try:
        return [...]  # Milvus 搜索
    except Exception:
        return []  # 不阻塞主流程
```

---

#### `python/services/inventory_db.py` - 库存查询服务

**职责**：
- 查询商品库存
- 低库存预警

**降级策略**：
```python
async def get_available_ids(self, product_ids):
    if not self._client:
        return set(product_ids)  # 降级：假设有货
```

---

#### `python/services/feature_store.py` - 特征存储服务

**职责**：
- Redis 存储用户行为序列
- 滑动窗口计算实时特征
- RFM 模型计算

**核心方法**：
```python
async def record_behavior(user_id, behavior_type, item_id):
    """记录用户行为"""
    
async def get_user_features(user_id):
    """获取用户特征向量"""
    
async def _compute_rfm(user_id, purchases):
    """计算 RFM 分数"""
```

---

#### `python/services/ab_test.py` - A/B 测试引擎

**职责**：
- 用户分桶（哈希取模）
- Thompson Sampling 动态流量分配
- 指标收集

**分桶算法**：
```python
def _hash_bucket(self, user_id, experiment_id):
    raw = f"{user_id}:{experiment_id}"
    h = hashlib.md5(raw.encode()).hexdigest()
    return int(h[:8], 16) % self.bucket_count
```

**Thompson Sampling**：
```python
def assign_thompson(self, user_id):
    samples = [beta(g.successes, g.failures) for g in groups]
    return max(samples)  # 选择最优组
```

---

#### `python/services/metrics.py` - 指标收集服务

**职责**：
- Agent 调用成功率/延迟统计
- 业务事件记录

**数据结构**：
```python
@dataclass
class AgentMetric:
    call_count: int
    success_count: int
    total_latency_ms: float
    errors: list[str]
```

---

### 2.8 前端层

#### `python/frontend/user.html` - 用户端页面

**功能**：
- 展示推荐商品
- 显示推荐解释
- 模拟用户行为

#### `python/frontend/admin.html` - 管理端页面

**功能**：
- 查看 A/B 实验状态
- 查看监控指标

---

### 2.9 测试层

#### `python/tests/test_repositories.py` - 仓库层测试

**测试覆盖**：
```python
def test_get_by_ids(): ...           # 批量查询
def test_get_by_category(): ...      # 类目查询
def test_get_by_price_range(): ...   # 价格查询
def test_get_hot_products(): ...     # 热门商品
def test_get_new_products(): ...     # 新品查询
def test_fallback_when_empty(): ...  # 降级测试
```

---

#### `python/tests/test_container.py` - 容器层测试

**测试覆盖**：
```python
def test_container_product_repo_singleton(): ...  # 单例测试
def test_container_set_product_repo(): ...         # 注入测试
def test_container_reset(): ...                    # 重置测试
```

---

#### `python/tests/test_product_rec_agent.py` - Agent 层测试

**测试覆盖**：
```python
def test_agent_init_with_container(): ...     # 容器注入
def test_agent_init_without_container(): ...  # 降级测试
def test_recall_with_profile(): ...           # 有画像召回
def test_recall_without_profile(): ...        # 无画像召回
def test_explain_field_present(): ...         # 解释字段
```

---

#### `python/tests/test_graph_supervisor_alignment.py` - 对齐测试

**测试覆盖**：
```python
def test_core_fields_present_in_both(): ...        # 核心字段
def test_products_structure_aligned(): ...         # 产品结构
def test_experiment_group_aligned(): ...           # 实验分组
def test_agent_results_structure(): ...            # 结果结构
def test_latency_field_present(): ...              # 延迟字段
```

---

#### `python/tests/test_supervisor_integration.py` - 集成测试

**测试覆盖**：
```python
def test_supervisor_end_to_end(): ...              # 端到端流程
def test_graph_and_supervisor_output_aligned(): ... # 输出对齐
```

---

## 三、系统运作流程

### 3.1 推荐请求处理流程

```
1. 用户发起请求
   POST /api/v1/recommend
   {
     "user_id": "u1",
     "scene": "homepage",
     "num_items": 10
   }
   │
   ▼
2. main.py 接收请求
   - 调用 supervisor.recommend(request)
   │
   ▼
3. SupervisorOrchestrator 编排执行
   
   Phase 1 (并行):
   ├─ UserProfileAgent.run(user_id)
   │  └─ 调用 LLM 分析用户行为
   │  └─ 返回 UserProfile
   │
   └─ ProductRecAgent.run(num_items=20)
      └─ 多策略召回商品
      └─ 返回候选商品列表
   
   │
   ▼
4. Phase 2 (并行):
   ├─ ProductRecAgent.run(user_profile, num_items=10)
   │  └─ LLM 重排序
   │  └─ 生成 explain 字段
   │
   └─ InventoryAgent.run(products)
      └─ 过滤无货商品
   
   │
   ▼
5. Phase 3:
   └─ MarketingCopyAgent.run(user_profile, final_products)
      └─ 生成个性化文案
   
   │
   ▼
6. 返回响应
   {
     "request_id": "...",
     "products": [...],
     "marketing_copies": [...],
     "experiment_group": "control",
     "total_latency_ms": 1379.4
   }
```

---

### 3.2 依赖注入流程

```
1. main.py 初始化
   container = AppContainer(settings)
   │
   ├─ container.product_repo → InMemoryProductRepository
   ├─ container.vector_store → VectorStore (无 Milvus 客户端)
   ├─ container.inventory_db → InventoryDB (无 db_client)
   └─ container.feature_store → FeatureStore (无 Redis 客户端)
   
2. 创建编排器
   supervisor = SupervisorOrchestrator(container)
   │
   └─ supervisor.product_rec_agent = ProductRecAgent(container)
   
3. Agent 执行时
   agent.product_repo → 从 container 获取
   agent.vector_store → 从 container 获取
```

---

### 3.3 降级流程

```
场景：向量服务不可用

ProductRecAgent._recall():
  1. 尝试向量召回
     if self.vector_store.is_available():
         # 不可用，跳过
     else:
         return []  # 降级
  │
  2. 尝试类目召回
     if profile.preferred_categories:
         return products_by_category
  │
  3. 热门商品兜底
     return hot_products
```

---

## 四、测试策略

### 4.1 测试金字塔

```
            ┌───────────┐
            │  E2E 测试   │  ← test_supervisor_integration.py
           ┌┴───────────┴┐
          │ 集成测试     │  ← test_graph_supervisor_alignment.py
         ┌┴─────────────┴┐
        │   单元测试       │  ← test_repositories.py, test_container.py,
        │                │      test_product_rec_agent.py
        └────────────────┘
```

---

### 4.2 单元测试要点

**Repository 测试**：
```python
def test_get_by_ids():
    repo = InMemoryProductRepository()
    products = asyncio.run(repo.get_by_ids(["P001", "P002"]))
    assert len(products) == 2
    assert products[0].product_id == "P001"
```

**Container 测试**：
```python
def test_container_set_product_repo():
    container = AppContainer()
    custom_repo = MockProductRepository()
    container.set_product_repo(custom_repo)
    assert container.product_repo is custom_repo
```

**Agent 测试**：
```python
def test_recall_with_profile():
    container = AppContainer(Settings())
    agent = ProductRecAgent(container=container)
    profile = UserProfile(preferred_categories=["手机"])
    result = asyncio.run(agent.run(user_profile=profile, num_items=5))
    assert result.success is True
    assert len(result.products) == 5
```

---

### 4.3 运行测试

```bash
cd python

# 运行单个测试文件
python tests/test_repositories.py

# 运行所有测试
python -m pytest tests/ -v

# 查看覆盖率
python -m pytest tests/ --cov=. --cov-report=html
```

---

## 五、扩展指南

### 5.1 添加新的数据源

```python
# 1. 创建新的 Repository 实现
class DatabaseProductRepository(ProductRepository):
    def __init__(self, db_url: str):
        self._db_url = db_url
    
    async def get_by_ids(self, ids):
        # 实现真实数据库查询

# 2. 修改 AppContainer
class AppContainer:
    @property
    def product_repo(self):
        if self._product_repo is None:
            self._product_repo = DatabaseProductRepository(
                db_url=self._settings.database_url
            )
        return self._product_repo
```

---

### 5.2 添加新的 Agent

```python
# 1. 创建 Agent 类
class ReviewAgent(BaseAgent):
    async def _execute(self, **kwargs):
        # 实现商品评价生成

# 2. 在 Supervisor 中注册
class SupervisorOrchestrator:
    def __init__(self):
        self.review_agent = ReviewAgent()
    
    async def recommend(self, request):
        # 在适当阶段调用
        review_result = await self.review_agent.run(...)
```

---

### 5.3 添加新的 A/B 实验

```python
# 在 ABTestEngine 中注册
ab_engine.register_experiment(
    Experiment(
        id="new_rerank_strategy",
        name="新重排策略实验",
        groups=[
            ExperimentGroup(name="control", weight=50),
            ExperimentGroup(name="treatment", weight=50),
        ],
    )
)
```

---

## 六、常见问题

### Q1: 为什么使用依赖注入？

**答**：
- 解耦 Agent 和具体实现
- 便于测试（可注入 Mock）
- 便于切换数据源（开发→生产）

### Q2: 降级策略如何工作？

**答**：
- 各服务检查 `_client` 是否为 None
- 不可用时返回空列表或默认值
- 上层使用兜底策略（如热门商品）

### Q3: explain 字段的作用？

**答**：
- 展示推荐理由（命中偏好类目、价格匹配等）
- 前端可据此展示个性化提示
- 便于 A/B 测试分析

### Q4: Supervisor 和 Graph 有什么区别？

**答**：
- **Supervisor**: 代码编排，灵活控制
- **Graph**: 状态机编排，可视化好
- 两者输出对齐，前端可复用

---

**文档版本**: 1.0  
**最后更新**: 2026-04-27
