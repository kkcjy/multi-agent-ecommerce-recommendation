from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any, Callable

import httpx


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


class SmokeHarness:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self.results: list[CheckResult] = []

    def run(self) -> int:
        self._check("GET /health", self._health)
        self._check("GET /user", self._user_page)
        self._check("GET /admin", self._admin_page)
        self._check("GET /assets/common.js", lambda: self._expect_status(self.client.get("/assets/common.js"), 200))
        self._check("GET /assets/user.js", lambda: self._expect_status(self.client.get("/assets/user.js"), 200))
        self._check("GET /assets/admin.js", lambda: self._expect_status(self.client.get("/assets/admin.js"), 200))
        self._check("GET /assets/styles.css", lambda: self._expect_status(self.client.get("/assets/styles.css"), 200))
        self._check("POST /api/v1/recommend", self._recommend)
        self._check("POST /api/v1/recommend/graph", self._recommend_graph)
        self._check("GET /api/v1/experiments", self._experiments)
        self._check("GET /api/v1/metrics", self._metrics)
        self._check("POST /api/v1/experiments/{id}/outcome", self._outcome)

        self._print_report()
        failed = [r for r in self.results if not r.ok]
        return 1 if failed else 0

    def _check(self, name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            self.results.append(CheckResult(name=name, ok=True, detail="ok"))
        except Exception as exc:
            self.results.append(CheckResult(name=name, ok=False, detail=str(exc)))

    @staticmethod
    def _expect(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)

    @staticmethod
    def _expect_status(resp: httpx.Response, code: int) -> None:
        if resp.status_code != code:
            snippet = resp.text[:300]
            raise AssertionError(f"expected={code} got={resp.status_code} body={snippet}")

    @staticmethod
    def _expect_keys(data: dict[str, Any], keys: list[str]) -> None:
        for key in keys:
            if key not in data:
                raise AssertionError(f"missing key: {key}")

    def _health(self) -> None:
        resp = self.client.get("/health")
        self._expect_status(resp, 200)
        data = resp.json()
        self._expect_keys(data, ["status", "model"])
        self._expect(data["status"] == "healthy", "health status is not healthy")

    def _user_page(self) -> None:
        resp = self.client.get("/user")
        self._expect_status(resp, 200)
        html = resp.text
        required_ids = [
            "recommend-form",
            "userId",
            "numItems",
            "recentViews",
            "submitBtn",
            "requestState",
            "metaLine",
            "copyList",
            "reasonList",
            "productGrid",
        ]
        for element_id in required_ids:
            self._expect(f'id="{element_id}"' in html, f"missing element id {element_id}")

        self._expect("/assets/common.js" in html, "common.js is not included in user page")
        self._expect("/assets/user.js" in html, "user.js is not included in user page")

    def _admin_page(self) -> None:
        resp = self.client.get("/admin")
        self._expect_status(resp, 200)
        html = resp.text
        required_ids = [
            "reloadExperiments",
            "reloadMetrics",
            "experimentsState",
            "metricsState",
            "experimentsContainer",
            "metricsContainer",
            "outcomeForm",
            "outcomeSubmitBtn",
            "outcomeState",
        ]
        for element_id in required_ids:
            self._expect(f'id="{element_id}"' in html, f"missing element id {element_id}")

        self._expect("/assets/common.js" in html, "common.js is not included in admin page")
        self._expect("/assets/admin.js" in html, "admin.js is not included in admin page")

    def _sample_payload(self) -> dict[str, Any]:
        return {
            "user_id": "smoke_user_001",
            "scene": "homepage",
            "num_items": 5,
            "context": {
                "recent_views": ["phone", "earphones", "charger"],
            },
        }

    def _assert_recommend_response_shape(self, data: dict[str, Any]) -> None:
        self._expect_keys(
            data,
            [
                "request_id",
                "user_id",
                "products",
                "marketing_copies",
                "experiment_group",
                "total_latency_ms",
            ],
        )
        self._expect(isinstance(data["request_id"], str) and len(data["request_id"]) > 8, "request_id invalid")
        self._expect(data["user_id"] == "smoke_user_001", "user_id mismatch")
        self._expect(isinstance(data["products"], list), "products must be list")
        self._expect(isinstance(data["marketing_copies"], list), "marketing_copies must be list")
        self._expect(isinstance(data["experiment_group"], str), "experiment_group must be string")
        self._expect(isinstance(data["total_latency_ms"], (float, int)), "total_latency_ms must be number")

    def _recommend(self) -> None:
        resp = self.client.post("/api/v1/recommend", json=self._sample_payload())
        self._expect_status(resp, 200)
        self._assert_recommend_response_shape(resp.json())

    def _recommend_graph(self) -> None:
        resp = self.client.post("/api/v1/recommend/graph", json=self._sample_payload())
        self._expect_status(resp, 200)
        data = resp.json()
        self._assert_recommend_response_shape(data)

    def _experiments(self) -> None:
        resp = self.client.get("/api/v1/experiments")
        self._expect_status(resp, 200)
        data = resp.json()
        self._expect(isinstance(data, dict), "experiments response must be object")
        self._expect("rec_strategy" in data, "rec_strategy experiment not found")

        rec_strategy = data["rec_strategy"]
        self._expect_keys(rec_strategy, ["name", "enabled", "groups", "stats"])
        self._expect(isinstance(rec_strategy["groups"], list), "groups must be list")
        self._expect(len(rec_strategy["groups"]) > 0, "groups list is empty")

        first_group = rec_strategy["groups"][0]
        self._expect_keys(first_group, ["name", "weight", "config", "successes", "failures"])

    def _metrics(self) -> None:
        resp = self.client.get("/api/v1/metrics")
        self._expect_status(resp, 200)
        data = resp.json()
        self._expect_keys(data, ["agents", "business"])
        self._expect(isinstance(data["agents"], dict), "metrics.agents must be object")
        self._expect(isinstance(data["business"], dict), "metrics.business must be object")

        # ensure critical agent entries become visible after recommendation call
        for required_agent in ["user_profile", "product_rec", "marketing_copy", "inventory"]:
            self._expect(required_agent in data["agents"], f"agent metric missing: {required_agent}")
            metric = data["agents"][required_agent]
            self._expect_keys(metric, ["call_count", "success_rate", "avg_latency_ms", "recent_errors"])

    def _outcome(self) -> None:
        before = self.client.get("/api/v1/experiments")
        self._expect_status(before, 200)
        before_data = before.json()
        before_control_successes = self._find_group_successes(before_data, "rec_strategy", "control")

        resp = self.client.post("/api/v1/experiments/rec_strategy/outcome?group=control&success=true")
        self._expect_status(resp, 200)
        body = resp.json()
        self._expect(body.get("status") == "recorded", "unexpected outcome response")

        after = self.client.get("/api/v1/experiments")
        self._expect_status(after, 200)
        after_data = after.json()
        after_control_successes = self._find_group_successes(after_data, "rec_strategy", "control")
        self._expect(
            after_control_successes == before_control_successes + 1,
            f"control successes not incremented as expected: before={before_control_successes} after={after_control_successes}",
        )

    @staticmethod
    def _find_group_successes(experiments: dict[str, Any], exp_id: str, group_name: str) -> int:
        exp = experiments.get(exp_id, {})
        for group in exp.get("groups", []):
            if group.get("name") == group_name:
                return int(group.get("successes", 0))
        raise AssertionError(f"group not found: {exp_id}/{group_name}")

    def _print_report(self) -> None:
        print("SMOKE_RESULTS_START")
        for result in self.results:
            status = "PASS" if result.ok else "FAIL"
            print(f"[{status}] {result.name} :: {result.detail}")
        failed = len([r for r in self.results if not r.ok])
        print("SMOKE_RESULTS_END")
        print(f"TOTAL={len(self.results)} FAILED={failed}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke harness for API + frontend key paths")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    harness = SmokeHarness(base_url=args.base_url, timeout=args.timeout)
    return harness.run()


if __name__ == "__main__":
    sys.exit(main())
