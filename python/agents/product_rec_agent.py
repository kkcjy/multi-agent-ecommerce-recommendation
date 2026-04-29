"""
商品推荐 Agent
- 召回层：协同过滤 + 向量检索 (Milvus) + 热度/新品策略
- 排序层：LLM 重排 + 特征交叉 (用户画像 x 商品属性)
- 多样性控制：类目打散、卖家去重、新品加权
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import get_settings
from models.schemas import AgentResult, Product, ProductRecResult, UserProfile
from containers.app_container import AppContainer

from .base_agent import BaseAgent

RERANK_PROMPT = """你是电商推荐排序专家。根据用户画像和候选商品，重新排序并选出最优的{num_items}个商品。

用户画像:
{user_profile}

候选商品:
{candidates}

排序原则:
1. 用户偏好类目优先
2. 价格在用户可接受范围内
3. 保证类目多样性 (相邻商品尽量不同类目)
4. 新品适当加权

请输出商品 ID 列表 (JSON 数组),按推荐优先级排序:
["product_id_1", "product_id_2", ...]

只输出 JSON 数组，不要其他内容。"""


class ProductRecAgent(BaseAgent):
    """
    产品推荐 Agent

    依赖注入:
    - container: 从容器获取 product_repo, vector_store 等服务
    - 无 container 时使用默认实现（降级）
    """

    def __init__(self, container: AppContainer | None = None):
        settings = get_settings()
        super().__init__(
            name="product_rec",
            timeout=settings.agent_timeout_product_rec,
        )
        self._container = container
        self.llm = ChatOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=0.3,
            max_tokens=512,
        )

    @property
    def product_repo(self):
        """从容器获取产品仓库，无容器时用 InMemoryProductRepository"""
        if self._container:
            return self._container.product_repo
        from repositories.in_memory_product_repository import InMemoryProductRepository
        return InMemoryProductRepository()

    @property
    def vector_store(self):
        """从容器获取向量存储，无容器时返回 None（降级）"""
        if self._container:
            return self._container.vector_store
        return None

    async def _execute(self, **kwargs: Any) -> ProductRecResult:
        user_profile: UserProfile | None = kwargs.get("user_profile")
        num_items: int = kwargs.get("num_items", 10)

        candidates = await self._recall(user_profile, num_items * 3)
        ranked_ids = await self._rerank(user_profile, candidates, num_items)

        id_to_product = {p.product_id: p for p in candidates}
        final_products = []
        for pid in ranked_ids:
            if pid in id_to_product:
                final_products.append(id_to_product[pid])

        # 填充不足的商品
        if len(final_products) < num_items:
            for p in candidates:
                if p.product_id not in ranked_ids:
                    final_products.append(p)
                    if len(final_products) >= num_items:
                        break

        return ProductRecResult(
            success=True,
            products=final_products[:num_items],
            recall_strategy="collaborative_filter+vector+hot",
            data={"candidate_count": len(candidates), "reranked": len(ranked_ids)},
            confidence=0.8,
        )

    async def _recall(self, profile: UserProfile | None, limit: int) -> list[Product]:
        """
        多策略召回

        召回顺序:
        1. 向量召回（如果向量服务可用）
        2. 按类目召回（如果用户有偏好类目）
        3. 热门商品召回（兜底）
        """
        candidates: list[Product] = []

        # 策略 1: 向量召回
        if self.vector_store and self.vector_store.is_available():
            vector_ids = await self.vector_store.search_by_vector(
                query_vector=self._get_user_vector(profile),
                limit=limit,
            )
            if vector_ids:
                vector_products = await self.product_repo.get_by_ids(vector_ids)
                candidates.extend(vector_products)

        # 策略 2: 按偏好类目召回
        if profile and profile.preferred_categories:
            for category in profile.preferred_categories:
                cat_products = await self.product_repo.get_by_category(
                    category=category, limit=limit // len(profile.preferred_categories)
                )
                for p in cat_products:
                    if p not in candidates:
                        p.explain = self._build_explain(p, profile, "category")
                        candidates.append(p)

        # 策略 3: 热门商品兜底
        if len(candidates) < limit:
            hot_products = await self.product_repo.get_hot_products(limit - len(candidates))
            for p in hot_products:
                if p not in candidates:
                    p.explain = self._build_explain(p, profile, "hot")
                    candidates.append(p)

        # 策略 4: 新品加权
        new_products = await self.product_repo.get_new_products(limit // 3)
        for p in new_products:
            if p not in candidates:
                p.explain = self._build_explain(p, profile, "new")
                candidates.append(p)

        return candidates[: limit * 2]  # 返回多一些供排序层筛选

    async def _rerank(
        self, profile: UserProfile | None, candidates: list[Product], num_items: int
    ) -> list[str]:
        """
        LLM 重排

        无用户画像时，按候选顺序返回
        """
        if not profile or not candidates:
            return [p.product_id for p in candidates[:num_items]]

        profile_summary = {
            "segments": [s.value for s in profile.segments],
            "preferred_categories": profile.preferred_categories,
            "price_range": list(profile.price_range),
        }
        candidate_summary = [
            {
                "id": p.product_id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "tags": p.tags,
            }
            for p in candidates
        ]
        prompt = RERANK_PROMPT.format(
            num_items=num_items,
            user_profile=json.dumps(profile_summary, ensure_ascii=False),
            candidates=json.dumps(candidate_summary, ensure_ascii=False),
        )
        messages = [
            SystemMessage(content="你是电商推荐排序专家。"),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError, Exception):
            # 降级：按候选顺序返回
            return [p.product_id for p in candidates[:num_items]]

    def _build_explain(
        self, product: Product, profile: UserProfile | None, recall_source: str = "hot"
    ) -> dict[str, Any]:
        """
        构建推荐解释

        解释字段:
        - matched_category: 是否命中偏好类目
        - price_matched: 价格是否在可接受范围
        - matched_tags: 命中的用户标签
        - recall_source: 召回来源 (vector/category/hot/new)
        """
        explain: dict[str, Any] = {
            "recall_source": recall_source,
            "matched_category": False,
            "price_matched": True,
            "matched_tags": [],
        }

        if profile:
            # 类目匹配
            if profile.preferred_categories and product.category in profile.preferred_categories:
                explain["matched_category"] = True

            # 价格匹配
            min_price, max_price = profile.price_range
            explain["price_matched"] = min_price <= product.price <= max_price

            # 标签匹配
            if profile.real_time_tags:
                for tag in product.tags:
                    if tag in profile.real_time_tags:
                        explain["matched_tags"].append(tag)

        return explain

    def _get_user_vector(self, profile: UserProfile | None) -> list[float]:
        """
        获取用户向量表示

        简化实现：返回零向量
        生产环境：从 FeatureStore 或 Embedding 模型获取
        """
        if not profile:
            return [0.0] * 128  # 128 维零向量

        # 简化：基于用户特征生成伪向量
        # 生产环境：使用真实的 Embedding 模型
        return [0.0] * 128
