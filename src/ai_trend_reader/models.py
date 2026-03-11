"""Core data models for AI Trend Reader."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Source(str, Enum):
    GITHUB = "github"
    ARXIV = "arxiv"


class AIDomain(str, Enum):
    LLM = "LLM/大语言模型"
    IMAGE_GEN = "AI图像生成"
    AGENT = "AI Agent/工具链"
    ML_INFRA = "ML基础设施"
    OTHER = "其他AI领域"


class TrendItem(BaseModel):
    """A unified data item from any source."""

    source: Source
    source_id: str = Field(description="Unique ID: 'owner/repo' for GitHub, paper ID for Arxiv")
    title: str
    url: str
    description: str = ""
    metadata: dict = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class ScoredItem(BaseModel):
    """A trend item after LLM scoring."""

    item: TrendItem
    relevance_score: float = Field(ge=0, le=10, description="Relevance score 0-10")
    domain: AIDomain = AIDomain.OTHER
    summary_zh: str = Field(default="", description="One-line Chinese summary")
    reason: str = Field(default="", description="Recommendation reason")


class DigestReport(BaseModel):
    """Daily digest report."""

    date: str
    github_items: list[ScoredItem] = Field(default_factory=list)
    arxiv_items: list[ScoredItem] = Field(default_factory=list)
    stats: DigestStats = Field(default_factory=lambda: DigestStats())


class DigestStats(BaseModel):
    """Statistics for the daily digest."""

    github_fetched: int = 0
    github_after_rules: int = 0
    github_recommended: int = 0
    arxiv_fetched: int = 0
    arxiv_after_rules: int = 0
    arxiv_recommended: int = 0
