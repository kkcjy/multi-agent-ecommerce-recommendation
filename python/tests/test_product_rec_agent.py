"""ProductRecAgent tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from config.settings import Settings
from containers.app_container import AppContainer
from agents.product_rec_agent import ProductRecAgent
from models.schemas import UserProfile, UserSegment


class TestProductRecAgent:
    """ProductRecAgent 单元测试"""

    def test_agent_init_with_container(self):
        """测试 Agent 使用容器初始化"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)
        assert agent._container is container

    def test_agent_init_without_container(self):
        """测试 Agent 无容器时降级"""
        agent = ProductRecAgent()
        assert agent._container is None
        # 应该仍然可以获取 product_repo（降级模式）
        repo = agent.product_repo
        assert repo is not None

    def test_recall_with_profile(self):
        """测试有用户画像时的召回"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)

        profile = UserProfile(
            user_id="u1",
            preferred_categories=["手机"],
            price_range=(0, 8000),
        )
        result = asyncio.run(agent.run(user_profile=profile, num_items=5))

        assert result.success is True
        assert len(result.products) == 5

    def test_recall_without_profile(self):
        """测试无用户画像时的召回（热门商品）"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)

        result = asyncio.run(agent.run(user_profile=None, num_items=5))

        assert result.success is True
        assert len(result.products) == 5

    def test_explain_field_present(self):
        """验收标准：推荐结果包含 explain 字段"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)

        profile = UserProfile(
            user_id="u1",
            preferred_categories=["耳机"],
            segments=[UserSegment.HIGH_VALUE],
        )
        result = asyncio.run(agent.run(user_profile=profile, num_items=3))

        for product in result.products:
            assert "explain" in product.model_dump()
            assert isinstance(product.explain, dict)

    def test_explain_recall_source(self):
        """验收标准：explain 字段包含召回来源"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)

        profile = UserProfile(
            user_id="u1",
            preferred_categories=["手机"],
        )
        result = asyncio.run(agent.run(user_profile=profile, num_items=3))

        for product in result.products:
            assert "recall_source" in product.explain
            assert product.explain["recall_source"] in ["category", "hot", "new", "vector"]

    def test_explain_matched_category(self):
        """验收标准：explain 字段包含类目匹配信息"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)

        profile = UserProfile(
            user_id="u1",
            preferred_categories=["手机"],
            price_range=(0, 10000),
        )
        result = asyncio.run(agent.run(user_profile=profile, num_items=5))

        # 至少有一个商品匹配了类目
        matched = any(p.explain.get("matched_category") for p in result.products)
        assert matched is True

    def test_explain_price_matched(self):
        """验收标准：explain 字段包含价格匹配信息"""
        container = AppContainer(Settings())
        agent = ProductRecAgent(container=container)

        profile = UserProfile(
            user_id="u1",
            preferred_categories=["手机"],
            price_range=(5000, 10000),  # 只接受高价商品
        )
        result = asyncio.run(agent.run(user_profile=profile, num_items=5))

        for product in result.products:
            assert "price_matched" in product.explain


if __name__ == "__main__":
    test = TestProductRecAgent()
    test.test_agent_init_with_container()
    test.test_agent_init_without_container()
    test.test_recall_with_profile()
    test.test_recall_without_profile()
    test.test_explain_field_present()
    test.test_explain_recall_source()
    test.test_explain_matched_category()
    test.test_explain_price_matched()
    print("All ProductRecAgent tests passed!")
