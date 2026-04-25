"""Container layer tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import Settings
from containers.app_container import AppContainer
from repositories.in_memory_product_repository import InMemoryProductRepository
from services.vector_store import VectorStore
from services.inventory_db import InventoryDB
from services.feature_store import FeatureStore


class TestAppContainer:
    """AppContainer 单元测试"""

    def test_container_settings(self):
        """测试容器配置"""
        settings = Settings()
        container = AppContainer(settings=settings)
        assert container.settings is settings

    def test_container_product_repo_singleton(self):
        """测试产品仓库懒加载和单例"""
        container = AppContainer()
        repo1 = container.product_repo
        repo2 = container.product_repo
        assert repo1 is repo2  # 单例
        assert isinstance(repo1, InMemoryProductRepository)

    def test_container_vector_store(self):
        """测试向量存储"""
        container = AppContainer()
        vector_store = container.vector_store
        assert vector_store is not None
        assert isinstance(vector_store, VectorStore)

    def test_container_inventory_db(self):
        """测试库存数据库"""
        container = AppContainer()
        inventory_db = container.inventory_db
        assert inventory_db is not None
        assert isinstance(inventory_db, InventoryDB)

    def test_container_feature_store(self):
        """测试特征存储"""
        container = AppContainer()
        feature_store = container.feature_store
        assert feature_store is not None
        assert isinstance(feature_store, FeatureStore)

    def test_container_reset(self):
        """测试重置容器"""
        container = AppContainer()
        _ = container.product_repo
        _ = container.vector_store
        container.reset()
        # 重置后应该可以重新创建
        assert container._product_repo is None
        assert container._vector_store is None

    def test_container_set_product_repo(self):
        """测试注入自定义产品仓库（用于测试）"""
        container = AppContainer()
        custom_repo = InMemoryProductRepository()
        container.set_product_repo(custom_repo)
        assert container.product_repo is custom_repo

    def test_container_set_vector_store(self):
        """测试注入自定义向量存储（用于测试）"""
        container = AppContainer()
        custom_vector_store = VectorStore()
        container.set_vector_store(custom_vector_store)
        assert container.vector_store is custom_vector_store

    def test_container_set_inventory_db(self):
        """测试注入自定义库存数据库（用于测试）"""
        container = AppContainer()
        custom_inventory_db = InventoryDB()
        container.set_inventory_db(custom_inventory_db)
        assert container.inventory_db is custom_inventory_db

    def test_container_set_feature_store(self):
        """测试注入自定义特征存储（用于测试）"""
        container = AppContainer()
        custom_feature_store = FeatureStore()
        container.set_feature_store(custom_feature_store)
        assert container.feature_store is custom_feature_store


if __name__ == "__main__":
    test = TestAppContainer()
    test.test_container_settings()
    test.test_container_product_repo_singleton()
    test.test_container_vector_store()
    test.test_container_inventory_db()
    test.test_container_feature_store()
    test.test_container_reset()
    test.test_container_set_product_repo()
    test.test_container_set_vector_store()
    test.test_container_set_inventory_db()
    test.test_container_set_feature_store()
    print("All Container tests passed!")
