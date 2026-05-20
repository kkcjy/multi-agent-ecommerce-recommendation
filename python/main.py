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
from urllib.parse import quote
import time
import asyncio

import structlog
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from containers.app_container import AppContainer
from models.schemas import RecommendationRequest, RecommendationResponse
from orchestrator.supervisor import SupervisorOrchestrator
from orchestrator.graph import build_recommendation_graph, set_container
from services.ab_test import ABTestEngine
from services.metrics import MetricsCollector, request_duration_seconds, requests_total
from services.rate_limiter import InMemoryRateLimiter

logger = structlog.get_logger()
settings = get_settings()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


# 初始化全局依赖注入容器
container = AppContainer(settings=settings)

ab_engine = ABTestEngine()
metrics_collector = MetricsCollector()
supervisor = SupervisorOrchestrator(container=container, ab_engine=ab_engine)
rec_graph = None
recommend_limiter = InMemoryRateLimiter(
    limit=settings.rate_limit_recommend_per_window,
    window_seconds=settings.rate_limit_window_seconds,
)
recommend_graph_limiter = InMemoryRateLimiter(
    limit=settings.rate_limit_graph_per_window,
    window_seconds=settings.rate_limit_window_seconds,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rec_graph
    # 设置 LangGraph 全局容器
    set_container(container)
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
    allow_origins=settings.cors_origins_list,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)


@app.middleware("http")
async def request_timeout_middleware(request: Request, call_next):
    """请求级超时处理。
    """
    # 使用前缀匹配而非精确匹配，支持版本扩展
    if request.url.path.startswith("/api/v1/recommend"):
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=settings.request_timeout_seconds,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(
                "request.timeout",
                path=request.url.path,
                timeout_seconds=settings.request_timeout_seconds,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Request timeout",
                    "message": f"请求超过 {settings.request_timeout_seconds}s 限制，请稍后重试",
                },
            )
        except Exception as exc:
            logger.error("request.middleware_error", path=request.url.path, error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"},
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
    return RedirectResponse(url="/home", status_code=307)


@app.get("/home")
async def home_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "home.html"))


@app.get("/user")
async def user_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "user.html"))


@app.get("/category")
async def category_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "category.html"))


@app.get("/search")
async def search_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "search.html"))


@app.get("/product/{product_id}")
async def product_portal(product_id: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "product.html"))


@app.get("/admin")
async def admin_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))


@app.get("/health")
async def health():
    return {"status": "healthy", "model": settings.llm_model}


@app.post("/api/v1/recommend", response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest, request_ctx: Request):
    """使用Supervisor编排器进行推荐 (生产推荐用法)"""
    _enforce_user_rate_limit(user_id=request.user_id, path="/api/v1/recommend", request_ctx=request_ctx)
    response = await supervisor.recommend(request)
    _collect_metrics(response)
    return response


@app.post("/api/v1/recommend/graph")
async def recommend_via_graph(request: RecommendationRequest, request_ctx: Request):
    """使用LangGraph状态图进行推荐 (展示LangGraph能力)"""
    _enforce_user_rate_limit(user_id=request.user_id, path="/api/v1/recommend/graph", request_ctx=request_ctx)
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
        "request_id": result.get("request_id", ""),
        "user_id": result.get("user_id", ""),
        "products": [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in result.get("final_products", [])],
        "marketing_copies": result.get("marketing_copies", []),
        "experiment_group": result.get("experiment_group", "control"),
        "total_latency_ms": round(result.get("total_latency_ms", 0), 1),
    }


def _verify_admin_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    expected = settings.admin_api_key.strip()
    if not expected:
        logger.warning("security.admin_api_key_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured",
        )
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


def _enforce_user_rate_limit(user_id: str, path: str, request_ctx: Request):
    if not settings.rate_limit_enabled:
        return
    limiter = recommend_limiter if path == "/api/v1/recommend" else recommend_graph_limiter
    client_ip = request_ctx.client.host if request_ctx.client else "unknown"
    limit_key = f"{user_id}:{client_ip}:{path}"
    allowed, retry_after = limiter.is_allowed(limit_key)
    if not allowed:
        logger.warning(
            "security.rate_limit_hit.user",
            path=path,
            user_id=user_id,
            client_ip=client_ip,
            retry_after=retry_after,
        )
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请 {retry_after}s 后重试",
        )


@app.get("/api/v1/product/{product_id}")
async def get_product_detail(product_id: str):
    """获取商品详情页所需数据。"""
    products = await container.product_repo.get_by_ids([product_id])
    if not products:
        raise HTTPException(status_code=404, detail="商品不存在")
    product = products[0]
    data = product.model_dump()
    price = float(data.get("price") or 0)
    discount_rate = 0.08 if price >= 5000 else 0.06 if price >= 2000 else 0.1
    discount = round(price * discount_rate, 2)
    data.update(
        {
            "description": data.get("description")
            or f"{data.get('brand') or 'Nova精选'} {data.get('category') or '商品'}，精选品质好物，支持规格选择、优惠展示、库存提示与相似推荐。",
            "final_price": max(0, round(price - discount, 2)),
            "discount": discount,
            "sales": max(99, int(data.get("stock") or 0) * 3),
            "rating": round(4.6 + (int(data.get("stock") or 0) % 4) * 0.1, 1),
            "external_url": f"https://www.jd.com/Search?keyword={quote(product.name)}",
        }
    )
    return {"code": 0, "message": "ok", "data": data}


@app.get("/api/v1/experiments")
async def get_experiments(_: None = Depends(_verify_admin_api_key)):
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
async def get_metrics(_: None = Depends(_verify_admin_api_key)):
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
async def record_outcome(
    experiment_id: str,
    group: str,
    success: bool,
    _: None = Depends(_verify_admin_api_key),
):
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
