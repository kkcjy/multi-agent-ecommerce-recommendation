"""Product repository abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.schemas import Product


class ProductRepository(ABC):
    """
    产品数据仓库抽象层

    设计原则:
    - 接口隔离：不同召回策略对应不同方法
    - 依赖倒置：上层依赖抽象，不依赖具体实现
    - 可降级：实现类可选择返回空列表而非抛异常
    """

    @abstractmethod
    async def get_by_ids(self, ids: list[str]) -> list[Product]:
        """根据 ID 批量查询商品"""
        pass

    @abstractmethod
    async def get_by_category(self, category: str, limit: int = 10) -> list[Product]:
        """按类目查询商品"""
        pass

    @abstractmethod
    async def get_by_price_range(
        self, min_price: float, max_price: float, limit: int = 10
    ) -> list[Product]:
        """按价格区间查询商品"""
        pass

    @abstractmethod
    async def get_hot_products(self, limit: int = 10) -> list[Product]:
        """获取热门商品（按销量/热度排序）"""
        pass

    @abstractmethod
    async def get_new_products(self, limit: int = 10) -> list[Product]:
        """获取新品（按上架时间排序）"""
        pass

    @abstractmethod
    async def get_all_products(self, limit: int = 100) -> list[Product]:
        """获取所有商品（用于降级场景）"""
        pass
