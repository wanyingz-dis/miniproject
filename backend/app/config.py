"""
Lightweight configuration for CSV-based backend
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
from functools import lru_cache
import os
from typing import List, Optional


class Settings(BaseSettings):
    # API Configuration
    api_title: str = "LLM Observability Platform"
    api_version: str = "1.1.0"
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://localhost:3001",
        ]
    )

    # Data Configuration
    data_dir: str = "data"
    experiments_file: str = "experiments.csv"
    trials_file: str = "trials.csv"
    runs_file: str = "runs.csv"

    # Cache Configuration
    cache_ttl: int = 300  # 5 minutes
    enable_cache: bool = True

    # Performance
    pagination_limit: int = 20
    max_results: int = 1000

    deepinfra_api_key: Optional[str] = None  # Loaded from .env file
    deepinfra_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"

    @property
    def enable_chatbot(self) -> bool:
        """Check if chatbot is enabled based on DeepInfra API key presence"""
        return bool(self.deepinfra_api_key)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def experiments_path(self) -> str:
        return os.path.join(self.data_dir, self.experiments_file)

    @property
    def trials_path(self) -> str:
        return os.path.join(self.data_dir, self.trials_file)

    @property
    def runs_path(self) -> str:
        return os.path.join(self.data_dir, self.runs_file)


@lru_cache()
def get_settings() -> Settings:
    """Cache settings instance"""
    return Settings()


settings = get_settings()
