from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class UserSegment(str, Enum):
    NEW_USER = "new_user"
    ACTIVE = "active"
    HIGH_VALUE = "high_value"
    PRICE_SENSITIVE = "price_sensitive"
    CHURN_RISK = "churn_risk"


class InventoryStatus(str, Enum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"


class UserProfile(BaseModel):
    user_id: str
    age: int | None = None
    gender: str | None = None
    city: str | None = None
    segments: list[UserSegment] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    price_range: tuple[float, float] = (0.0, 10000.0)
    recent_views: list[str] = Field(default_factory=list)
    recent_purchases: list[str] = Field(default_factory=list)
    rfm_score: dict[str, float] = Field(default_factory=dict)
    real_time_tags: dict[str, Any] = Field(default_factory=dict)


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    final_price: float | None = None
    discount: float = 0.0
    original_price: float | None = None
    currency: str = "CNY"
    description: str = ""
    brand: str = ""
    seller_id: str = ""
    stock: int = 0
    inventory_status: InventoryStatus = InventoryStatus.IN_STOCK
    sales: int = 0
    rating: float = 0.0
    review_count: int = 0
    tags: list[str] = Field(default_factory=list)
    price_tags: list[str] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    score: float = 0.0
    image_url: str = ""
    image_urls: list[str] = Field(default_factory=list)
    external_url: str = ""
    specs: dict[str, Any] = Field(default_factory=dict)
    explain: dict[str, Any] = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    scene: str = Field(default="homepage", min_length=1, max_length=64)
    num_items: int = Field(default=10, ge=1, le=50)
    context: dict[str, Any] = Field(default_factory=dict)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_id 不能为空")
        return value

    @field_validator("scene")
    @classmethod
    def validate_scene(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("scene 不能为空")
        return value

    @model_validator(mode="after")
    def validate_context_limits(self) -> "RecommendationRequest":
        if len(self.context) > 30:
            raise ValueError("context 键数量超出限制(<=30)")
        context_chars = len(str(self.context))
        if context_chars > 4096:
            raise ValueError("context 内容过长(<=4096字符)")
        return self


class AgentResult(BaseModel):
    agent_name: str
    success: bool = True
    latency_ms: float = 0.0
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class UserProfileResult(AgentResult):
    agent_name: str = "user_profile"
    profile: UserProfile | None = None


class ProductRecResult(AgentResult):
    agent_name: str = "product_rec"
    products: list[Product] = Field(default_factory=list)
    recall_strategy: str = ""
    explain: dict[str, Any] = Field(default_factory=dict)


class MarketingCopyResult(AgentResult):
    agent_name: str = "marketing_copy"
    copies: list[dict[str, str]] = Field(default_factory=list)
    prompt_template_used: str = ""


class InventoryResult(AgentResult):
    agent_name: str = "inventory"
    available_products: list[str] = Field(default_factory=list)
    low_stock_alerts: list[dict[str, Any]] = Field(default_factory=list)
    purchase_limits: dict[str, int] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    request_id: str
    user_id: str
    products: list[Product] = Field(default_factory=list)
    marketing_copies: list[dict[str, str]] = Field(default_factory=list)
    experiment_group: str = "control"
    agent_results: dict[str, AgentResult] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
