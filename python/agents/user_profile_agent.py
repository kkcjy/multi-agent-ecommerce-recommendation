"""
用户画像 Agent
- 实时特征提取：浏览/点击/购买/收藏行为 -> Redis Feature Store
- 用户分群：RFM 模型 + 实时标签
- 画像合并：离线标签 (T+1) + 在线标签 (实时)
- 缓存优化：Redis (L2, TTL=1h) + 本地内存 (L1, TTL=1min)
"""

from __future__ import annotations

import json
import redis
import asyncio
import time
import structlog
from concurrent.futures import ThreadPoolExecutor
from cachetools import TTLCache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import get_settings
from models.schemas import (
    AgentResult,
    UserProfile,
    UserProfileResult,
    UserSegment,
)
from services.metrics import cache_hits_total, cache_misses_total

from .base_agent import BaseAgent

logger = structlog.get_logger()

SYSTEM_PROMPT = """你是电商用户画像专家。根据用户行为生成 JSON。
输出格式：{"segments":["active"],"preferred_categories":["手机"],"price_range":[0,5000],"rfm_score":{"recency":0.5,"frequency":0.5,"monetary":0.5}}
只输出 JSON，不要其他内容。"""


class UserProfileAgent(BaseAgent):
    """用户画像 Agent"""

    def __init__(self):
        settings = get_settings()
        super().__init__(
            name="user_profile",
            timeout=settings.agent_timeout_user_profile,
        )
        self.llm_enabled = bool(settings.llm_api_key and settings.llm_api_key.strip())
        self.llm: ChatOpenAI | None = None
        if self.llm_enabled:
            self.llm = ChatOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                temperature=0.1,
                max_tokens=200,
                extra_body={"enable_thinking": settings.llm_enable_thinking},
            )
        self.feature_store: Any = None

        self._local_cache = TTLCache(
            maxsize=settings.cache_local_maxsize,
            ttl=settings.cache_user_profile_local_ttl_seconds,
        )

        self.redis_client: redis.Redis | None = None
        self.redis_ttl = settings.cache_user_profile_ttl_seconds
        self._redis_executor = ThreadPoolExecutor(max_workers=2)

        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            redis_host = settings.redis_url.split("//")[1].split(":")[0] if "//" in settings.redis_url else "localhost"
            redis_port = int(settings.redis_url.split(":")[2].split("/")[0]) if ":" in settings.redis_url else 6379
            result = sock.connect_ex((redis_host, redis_port))
            sock.close()
            if result == 0:
                self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            else:
                self.redis_client = None
        except Exception:
            self.redis_client = None

    async def _execute(self, **kwargs: Any) -> UserProfileResult:
        user_id: str = kwargs["user_id"]
        context: dict = kwargs.get("context", {})
        profile_data = await self._get_cached_profile(user_id, context)
        return UserProfileResult(
            success=True,
            profile=profile_data,
            data={"source": "cache_or_fallback_or_llm"},
            confidence=0.85,
        )

    async def _get_cached_profile(self, user_id: str, context: dict) -> UserProfile:
        logger.info("user_profile.get_profile_start", user_id=user_id)
        # L1 cache
        try:
            cached = self._local_cache[user_id]
            cache_hits_total.labels(cache_name="user_profile_local").inc()
            logger.info("user_profile.cache_hit", user_id=user_id, cache="L1")
            return cached
        except KeyError:
            pass
        cache_misses_total.labels(cache_name="user_profile_local").inc()
        logger.info("user_profile.cache_miss", user_id=user_id, cache="L1")

        # L2 Redis cache
        if self.redis_client:
            loop = asyncio.get_event_loop()
            redis_cached = await loop.run_in_executor(
                self._redis_executor,
                self._get_redis_cache,
                user_id
            )
            if redis_cached is not None:
                cache_hits_total.labels(cache_name="user_profile_redis").inc()
                self._local_cache[user_id] = redis_cached
                logger.info("user_profile.cache_hit", user_id=user_id, cache="L2")
                return redis_cached
            cache_misses_total.labels(cache_name="user_profile_redis").inc()
            logger.info("user_profile.cache_miss", user_id=user_id, cache="L2")

        # Cache miss - generate profile
        logger.info("user_profile.generating", user_id=user_id)
        behavior_data = await self._collect_behavior(user_id, context)

        # Try LLM with strict timeout using ThreadPoolExecutor
        profile_data = None
        if self.llm:
            try:
                logger.info("user_profile.llm_call_start", user_id=user_id)
                llm_start = time.perf_counter()
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=f"用户 ID: {user_id} 行为数据:{json.dumps(behavior_data, ensure_ascii=False, separators=(',', ':'))}"),
                ]
                # 使用同步 executor + 超时控制
                def _llm_call():
                    return self.llm.invoke(messages, max_tokens=80)

                loop = asyncio.get_event_loop()
                future = loop.run_in_executor(self._redis_executor, _llm_call)
                response = await asyncio.wait_for(future, timeout=1.5)

                llm_duration = (time.perf_counter() - llm_start) * 1000
                logger.info("user_profile.llm_call_complete", user_id=user_id, duration_ms=llm_duration)
                profile_data = self._parse_profile(user_id, response.content)
            except asyncio.TimeoutError:
                logger.warning("user_profile.llm_timeout", user_id=user_id)
                profile_data = self._fallback_profile(user_id, behavior_data)
            except Exception as e:
                logger.warning("user_profile.llm_error", user_id=user_id, error=str(e))
                profile_data = self._fallback_profile(user_id, behavior_data)
        else:
            profile_data = self._fallback_profile(user_id, behavior_data)

        # Write to cache
        self._local_cache[user_id] = profile_data
        if self.redis_client:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._redis_executor,
                self._set_redis_cache,
                user_id,
                profile_data
            )
        logger.info("user_profile.get_profile_complete", user_id=user_id)
        return profile_data

    def _get_local_cache(self, user_id: str) -> UserProfile | None:
        try:
            return self._local_cache[user_id]
        except KeyError:
            return None

    def _set_local_cache(self, user_id: str, profile: UserProfile):
        self._local_cache[user_id] = profile

    def _get_redis_cache(self, user_id: str) -> UserProfile | None:
        if not self.redis_client:
            return None
        try:
            key = f"user_profile:{user_id}"
            data = self.redis_client.get(key)
            if data:
                parsed = json.loads(data)
                return UserProfile(**parsed)
        except Exception:
            pass
        return None

    def _set_redis_cache(self, user_id: str, profile: UserProfile):
        if not self.redis_client:
            return
        try:
            key = f"user_profile:{user_id}"
            self.redis_client.setex(
                key,
                self.redis_ttl,
                json.dumps(profile.model_dump(), ensure_ascii=False),
            )
        except Exception:
            pass

    async def _collect_behavior(self, user_id: str, context: dict) -> dict:
        if self.feature_store:
            return await self.feature_store.get_user_features(user_id)
        return {
            "user_id": user_id,
            "recent_views": context.get("recent_views", ["手机", "耳机", "平板"]),
            "recent_purchases": context.get("recent_purchases", ["充电器"]),
            "view_count_7d": context.get("view_count_7d", 25),
            "purchase_count_30d": context.get("purchase_count_30d", 3),
            "avg_order_amount": context.get("avg_order_amount", 299.0),
        }

    def _parse_profile(self, user_id: str, raw: str) -> UserProfile:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            data = {}

        segments = []
        for s in data.get("segments", ["active"]):
            try:
                segments.append(UserSegment(s))
            except ValueError:
                continue

        price_range_raw = data.get("price_range", [0, 10000])
        price_range = (
            float(price_range_raw[0]),
            float(price_range_raw[1]) if len(price_range_raw) > 1 else 10000.0,
        )

        return UserProfile(
            user_id=user_id,
            segments=segments or [UserSegment.ACTIVE],
            preferred_categories=data.get("preferred_categories", []),
            price_range=price_range,
            rfm_score=data.get("rfm_score", {}),
            real_time_tags=data.get("real_time_tags", {}),
        )

    def _fallback_profile(self, user_id: str, behavior_data: dict[str, Any]) -> UserProfile:
        views = [str(v) for v in behavior_data.get("recent_views", [])]
        purchases = int(behavior_data.get("purchase_count_30d", 0) or 0)
        avg_amount = float(behavior_data.get("avg_order_amount", 0.0) or 0.0)

        preferred = []
        for item in views:
            if item.strip() and item.strip() not in preferred:
                preferred.append(item.strip())
            if len(preferred) >= 3:
                break

        segments: list[UserSegment] = [UserSegment.ACTIVE]
        if purchases <= 1:
            segments.append(UserSegment.NEW_USER)
        if avg_amount >= 800:
            segments.append(UserSegment.HIGH_VALUE)
        if avg_amount <= 300:
            segments.append(UserSegment.PRICE_SENSITIVE)

        unique_segments = []
        seen = set()
        for seg in segments:
            if seg not in seen:
                unique_segments.append(seg)
                seen.add(seg)

        return UserProfile(
            user_id=user_id,
            segments=unique_segments,
            preferred_categories=preferred,
            price_range=(0.0, max(2000.0, avg_amount * 8 if avg_amount > 0 else 3000.0)),
            rfm_score={
                "recency": 0.6,
                "frequency": min(1.0, purchases / 10.0),
                "monetary": min(1.0, avg_amount / 2000.0),
            },
            real_time_tags={"source": "fallback"},
        )
