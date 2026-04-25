"""Repository layer tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from repositories.in_memory_product_repository import InMemoryProductRepository, MOCK_PRODUCTS


class TestInMemoryProductRepository:
    """InMemoryProductRepository 单元测试"""

    def test_get_by_ids(self):
        """测试根据 ID 批量查询"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_by_ids(["P001", "P002"]))
        assert len(products) == 2
        assert products[0].product_id == "P001"
        assert products[1].product_id == "P002"

    def test_get_by_ids_not_found(self):
        """测试查询不存在的 ID"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_by_ids(["NON_EXISTENT"]))
        assert products == []

    def test_get_by_ids_partial_match(self):
        """测试部分 ID 存在"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_by_ids(["P001", "NON_EXISTENT"]))
        assert len(products) == 1
        assert products[0].product_id == "P001"

    def test_get_by_category(self):
        """测试按类目查询"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_by_category("手机", limit=5))
        assert len(products) > 0
        assert all(p.category == "手机" for p in products)

    def test_get_by_category_not_found(self):
        """测试查询不存在的类目"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_by_category("不存在的类目", limit=5))
        assert products == []

    def test_get_by_price_range(self):
        """测试按价格区间查询"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_by_price_range(0, 1000, limit=10))
        assert len(products) > 0
        assert all(0 <= p.price <= 1000 for p in products)

    def test_get_hot_products(self):
        """测试获取热门商品"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_hot_products(limit=5))
        assert len(products) == 5
        # 热门商品按 stock 降序
        for i in range(len(products) - 1):
            assert products[i].stock >= products[i + 1].stock

    def test_get_new_products(self):
        """测试获取新品"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_new_products(limit=5))
        assert len(products) > 0
        assert all("新品" in p.tags for p in products)

    def test_get_all_products(self):
        """测试获取所有商品"""
        repo = InMemoryProductRepository()
        products = asyncio.run(repo.get_all_products(limit=100))
        assert len(products) == len(MOCK_PRODUCTS)

    def test_fallback_when_empty(self):
        """验收标准：数据源为空时，降级返回空列表而非报错"""
        repo = InMemoryProductRepository(products=[])
        products = asyncio.run(repo.get_by_ids(["P001"]))
        assert products == []


if __name__ == "__main__":
    test = TestInMemoryProductRepository()
    test.test_get_by_ids()
    test.test_get_by_ids_not_found()
    test.test_get_by_ids_partial_match()
    test.test_get_by_category()
    test.test_get_by_category_not_found()
    test.test_get_by_price_range()
    test.test_get_hot_products()
    test.test_get_new_products()
    test.test_get_all_products()
    test.test_fallback_when_empty()
    print("All Repository tests passed!")
