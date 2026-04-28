from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Multi-Agent E-Commerce System"
    debug: bool = False

    # LLM
    llm_api_key: str = ""
    llm_base_url: str = "https://api.minimax.chat/v1"
    llm_model: str = "MiniMax-M1"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    feature_ttl_seconds: int = 86400

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "product_embeddings"

    # Database
    database_url: str = "sqlite:///./ecommerce.db"

    # A/B Testing
    ab_test_enabled: bool = True
    ab_test_default_bucket_count: int = 100

    # Agent timeouts (seconds)
    agent_timeout_user_profile: float = 5.0
    agent_timeout_product_rec: float = 8.0
    agent_timeout_marketing_copy: float = 10.0
    agent_timeout_inventory: float = 5.0

    # Request-level timeout & retry
    request_timeout_seconds: float = 8.0
    agent_max_retries: int = 2
    agent_retry_backoff_factor: float = 0.5
    agent_retry_backoff_max: float = 4.0

    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5  # 失败次数阈值
    circuit_breaker_window_seconds: int = 300  # 时间窗口

    # Cache configuration
    cache_user_profile_ttl_seconds: int = 3600  # Redis TTL: 1h
    cache_user_profile_local_ttl_seconds: int = 60  # 本地 L1 缓存: 1min
    cache_product_recall_ttl_seconds: int = 300  # 产品推荐缓存: 5min
    cache_local_maxsize: int = 128  # lru_cache 大小

    # Metrics configuration
    metrics_business_event_max_size: int = 1000  # 循环缓冲区大小
    metrics_business_event_sampling_rate: int = 100  # 采样率: 每 100 个请求采 1 条

    model_config = {"env_file": ".env", "env_prefix": "ECOM_"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
