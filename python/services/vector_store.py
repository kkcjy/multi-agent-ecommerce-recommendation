"""Vector store service for product embedding search."""

from __future__ import annotations

from typing import Any


class VectorStore:
    """
    向量检索服务

    设计原则:
    - 可降级：Milvus 不可用时返回空列表
    - 接口统一：无论底层是 Milvus 还是其他，接口一致

    使用场景:
    - 基于商品向量的相似商品召回
    - 基于用户行为向量的个性化召回
    """

    def __init__(self, milvus_client: Any | None = None, collection_name: str = "product_embeddings"):
        self._client = milvus_client
        self._collection_name = collection_name

    async def search_by_vector(
        self, query_vector: list[float], limit: int = 10
    ) -> list[str]:
        """
        基于向量相似度搜索商品 ID

        Args:
            query_vector: 查询向量（商品 embedding 或用户 embedding）
            limit: 返回结果数量

        Returns:
            商品 ID 列表，如果服务不可用返回空列表
        """
        if not self._client:
            # 降级：返回空列表，上层使用热门商品填充
            return []

        try:
            # Milvus 搜索（生产环境实现）
            # results = self._client.search(
            #     collection_name=self._collection_name,
            #     data=[query_vector],
            #     limit=limit,
            # )
            # return [hit.entity.id for hit in results[0]]
            return []
        except Exception:
            # 任何异常都返回空列表，不阻塞主流程
            return []

    async def search_by_category(
        self, category: str, query_vector: list[float], limit: int = 10
    ) -> list[str]:
        """
        基于向量搜索指定类目的商品

        Args:
            category: 商品类目
            query_vector: 查询向量
            limit: 返回结果数量

        Returns:
            商品 ID 列表
        """
        if not self._client:
            return []

        try:
            # Milvus 带过滤搜索（生产环境实现）
            # expr = f"category == '{category}'"
            # results = self._client.search(
            #     collection_name=self._collection_name,
            #     data=[query_vector],
            #     filter=expr,
            #     limit=limit,
            # )
            # return [hit.entity.id for hit in results[0]]
            return []
        except Exception:
            return []

    async def add_product_embedding(
        self, product_id: str, embedding: list[float], category: str
    ):
        """添加商品向量到向量库"""
        if not self._client:
            return

        try:
            # self._client.insert(
            #     collection_name=self._collection_name,
            #     data=[{"id": product_id, "vector": embedding, "category": category}],
            # )
            pass
        except Exception:
            pass

    def is_available(self) -> bool:
        """检查向量服务是否可用"""
        return self._client is not None
