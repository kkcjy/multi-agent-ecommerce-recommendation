"""
Multi-Agent E-Commerce Recommendation System — FastAPI Entry Point

Endpoints:
  POST /api/v1/recommend          - 获取个性化推荐
  POST /api/v1/recommend/graph    - 通过LangGraph pipeline推荐
  GET  /api/v1/experiments        - 查看A/B实验状态
  GET  /api/v1/metrics            - 查看系统监控指标
  GET  /health                    - 健康检查
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from typing import Any
import time
import asyncio

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from models.schemas import RecommendationRequest, RecommendationResponse
from orchestrator.supervisor import SupervisorOrchestrator
from orchestrator.graph import build_recommendation_graph
from services.ab_test import ABTestEngine
from services.metrics import MetricsCollector, request_duration_seconds, requests_total

logger = structlog.get_logger()
settings = get_settings()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


ab_engine = ABTestEngine()
metrics_collector = MetricsCollector()
supervisor = SupervisorOrchestrator(ab_engine=ab_engine)
rec_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rec_graph
    rec_graph = build_recommendation_graph()
    logger.info("app.startup", model=settings.llm_model)
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title="Multi-Agent E-Commerce Recommendation System",
    description="用户画像Agent + 商品推荐Agent + 营销文案Agent + 库存决策Agent，并行+聚合模式",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_timeout_middleware(request: Request, call_next):
    """请求级超时处理 (阶段 4)。
    
    对于耗时的推荐请求，使用 settings 中配置的超时时间。
    """
    # 只对 /api/v1/recommend 和 /api/v1/recommend/graph 应用超时
    if request.url.path in ["/api/v1/recommend", "/api/v1/recommend/graph"]:
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=settings.request_timeout_seconds,
            )
            return response
        except asyncio.TimeoutError:
            logger.error("request.timeout", path=request.url.path)
            return JSONResponse(
                status_code=503,
                content={"error": "Request timeout", "message": f"请求超过 {settings.request_timeout_seconds}s 限制"},
            )
    else:
        return await call_next(request)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    """记录 HTTP 请求延迟，暴露给 Prometheus."""
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    
    # 记录 Prometheus 指标
    endpoint = request.url.path
    method = request.method
    status = response.status_code
    
    request_duration_seconds.labels(endpoint=endpoint, method=method).observe(latency)
    requests_total.labels(endpoint=endpoint, method=method, status=status).inc()
    
    return response


app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")),
    name="assets",
)


@app.get("/")
async def root():
    return RedirectResponse(url="/user", status_code=307)


@app.get("/user")
async def user_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "user.html"))


@app.get("/admin")
async def admin_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))


@app.get("/health")
async def health():
    return {"status": "healthy", "model": settings.llm_model}


@app.post("/api/v1/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest):
    """使用Supervisor编排器进行推荐 (生产推荐用法)"""
    response = await supervisor.recommend(request)
    _collect_metrics(response)
    return response


@app.post("/api/v1/recommend/graph")
async def recommend_via_graph(request: RecommendationRequest):
    """使用LangGraph状态图进行推荐 (展示LangGraph能力)"""
    if not rec_graph:
        return {"error": "Graph not initialized"}
    state = {
        "user_id": request.user_id,
        "scene": request.scene,
        "num_items": request.num_items,
        "context": request.context,
    }
    result = await rec_graph.ainvoke(state)
    return {
        "request_id": result.get("request_id"),
        "user_id": result.get("user_id"),
        "products": [p.model_dump() for p in result.get("final_products", [])],
        "marketing_copies": result.get("marketing_copies", []),
        "experiment_group": result.get("experiment_group", "control"),
        "total_latency_ms": round(result.get("total_latency_ms", 0), 1),
    }


@app.get("/api/v1/experiments")
async def get_experiments():
    """查看所有A/B实验状态"""
    experiments = {}
    for exp_id, exp in ab_engine.experiments.items():
        experiments[exp_id] = {
            "name": exp.name,
            "enabled": exp.enabled,
            "groups": [
                {
                    "name": g.name,
                    "weight": g.weight,
                    "config": g.config,
                    "successes": g.successes,
                    "failures": g.failures,
                }
                for g in exp.groups
            ],
            "stats": ab_engine.get_stats(exp_id),
        }
    return experiments


@app.get("/api/v1/metrics")
async def get_metrics():
    """查看系统监控指标 (JSON 格式)"""
    return {
        "agents": metrics_collector.get_agent_stats(),
        "business": metrics_collector.get_business_stats(),
    }


@app.get("/metrics")
async def get_prometheus_metrics():
    """暴露 Prometheus 格式的指标 (text/plain)"""
    metrics_data = metrics_collector.get_prometheus_metrics()
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4")


@app.post("/api/v1/experiments/{experiment_id}/outcome")
async def record_outcome(experiment_id: str, group: str, success: bool):
    """记录A/B测试结果,更新Thompson Sampling"""
    ab_engine.record_outcome(experiment_id, group, success)
    return {"status": "recorded"}


def _collect_metrics(response: RecommendationResponse):
    for name, result in response.agent_results.items():
        metrics_collector.record_agent_call(
            agent_name=name,
            success=result.success,
            latency_ms=result.latency_ms,
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8866, reload=True)
