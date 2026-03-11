"""Configuration management using Pydantic Settings + YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubConfig(BaseModel):
    enabled: bool = True
    keywords: list[str] = [
        "llm", "large-language-model", "gpt", "transformer",
        "stable-diffusion", "image-generation", "text-to-image", "comfyui",
        "ai-agent", "langchain", "autogen", "mcp-server", "function-calling",
        "mlops", "model-serving", "vllm", "inference-engine",
    ]
    topics: list[str] = [
        "llm", "ai-agent", "stable-diffusion", "machine-learning",
        "deep-learning", "generative-ai", "text-to-image", "langchain",
    ]
    search_days_back: int = 7
    max_results_per_query: int = 100


class ArxivConfig(BaseModel):
    enabled: bool = True
    categories: list[str] = ["cs.AI", "cs.CL", "cs.CV", "cs.LG"]
    keywords: list[str] = [
        "large language model", "LLM", "GPT", "diffusion model",
        "text-to-image", "image generation", "agent",
        "reinforcement learning from human feedback", "RLHF",
        "transformer", "retrieval augmented generation", "RAG",
        "fine-tuning", "inference", "quantization",
    ]
    search_hours_back: int = 48
    max_results_per_category: int = 200


class GitHubRuleConfig(BaseModel):
    min_stars: int = 50
    exclude_forks: bool = True
    language_whitelist: list[str] | None = None


class ArxivRuleConfig(BaseModel):
    require_keyword_match: bool = True


class RuleFilterConfig(BaseModel):
    github: GitHubRuleConfig = Field(default_factory=GitHubRuleConfig)
    arxiv: ArxivRuleConfig = Field(default_factory=ArxivRuleConfig)


class LLMConfig(BaseModel):
    model: str = "kimi-k2-turbo-preview"
    base_url: str = "https://api.moonshot.cn/v1"
    batch_size: int = 6
    max_concurrent: int = 3
    timeout: int = 60
    temperature: float = 0.3
    score_threshold: float = 6.0


class ServerChanConfig(BaseModel):
    enabled: bool = True


class NotifyConfig(BaseModel):
    serverchan: ServerChanConfig = Field(default_factory=ServerChanConfig)
    max_github_items: int = 10
    max_arxiv_items: int = 10


class StorageConfig(BaseModel):
    db_path: str = "data/trend_reader.db"
    retention_days: int = 90


class LoggingConfig(BaseModel):
    level: str = "INFO"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Secrets from environment variables
    github_token: str = "xx"
    llm_api_key: str = "sk-xx"
    serverchan_sendkey: str = "xx"

    # Nested config sections
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    rule_filter: RuleFilterConfig = Field(default_factory=RuleFilterConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings with priority: env vars > config.yaml > defaults."""
    yaml_data: dict[str, Any] = {}

    if config_path is None:
        # Try default locations
        for candidate in [Path("config.yaml"), Path("config.example.yaml")]:
            if candidate.exists():
                config_path = candidate
                break

    if config_path is not None:
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                yaml_data = yaml.safe_load(f) or {}

    return Settings(**yaml_data)
