from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Multi-Agent E-Commerce System"
    debug: bool = False

    # LLM
    llm_api_key: str = "sk-RfjkDtWBtFMIJYAjoTLS6DqZfPUPmlbGPcKfqi3VYnMtkU0w"
    llm_base_url: str = "https://api.meai.cloud/v1"
    llm_model: str = "glm-5.1"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    llm_enable_thinking: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    feature_ttl_seconds: int = 86400
    cache_local_maxsize: int = 1000
    cache_user_profile_local_ttl_seconds: int = 60
    cache_user_profile_ttl_seconds: int = 3600

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "product_embeddings"

    # Database
    database_url: str = "sqlite:///./ecommerce.db"

    # A/B Testing
    ab_test_enabled: bool = True
    ab_test_default_bucket_count: int = 100

    # Agent retry & circuit breaker
    agent_max_retries: int = 2
    agent_retry_backoff_factor: float = 0.5
    agent_retry_backoff_max: float = 4.0
    circuit_breaker_enabled: bool = False
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_window_seconds: int = 30

    # Agent timeouts (seconds)
    agent_timeout_user_profile: float = 5.0
    agent_timeout_product_rec: float = 8.0
    agent_timeout_marketing_copy: float = 10.0
    agent_timeout_inventory: float = 5.0

    # Request timeout (seconds)
    request_timeout_seconds: int = 10

    # Security - admin key
    admin_api_key: str = "admin123456"

    # Security - CORS
    cors_allow_origins: str = "http://localhost:8866,http://127.0.0.1:8866"
    cors_allow_methods: str = "GET,POST,OPTIONS"
    cors_allow_headers: str = "Content-Type,Authorization,X-API-Key"

    # Security - rate limit
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_recommend_per_window: int = 30
    rate_limit_graph_per_window: int = 20

    model_config = {"env_file": ".env", "env_prefix": "ECOM_", "extra": "ignore"}

    def _split_csv(self, raw: str) -> list[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return self._split_csv(self.cors_allow_origins)

    @property
    def cors_methods_list(self) -> list[str]:
        return self._split_csv(self.cors_allow_methods)

    @property
    def cors_headers_list(self) -> list[str]:
        return self._split_csv(self.cors_allow_headers)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
