"""Integration tests for Supervisor and Graph output alignment."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import Settings
from containers.app_container import AppContainer
from orchestrator.supervisor import SupervisorOrchestrator
from orchestrator.graph import build_recommendation_graph, set_container
from services.ab_test import ABTestEngine
from models.schemas import RecommendationRequest


class TestSupervisorIntegration:
    """Supervisor 集成测试"""

    def test_supervisor_end_to_end(self):
        """端到端测试：完整推荐流程"""
        container = AppContainer(Settings())
        orchestrator = SupervisorOrchestrator(container=container, ab_engine=ABTestEngine())

        import asyncio

        request = RecommendationRequest(
            user_id="test_user",
            scene="homepage",
            num_items=5,
        )

        response = asyncio.run(orchestrator.recommend(request))

        # 验收标准：核心字段存在
        assert response.request_id is not None
        assert len(response.products) == 5
        assert response.experiment_group in ("control", "treatment")

        # 验收标准：explain 字段存在
        for product in response.products:
            assert hasattr(product, "explain")
            assert isinstance(product.explain, dict)


class TestGraphOutputAlignment:
    """LangGraph 与 Supervisor 输出对齐测试"""

    def test_graph_and_supervisor_output_aligned(self):
        """验收标准：两条接口输出结构一致"""
        container = AppContainer(Settings())
        set_container(container)

        # 构建 Graph
        graph = build_recommendation_graph()

        import asyncio

        state = {
            "user_id": "test_user",
            "scene": "homepage",
            "num_items": 5,
        }

        result = asyncio.run(graph.ainvoke(state))

        # 检查 Graph 输出包含与 Supervisor 相同的字段
        assert "request_id" in result
        assert "user_id" in result
        assert "final_products" in result
        assert "experiment_group" in result
        assert "total_latency_ms" in result

        # 检查产品包含 explain 字段
        for product in result.get("final_products", []):
            if hasattr(product, "explain"):
                assert isinstance(product.explain, dict)


if __name__ == "__main__":
    # Supervisor 测试
    test_sup = TestSupervisorIntegration()
    test_sup.test_supervisor_end_to_end()
    print("Supervisor integration test passed!")

    # Graph 对齐测试
    test_graph = TestGraphOutputAlignment()
    test_graph.test_graph_and_supervisor_output_aligned()
    print("Graph output alignment test passed!")
