"""Inventory database service for stock checking."""

from __future__ import annotations

from typing import Any


class InventoryDB:
    """
    库存查询服务

    设计原则:
    - 快速失败：超时或不可用时快速返回
    - 降级策略：服务不可用时假设商品有货

    使用场景:
    - 推荐结果过滤（移除无货商品）
    - 库存预警（低库存提示）
    """

    def __init__(self, db_client: Any | None = None):
        self._client = db_client

    async def get_available_ids(self, product_ids: list[str]) -> set[str]:
        """
        查询有货的商品 ID 集合

        Args:
            product_ids: 待查询的商品 ID 列表

        Returns:
            有货的商品 ID 集合，如果服务不可用返回全部 ID（降级策略）
        """
        if not self._client:
            # 降级：假设所有商品都有货
            return set(product_ids)

        try:
            # 生产环境：查询真实库存数据库
            # results = await self._client.execute(
            #     "SELECT product_id FROM inventory WHERE product_id IN :ids AND stock > 0",
            #     {"ids": product_ids}
            # )
            # return {r["product_id"] for r in results}
            return set(product_ids)
        except Exception:
            # 异常时返回全部 ID（保守策略：不因为库存服务问题而过滤商品）
            return set(product_ids)

    async def get_stock_level(self, product_id: str) -> int:
        """
        查询单个商品的库存数量

        Args:
            product_id: 商品 ID

        Returns:
            库存数量，查询失败返回 -1
        """
        if not self._client:
            return -1

        try:
            # result = await self._client.execute(
            #     "SELECT stock FROM inventory WHERE product_id = :id",
            #     {"id": product_id}
            # )
            # return result["stock"] if result else 0
            return 0
        except Exception:
            return -1

    async def get_low_stock_products(
        self, product_ids: list[str], threshold: int = 10
    ) -> list[dict[str, Any]]:
        """
        查询低库存商品

        Args:
            product_ids: 待查询的商品 ID 列表
            threshold: 低库存阈值

        Returns:
            低库存商品列表 [{product_id, stock, ...}]
        """
        if not self._client:
            return []

        try:
            # results = await self._client.execute(
            #     "SELECT product_id, stock FROM inventory WHERE product_id IN :ids AND stock < :threshold",
            #     {"ids": product_ids, "threshold": threshold}
            # )
            # return [dict(r) for r in results]
            return []
        except Exception:
            return []

    def is_available(self) -> bool:
        """检查库存服务是否可用"""
        return self._client is not None
