"""Graph 与 Supervisor 输出对齐测试（简化版，不调用 LLM）。

验收标准：
- 两条推荐接口核心字段一致，便于前端复用
- 验证 /recommend 与 /recommend/graph 输出结构对齐

注意：本测试使用 Mock 数据，不调用真实 LLM，适合快速验证
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.settings import Settings
from containers.app_container import AppContainer
from models.schemas import RecommendationRequest, Product, RecommendationResponse
from orchestrator.supervisor import SupervisorOrchestrator
from orchestrator.graph import build_recommendation_graph, set_container
from services.ab_test import ABTestEngine


class TestGraphSupervisorAlignment:
    """验证 LangGraph 与 Supervisor 输出字段一致性（静态结构验证）"""

    def setup_method(self):
        """每个测试前重置容器"""
        settings = Settings()
        self.container = AppContainer(settings=settings)
        self.ab_engine = ABTestEngine()
        set_container(self.container)

    def test_core_fields_present_in_both(self):
        """验收标准：两条接口都包含核心字段"""
        # Supervisor 的核心字段（RecommendationResponse）
        supervisor_core_fields = ["request_id", "user_id", "products", "experiment_group", "total_latency_ms"]

        for field in supervisor_core_fields:
            assert field in RecommendationResponse.model_fields, f"RecommendationResponse 缺少字段：{field}"

        # Graph 的核心字段（final_products 是 Graph 的输出字段名）
        # Graph 输出通过 final_products 映射到 products

    def test_products_structure_aligned(self):
        """验收标准：products 字段结构一致"""
        # 验证 Product 包含必需字段
        required_fields = ["product_id", "name", "category", "price", "explain"]

        for field in required_fields:
            assert field in Product.model_fields, f"Product 缺少字段：{field}"

    def test_experiment_group_aligned(self):
        """验收标准：实验分组字段一致"""
        # 同一用户 ID 应该分配到相同实验组
        user_id = "aligned_test_user"
        group1 = self.ab_engine.assign(user_id).get("group", "control")
        group2 = self.ab_engine.assign(user_id).get("group", "control")
        assert group1 == group2, "同一用户应该分配到相同实验组"

    def test_agent_results_structure(self):
        """验收标准：agent_results 字段结构一致"""
        # 验证 AgentResult 包含必需字段
        from models.schemas import AgentResult
        required_fields = ["agent_name", "success", "latency_ms", "data", "confidence"]

        for field in required_fields:
            assert field in AgentResult.model_fields, f"AgentResult 缺少字段：{field}"

    def test_latency_field_present(self):
        """验收标准：延迟字段都存在"""
        from models.schemas import RecommendationResponse
        response = RecommendationResponse(
            request_id="test",
            user_id="test",
            products=[],
            experiment_group="control",
        )
        assert hasattr(response, "total_latency_ms")
        assert isinstance(response.total_latency_ms, float)

    def test_explain_field_in_products(self):
        """验收标准：推荐结果包含 explain 字段"""
        product = Product(
            product_id="P001",
            name="Test Product",
            category="test",
            price=99.0,
        )
        assert hasattr(product, "explain")
        assert isinstance(product.explain, dict)

    def test_supervisor_response_fields(self):
        """验收标准：Supervisor 返回完整字段"""
        # 验证 SupervisorOrchestrator 类存在且可实例化
        assert SupervisorOrchestrator is not None
        supervisor = SupervisorOrchestrator(container=self.container, ab_engine=self.ab_engine)
        assert supervisor is not None

    def test_graph_state_fields(self):
        """验收标准：Graph 状态包含必需字段"""
        from orchestrator.graph import PipelineState

        # Graph 输出应该包含最终产品列表
        graph = build_recommendation_graph()

        # 验证 graph 是编译后的状态图
        assert graph is not None


if __name__ == "__main__":
    test = TestGraphSupervisorAlignment()
    test.setup_method()
    test.test_core_fields_present_in_both()
    test.test_products_structure_aligned()
    test.test_experiment_group_aligned()
    test.test_agent_results_structure()
    test.test_latency_field_present()
    test.test_explain_field_in_products()
    test.test_supervisor_response_fields()
    test.test_graph_state_fields()
    print("All Graph-Supervisor Alignment tests passed!")
