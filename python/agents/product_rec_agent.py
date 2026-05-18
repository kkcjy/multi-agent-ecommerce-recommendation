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
            temperature=0.1,
            max_tokens=200,  # JSON 输出不需要太多 tokens
            extra_body={"enable_thinking": settings.llm_enable_thinking},
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
        scene: str | None = kwargs.get("scene")
        context: dict | None = kwargs.get("context", {})

        candidates = await self._recall(user_profile, num_items * 3, scene=scene, context=context)
        ranked_ids = await self._rerank(user_profile, candidates, num_items, scene=scene)

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

        strategy_map = {
            "hot": "hot_scene",
            "new": "new_scene",
            "intent": "intent_category",
            "personal": "personalized_full",
        }
        default_strategy = "collaborative_filter+vector+hot"

        return ProductRecResult(
            success=True,
            products=final_products[:num_items],
            recall_strategy=strategy_map.get(scene or "", default_strategy),
            data={"candidate_count": len(candidates), "reranked": len(ranked_ids)},
            confidence=0.8,
        )

    async def _recall(
        self, profile: UserProfile | None, limit: int,
        scene: str | None = None, context: dict | None = None,
    ) -> list[Product]:
        """
        多策略召回，根据 scene 选择不同策略:

        - hot:  热门商品（按库存排序）
        - new:  新品首发（tags 含"新品"）
        - intent:  搜索意图（从 context.recent_views 提取类目召回）
        - personal:  全个性化（向量 + profile 类目 + 热门兜底 + 新品加权）
        - 默认:  保持原有全策略逻辑
        """
        if scene == "hot":
            return await self._recall_hot(profile, limit)
        elif scene == "new":
            return await self._recall_new(profile, limit)
        elif scene == "intent":
            return await self._recall_intent(profile, limit, context)
        elif scene == "personal":
            return await self._recall_default(profile, limit)
        else:
            return await self._recall_default(profile, limit)

    async def _recall_hot(self, profile: UserProfile | None, limit: int) -> list[Product]:
        """热门商品召回"""
        candidates: list[Product] = []
        hot_products = await self.product_repo.get_hot_products(limit)
        for p in hot_products:
            p.explain = self._build_explain(p, profile, "hot")
            candidates.append(p)
        return candidates

    async def _recall_new(self, profile: UserProfile | None, limit: int) -> list[Product]:
        """新品首发召回，不足时用热门商品补充"""
        candidates: list[Product] = []
        new_products = await self.product_repo.get_new_products(limit)
        for p in new_products:
            p.explain = self._build_explain(p, profile, "new")
            candidates.append(p)

        if len(candidates) < limit:
            hot_products = await self.product_repo.get_hot_products(limit - len(candidates))
            for p in hot_products:
                if p not in candidates:
                    p.explain = self._build_explain(p, profile, "hot")
                    candidates.append(p)
        return candidates

    async def _recall_intent(
        self, profile: UserProfile | None, limit: int, context: dict | None,
    ) -> list[Product]:
        """搜索意图召回：从 recent_views 或 profile 提取类目，按类目匹配商品"""
        candidates: list[Product] = []

        categories: list[str] = []
        if profile and profile.preferred_categories:
            categories = profile.preferred_categories
        elif context:
            recent = context.get("recent_views", [])
            for item in recent:
                item_str = str(item).strip()
                if item_str and item_str not in categories:
                    categories.append(item_str)

        if categories:
            per_cat = max(1, limit // len(categories))
            for category in categories:
                cat_products = await self.product_repo.get_by_category(category, per_cat)
                for p in cat_products:
                    if p not in candidates:
                        p.explain = self._build_explain(p, profile, "category")
                        candidates.append(p)

        if len(candidates) < limit:
            # 无类目信息时，返回多类目混搭商品作为兜底，避免与 hot 场景重复
            all_products = await self.product_repo.get_all_products(limit * 2)
            for p in all_products:
                if p not in candidates:
                    p.explain = self._build_explain(p, profile, "diverse")
                    candidates.append(p)
                    if len(candidates) >= limit:
                        break

        return candidates[:limit * 2]

    async def _recall_default(self, profile: UserProfile | None, limit: int) -> list[Product]:
        """
        原有全策略召回

        召回顺序:
        1. 向量召回（如果向量服务可用）
        2. 按类目召回（如果用户有偏好类目）
        3. 热门商品召回（兜底）
        4. 新品加权
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

        return candidates[: limit * 2]

    async def _rerank(
        self, profile: UserProfile | None, candidates: list[Product], num_items: int,
        scene: str | None = None,
    ) -> list[str]:
        """
        规则重排（优先保证速度）

        hot/new 场景保持召回顺序，不做 profile 重排
        intent/personal 场景按类目匹配度、价格匹配度排序
        """
        if not profile or not candidates:
            return [p.product_id for p in candidates[:num_items]]

        # hot / new 场景保持召回原始排序
        if scene in ("hot", "new"):
            return [p.product_id for p in candidates[:num_items]]

        # 规则排序：匹配用户偏好的商品优先
        def score_product(p: Product) -> tuple:
            cat_match = 1 if profile.preferred_categories and p.category in profile.preferred_categories else 0
            min_price, max_price = profile.price_range
            price_match = 1 if min_price <= p.price <= max_price else 0
            return (-cat_match, -price_match, p.price)  # 类目优先，价格次之

        sorted_candidates = sorted(candidates, key=score_product)
        return [p.product_id for p in sorted_candidates[:num_items]]

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
