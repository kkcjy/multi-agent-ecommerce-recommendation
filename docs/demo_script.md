# 演示脚本：如何从 toy 切换到真实服务

## 架构重构说明

本次重构将推荐链路从 mock 驱动升级为"可替换真实数据源"的架构。

---

## 一、重构前后对比

### 重构前
```python
# agents/product_rec_agent.py
MOCK_PRODUCTS = [
    Product(product_id="P001", name="iPhone 16 Pro", ...),
    Product(product_id="P002", name="华为 Mate 70", ...),
    ...
]

class ProductRecAgent:
    def __init__(self):
        # 硬编码在 Agent 内部
        self.products = MOCK_PRODUCTS
```

### 重构后
```python
# repositories/in_memory_product_repository.py
class InMemoryProductRepository(ProductRepository):
    """Mock 数据移到了这里"""

# agents/product_rec_agent.py
class ProductRecAgent:
    def __init__(self, container: AppContainer = None):
        # 通过容器注入，可在生产环境替换
        self._container = container
    
    @property
    def product_repo(self):
        return self._container.product_repo if self._container else InMemoryProductRepository()
```

---

## 二、切换真实服务步骤

### 步骤 1: 创建真实数据源实现

```python
# repositories/database_product_repository.py
from repositories.product_repository import ProductRepository

class DatabaseProductRepository(ProductRepository):
    """数据库实现 - 生产环境使用"""
    
    def __init__(self, db_url: str):
        self._db_url = db_url
    
    async def get_by_ids(self, ids: list[str]) -> list[Product]:
        # 从真实数据库查询
        async with create_engine(self._db_url) as conn:
            results = await conn.execute(
                "SELECT * FROM products WHERE id IN :ids",
                {"ids": ids}
            )
            return [self._to_product(row) for row in results]
    
    # ... 其他方法实现
```

### 步骤 2: 修改容器配置

```python
# containers/app_container.py
class AppContainer:
    @property
    def product_repo(self) -> ProductRepository:
        if self._product_repo is None:
            # 开发环境：使用 InMemoryProductRepository
            # self._product_repo = InMemoryProductRepository()
            
            # 生产环境：使用 DatabaseProductRepository
            self._product_repo = DatabaseProductRepository(
                db_url=self._settings.database_url
            )
        return self._product_repo
```

### 步骤 3: 配置向量服务 (可选)

```python
# containers/app_container.py
class AppContainer:
    @property
    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            # 生产环境：创建 Milvus 客户端
            from pymilvus import connections, MilvusClient
            
            connections.connect(host="milvus.server.com", port="19530")
            milvus_client = MilvusClient()
            
            self._vector_store = VectorStore(
                milvus_client=milvus_client,
                collection_name=self._settings.milvus_collection
            )
        return self._vector_store
```

### 步骤 4: 配置库存服务 (可选)

```python
# containers/app_container.py
class AppContainer:
    @property
    def inventory_db(self) -> InventoryDB:
        if self._inventory_db is None:
            # 生产环境：创建数据库连接
            from sqlalchemy import create_engine
            engine = create_engine(self._settings.database_url)
            
            self._inventory_db = InventoryDB(db_client=engine)
        return self._inventory_db
```

---

## 三、环境变量配置

创建 `.env` 文件：

```bash
# LLM 配置
ECOM_LLM_API_KEY=your_api_key
ECOM_LLM_BASE_URL=https://api.example.com
ECOM_LLM_MODEL=gpt-4

# Redis 配置 (FeatureStore 使用)
ECOM_REDIS_URL=redis://redis.server.com:6379/0

# Milvus 配置 (VectorStore 使用)
ECOM_MILVUS_HOST=milvus.server.com
ECOM_MILVUS_PORT=19530
ECOM_MILVUS_COLLECTION=product_embeddings

# 数据库配置
ECOM_DATABASE_URL=postgresql://user:pass@db.server.com/ecommerce
```

---

## 四、运行模式

### 开发模式 (当前默认)

```bash
# 使用 Mock 数据，所有服务降级
python main.py
```

特点：
- 数据源：InMemoryProductRepository (Mock 数据)
- 向量服务：降级 (返回空列表)
- 库存服务：降级 (假设全部有货)
- 特征存储：降级 (内存模式)

### 生产模式

```bash
# 配置环境变量后启动
export ECOM_DATABASE_URL=postgresql://...
export ECOM_REDIS_URL=redis://...
export ECOM_MILVUS_HOST=...
python main.py
```

特点：
- 数据源：DatabaseProductRepository
- 向量服务：Milvus 真实查询
- 库存服务：真实数据库查询
- 特征存储：Redis 实时特征

---

## 五、验证切换

### 1. 运行测试

```bash
# 运行所有单元测试
cd python
pytest tests/ -v

# 预期输出:
# test_repositories.py ........ PASSED
# test_container.py ........... PASSED
# test_product_rec_agent.py ... PASSED
# test_supervisor_integration.py . PASSED
```

### 2. API 测试

```bash
# 健康检查
curl http://localhost:8000/health

# 推荐接口
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","scene":"homepage","num_items":5}'
```

响应示例：

```json
{
  "request_id": "59b9428c-3d90-4cf4-b5d4-aa18300eb304",
  "user_id": "u1",
  "products": [
    {
      "product_id": "P001",
      "name": "iPhone 16 Pro",
      "category": "手机",
      "price": 7999,
      "explain": {
        "recall_source": "category",
        "matched_category": true,
        "price_matched": true,
        "matched_tags": ["旗舰", "新品"]
      }
    }
  ],
  "experiment_group": "control",
  "total_latency_ms": 1379.4
}
```

---

## 六、验收标准检查

| 验收项 | 状态 | 验证方法 |
|--------|------|---------|
| Mock 常量不再硬编码在 Agent | ✅ | `grep -r "MOCK_PRODUCTS" agents/` 无结果 |
| 数据源不可用时降级 | ✅ | `test_fallback_when_empty` 测试通过 |
| 两条接口字段一致 | ✅ | `test_graph_and_supervisor_output_aligned` 通过 |
| 至少 3 条单元测试 | ✅ | 已创建 13+ 条测试 |
| 架构文档 | ✅ | `docs/architecture/system_architecture.md` |
| 演示脚本 | ✅ | 本文档 |

---

## 七、文件清单

### 新建文件

```
python/
├── repositories/
│   ├── __init__.py
│   ├── product_repository.py         # 抽象基类
│   └── in_memory_product_repository.py # Mock 实现
├── containers/
│   ├── __init__.py
│   └── app_container.py              # 依赖注入容器
├── services/
│   ├── vector_store.py               # 向量检索服务
│   └── inventory_db.py               # 库存查询服务
└── tests/
    ├── test_repositories.py          # Repository 测试
    ├── test_container.py             # 容器测试
    ├── test_product_rec_agent.py     # Agent 测试
    └── test_supervisor_integration.py # 集成测试

docs/
└── architecture/
    └── system_architecture.md        # 系统架构文档
```

### 修改文件

```
python/
├── agents/
│   └── product_rec_agent.py          # 添加容器注入 + explain 字段
├── orchestrator/
│   ├── supervisor.py                 # 使用容器注入
│   └── graph.py                      # 使用容器注入 + 输出对齐
├── models/
│   └── schemas.py                    # Product 添加 explain 字段
└── main.py                           # 初始化容器并注入
```
