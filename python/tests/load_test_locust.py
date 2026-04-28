"""
Locust 压测脚本

功能:
* 模拟混合流量：
  * 推荐请求（≈90%）
  * 指标查询（≈10%）
  * Prometheus 抓取（固定频率）
* 输出性能指标：
  * 请求数 / 错误率
  * 平均延迟、P50 / P95 / P99
* 生成 JSON 报告（baseline.json）

使用:
locust -f load_test_locust.py --host=http://localhost:8866 --users=100 --spawn-rate=2 --run-time=60s

监控:
http://localhost:8089
"""


from __future__ import annotations

import json
import random
import time
from typing import Any

from locust import HttpUser, task, between, events, constant_pacing


class RecommendationUser(HttpUser):
    """模拟用户行为: 发起推荐请求."""
    
    wait_time = between(1, 3)  # 用户间隔 1-3s 发起请求
    
    def on_start(self):
        """初始化用户会话."""
        self.user_id = f"user_{random.randint(1000, 9999)}"
        self.scene = random.choice(["home", "search", "category"])
    
    @task(10)
    def recommend_api(self):
        """主要任务: 发起推荐请求 (占 90% 的请求)."""
        payload = {
            "user_id": self.user_id,
            "scene": self.scene,
            "num_items": 10,
            "context": {
                "device": random.choice(["mobile", "pc", "tablet"]),
                "referrer": random.choice(["search", "homepage", "cart"]),
            },
        }
        with self.client.post(
            "/api/v1/recommend",
            json=payload,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if "products" in data:
                        resp.success()
                    else:
                        resp.failure(f"Missing 'products' field: {data}")
                except json.JSONDecodeError:
                    resp.failure("Invalid JSON response")
            else:
                resp.failure(f"Status code: {resp.status_code}")
    
    @task(1)
    def metrics_api(self):
        """次要任务: 查询指标端点 (占 10% 的请求, 模拟监控查询)."""
        with self.client.get("/api/v1/metrics", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status code: {resp.status_code}")


class PrometheusMetricsUser(HttpUser):
    """模拟 Prometheus scraper: 频繁查询 /metrics 端点."""
    
    wait_time = constant_pacing(2)  # 每 2s 查询一次
    
    @task
    def scrape_prometheus_metrics(self):
        """持续抓取 Prometheus 指标."""
        with self.client.get("/metrics", catch_response=True) as resp:
            if resp.status_code == 200:
                # 验证 Prometheus 格式
                content = resp.text
                if "# HELP" in content and "# TYPE" in content:
                    resp.success()
                else:
                    resp.failure("Invalid Prometheus format")
            else:
                resp.failure(f"Status code: {resp.status_code}")


# ============================================================================
# Locust 事件处理 & 报告生成
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """压测开始时的初始化."""
    print("\n" + "=" * 80)
    print("🚀 性能基线压测启动")
    print(f"   Host: {environment.host}")
    print(f"   开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """压测结束时生成报告."""
    print("\n" + "=" * 80)
    print("✅ 压测完成，生成性能报告")
    print("=" * 80 + "\n")
    
    # 收集统计数据
    stats = environment.stats
    
    # 计算关键指标
    request_stats = []
    for (method, name), req_stats in stats.entries.items():
        if not req_stats.name.startswith("/"):
            continue
        
        # 计算分位数
        response_times_sorted = sorted(req_stats.response_times.values())
        if response_times_sorted:
            count = len(response_times_sorted)
            p50 = response_times_sorted[int(count * 0.50)] if count > 0 else 0
            p95 = response_times_sorted[int(count * 0.95)] if count > 0 else 0
            p99 = response_times_sorted[int(count * 0.99)] if count > 0 else 0
        else:
            p50 = p95 = p99 = 0
        
        request_stats.append({
            "endpoint": req_stats.name,
            "method": req_stats.method,
            "requests": req_stats.num_requests,
            "failures": req_stats.num_failures,
            "error_rate": (req_stats.num_failures / req_stats.num_requests * 100) if req_stats.num_requests > 0 else 0,
            "avg_latency_ms": req_stats.avg_response_time,
            "min_latency_ms": req_stats.min_response_time,
            "max_latency_ms": req_stats.max_response_time,
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
        })
    
    # 打印表格
    print("📊 请求统计\n")
    print(f"{'端点':<30} {'请求数':<10} {'失败数':<10} {'错误率%':<10} {'平均延迟ms':<15}")
    print("-" * 75)
    for stat in request_stats:
        print(
            f"{stat['endpoint']:<30} {stat['requests']:<10} {stat['failures']:<10} "
            f"{stat['error_rate']:<10.2f} {stat['avg_latency_ms']:<15.1f}"
        )
    
    print("\n📈 延迟分位数 (毫秒)\n")
    print(f"{'端点':<30} {'P50':<12} {'P95':<12} {'P99':<12}")
    print("-" * 70)
    for stat in request_stats:
        print(
            f"{stat['endpoint']:<30} {stat['p50_latency_ms']:<12.1f} "
            f"{stat['p95_latency_ms']:<12.1f} {stat['p99_latency_ms']:<12.1f}"
        )
    
    # 全局指标
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    total_error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    total_avg_latency = stats.total.avg_response_time
    
    print(f"\n🎯 全局指标\n")
    print(f"   总请求数: {total_requests}")
    print(f"   总失败数: {total_failures}")
    print(f"   错误率: {total_error_rate:.2f}%")
    print(f"   平均延迟: {total_avg_latency:.1f} ms")
    
    # 保存为 JSON (便于后处理)
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_requests": total_requests,
        "total_failures": total_failures,
        "error_rate_percent": total_error_rate,
        "avg_latency_ms": total_avg_latency,
        "requests": request_stats,
    }
    
    report_file = f"reports/baseline.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n   📁 报告已保存: {report_file}\n")
    print("=" * 80 + "\n")
