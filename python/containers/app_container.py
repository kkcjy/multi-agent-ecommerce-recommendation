"""Application container for dependency injection."""

from __future__ import annotations

from services.feature_store import FeatureStore
from services.vector_store import VectorStore
from services.inventory_db import InventoryDB
from repositories.product_repository import ProductRepository
from repositories.in_memory_product_repository import InMemoryProductRepository
from config.settings import Settings


class AppContainer:
    """
    统一依赖注入容器

    职责:
    - 集中管理所有服务的生命周期
    - 提供懒加载能力（首次访问才创建实例）
    - 支持服务替换（测试时可注入 mock）

    使用示例:
        container = AppContainer(settings)
        repo = container.product_repo
        vector_store = container.vector_store
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings

        # 核心服务（懒加载）
        self._product_repo: ProductRepository | None = None
        self._vector_store: VectorStore | None = None
        self._inventory_db: InventoryDB | None = None
        self._feature_store: FeatureStore | None = None

    @property
    def settings(self) -> Settings | None:
        """获取配置"""
        return self._settings

    @property
    def product_repo(self) -> ProductRepository:
        """
        产品数据仓库

        当前使用 InMemoryProductRepository（开发/降级用）
        生产环境可切换为 DatabaseProductRepository
        """
        if self._product_repo is None:
            self._product_repo = InMemoryProductRepository()
        return self._product_repo

    @property
    def vector_store(self) -> VectorStore:
        """
        向量检索服务

        当前为降级模式（无 Milvus 客户端）
        生产环境注入 Milvus 客户端
        """
        if self._vector_store is None:
            self._vector_store = VectorStore(
                milvus_client=None,  # 生产环境：创建 Milvus 客户端
                collection_name=self._settings.milvus_collection if self._settings else "product_embeddings",
            )
        return self._vector_store

    @property
    def inventory_db(self) -> InventoryDB:
        """
        库存查询服务

        当前为降级模式（无数据库客户端）
        生产环境注入 SQLAlchemy 或其他数据库客户端
        """
        if self._inventory_db is None:
            self._inventory_db = InventoryDB(db_client=None)
        return self._inventory_db

    @property
    def feature_store(self) -> FeatureStore:
        """
        实时特征存储服务

        当前为降级模式（无 Redis 客户端）
        生产环境注入 Redis 客户端
        """
        if self._feature_store is None:
            self._feature_store = FeatureStore(redis_client=None)
        return self._feature_store

    def reset(self):
        """重置所有服务（用于测试）"""
        self._product_repo = None
        self._vector_store = None
        self._inventory_db = None
        self._feature_store = None

    def set_product_repo(self, repo: ProductRepository):
        """设置产品仓库（用于测试注入）"""
        self._product_repo = repo

    def set_vector_store(self, vector_store: VectorStore):
        """设置向量存储（用于测试注入）"""
        self._vector_store = vector_store

    def set_inventory_db(self, inventory_db: InventoryDB):
        """设置库存数据库（用于测试注入）"""
        self._inventory_db = inventory_db

    def set_feature_store(self, feature_store: FeatureStore):
        """设置特征存储（用于测试注入）"""
        self._feature_store = feature_store
