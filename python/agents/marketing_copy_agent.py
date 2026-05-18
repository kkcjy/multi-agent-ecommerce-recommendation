"""
营销文案Agent
- Prompt模板引擎：基于用户画像动态选择模板(新客/老客/高价值)
- 个性化生成：调用MiniMax M2.7生成文案
- 合规校验：敏感词过滤 + 广告法合规检查
"""

from __future__ import annotations

import json
import re
import asyncio
import time
import structlog
from typing import Any
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import get_settings
from models.schemas import (
    MarketingCopyResult,
    Product,
    UserProfile,
    UserSegment,
)

from .base_agent import BaseAgent

PROMPT_TEMPLATES = {
    UserSegment.NEW_USER: """你是电商营销文案专家。为新用户撰写欢迎+推荐文案。
风格要求：热情友好、突出新人专属优惠感、降低决策门槛。
每个商品生成一条文案(30-50字)。""",

    UserSegment.HIGH_VALUE: """你是电商营销文案专家。为高价值VIP用户撰写推荐文案。
风格要求：品质感、尊享感、突出商品高端属性和品牌价值。
每个商品生成一条文案(30-50字)。""",

    UserSegment.PRICE_SENSITIVE: """你是电商营销文案专家。为价格敏感用户撰写推荐文案。
风格要求：突出性价比、促销价格、限时优惠、省钱金额。
每个商品生成一条文案(30-50字)。""",

    UserSegment.ACTIVE: """你是电商营销文案专家。为活跃用户撰写推荐文案。
风格要求：突出商品亮点和使用场景,引发共鸣。
每个商品生成一条文案(30-50字)。""",

    UserSegment.CHURN_RISK: """你是电商营销文案专家。为即将流失的用户撰写召回文案。
风格要求：情感唤回、专属折扣、限时活动、制造紧迫感。
每个商品生成一条文案(30-50字)。""",
}

FORBIDDEN_WORDS = [
    "最好", "第一", "国家级", "全球首", "绝对", "100%",
    "永久", "万能", "祖传", "纯天然",
]

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"assistant\s*:", re.IGNORECASE),
    re.compile(r"developer\s*:", re.IGNORECASE),
    re.compile(r"```"),
    re.compile(r"<\|.*?\|>"),
]

# 预编译正则表达式
_FORBIDDEN_WORDS_PATTERNS = {
    word: re.compile(re.escape(word)) for word in FORBIDDEN_WORDS
}

COPY_OUTPUT_INSTRUCTION = """
请以JSON数组格式输出,每个元素格式:
[{"product_id": "xxx", "copy": "文案内容"}]
只输出JSON,不要其他内容。"""


class MarketingCopyAgent(BaseAgent):
    def __init__(self):
        settings = get_settings()
        super().__init__(
            name="marketing_copy",
            timeout=settings.agent_timeout_marketing_copy,
        )
        self.llm_enabled = bool(settings.llm_api_key and settings.llm_api_key.strip())
        self.max_llm_field_chars = 120
        self.llm: ChatOpenAI | None = None
        if self.llm_enabled:
            self.llm = ChatOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                temperature=0.7,
                max_tokens=200,
                extra_body={"enable_thinking": settings.llm_enable_thinking},
            )
        self._llm_executor = ThreadPoolExecutor(max_workers=2)
        self.logger = structlog.get_logger()

    async def _execute(self, **kwargs: Any) -> MarketingCopyResult:
        user_profile: UserProfile | None = kwargs.get("user_profile")
        products: list[Product] = kwargs.get("products", [])

        if not products:
            return MarketingCopyResult(success=True, copies=[], confidence=1.0)

        if not self.llm:
            fallback_copies = [
                {
                    "product_id": product.product_id,
                    "title": product.name,
                    "copy": self._fallback_copy(user_profile, product),
                }
                for product in products
            ]
            return MarketingCopyResult(
                success=True,
                copies=fallback_copies,
                prompt_template_used="fallback_template",
                data={"fallback": "llm_disabled"},
                confidence=0.7,
            )

        template_key = self._select_template(user_profile)
        system_prompt = PROMPT_TEMPLATES[template_key]

        product_info = "\n".join(self._safe_product_prompt_line(p) for p in products)

        messages = [
            SystemMessage(content=system_prompt + COPY_OUTPUT_INSTRUCTION),
            HumanMessage(content=f"商品列表:\n{product_info}"),
        ]

        # 添加超时保护，使用线程池运行 LLM 调用
        response = None
        try:
            loop = asyncio.get_event_loop()
            def _llm_call():
                return self.llm.invoke(messages)
            response = await asyncio.wait_for(
                loop.run_in_executor(self._llm_executor, _llm_call),
                timeout=2.0  # 2 秒超时
            )
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.warning("marketing_copy.llm_error", error=str(e))

        # 如果 LLM 失败或超时，使用 fallback 文案
        if response is None:
            fallback_copies = [
                {
                    "product_id": p.product_id,
                    "title": p.name,
                    "copy": self._fallback_copy(user_profile, p),
                }
                for p in products
            ]
            return MarketingCopyResult(
                success=True,
                copies=fallback_copies,
                prompt_template_used="fallback_template",
                data={"fallback": "llm_timeout"},
                confidence=0.7,
            )

        copies = self._parse_copies(response.content)
        copies = [self._compliance_check(c) for c in copies]

        return MarketingCopyResult(
            success=True,
            copies=copies,
            prompt_template_used=template_key.value,
            data={"raw_response": response.content},
            confidence=0.9,
        )

    def _select_template(self, profile: UserProfile | None) -> UserSegment:
        if not profile or not profile.segments:
            return UserSegment.ACTIVE
        priority = [
            UserSegment.NEW_USER,
            UserSegment.HIGH_VALUE,
            UserSegment.CHURN_RISK,
            UserSegment.PRICE_SENSITIVE,
            UserSegment.ACTIVE,
        ]
        for seg in priority:
            if seg in profile.segments:
                return seg
        return UserSegment.ACTIVE

    def _parse_copies(self, raw: str) -> list[dict[str, str]]:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return []

    def _compliance_check(self, copy_item: dict[str, str]) -> dict[str, str]:
        """过滤违反广告法的禁用词汇。
        
        优化: 使用预编译的正则表达式，避免每次都重新编译。
        """
        text = copy_item.get("copy", "")
        for word, pattern in _FORBIDDEN_WORDS_PATTERNS.items():
            text = pattern.sub("***", text)
        copy_item["copy"] = text
        return copy_item

    def _fallback_copy(self, profile: UserProfile | None, product: Product) -> str:
        segment = UserSegment.ACTIVE
        if profile and profile.segments:
            segment = profile.segments[0]

        if segment == UserSegment.NEW_USER:
            text = f"新用户专享推荐：{product.name}，现在下单更划算，快来看看。"
        elif segment == UserSegment.HIGH_VALUE:
            text = f"为您精选高品质单品 {product.name}，兼顾性能与体验，值得入手。"
        elif segment == UserSegment.PRICE_SENSITIVE:
            text = f"高性价比推荐：{product.name}，当前价格友好，适合立即下单。"
        elif segment == UserSegment.CHURN_RISK:
            text = f"好久不见，为你保留了 {product.name}，现在回归可享专属优惠。"
        else:
            text = f"根据你的近期偏好，推荐 {product.name}，适配当前浏览场景。"

        return self._compliance_check({"copy": text})["copy"]

    def _safe_product_prompt_line(self, product: Product) -> str:
        safe_tags = ",".join(self._sanitize_text(tag) for tag in product.tags[:8])
        return (
            f"- ID:{self._sanitize_text(product.product_id, 32)} "
            f"名称:{self._sanitize_text(product.name)} "
            f"类目:{self._sanitize_text(product.category, 64)} "
            f"价格:¥{product.price} "
            f"标签:{safe_tags}"
        )

    def _sanitize_text(self, text: str, max_chars: int | None = None) -> str:
        clean = str(text).strip()
        for pattern in PROMPT_INJECTION_PATTERNS:
            clean = pattern.sub("[filtered]", clean)
        limit = max_chars or self.max_llm_field_chars
        if len(clean) > limit:
            clean = clean[:limit]
        return clean
