"""Rule-based filter for GitHub repos, Arxiv papers, and HuggingFace papers."""

from __future__ import annotations

import structlog

from ai_trend_reader.config import ArxivConfig, GitHubConfig, HuggingFaceConfig, RuleFilterConfig
from ai_trend_reader.filters.base import BaseFilter
from ai_trend_reader.models import Source, TrendItem

logger = structlog.get_logger()


class RuleFilter(BaseFilter):
    def __init__(
        self,
        config: RuleFilterConfig,
        github_config: GitHubConfig,
        arxiv_config: ArxivConfig,
        huggingface_config: HuggingFaceConfig | None = None,
    ):
        self.config = config
        self.github_keywords = [kw.lower() for kw in github_config.keywords]
        self.arxiv_keywords = [kw.lower() for kw in arxiv_config.keywords]

    async def filter(self, items: list[TrendItem]) -> list[TrendItem]:
        passed = []
        for item in items:
            if item.source == Source.GITHUB and self._check_github(item):
                passed.append(item)
            elif item.source == Source.ARXIV and self._check_arxiv(item):
                passed.append(item)
            elif item.source == Source.HUGGINGFACE and self._check_huggingface(item):
                passed.append(item)

        logger.info(
            "rule_filter_complete",
            input=len(items),
            output=len(passed),
        )
        return passed

    def _check_github(self, item: TrendItem) -> bool:
        """GitHub Trending items already have high signal.
        Only apply basic filters; let LLM decide AI relevance."""
        meta = item.metadata
        rules = self.config.github

        # Exclude forks
        if rules.exclude_forks and meta.get("is_fork", False):
            return False

        # Minimum stars
        if meta.get("stars", 0) < rules.min_stars:
            return False

        # Language whitelist
        if rules.language_whitelist:
            lang = meta.get("language")
            if lang and lang not in rules.language_whitelist:
                return False

        # GitHub Trending items are already curated, pass all through
        # LLM will handle AI relevance scoring
        return True

    def _check_arxiv(self, item: TrendItem) -> bool:
        rules = self.config.arxiv

        if not rules.require_keyword_match:
            return True

        searchable = f"{item.title} {item.description}".lower()
        return any(kw.lower() in searchable for kw in self.arxiv_keywords)

    def _check_huggingface(self, item: TrendItem) -> bool:
        rules = self.config.huggingface

        # Minimum upvotes
        if item.metadata.get("upvotes", 0) < rules.min_upvotes:
            return False

        # Optional keyword match
        if rules.require_keyword_match:
            searchable = f"{item.title} {item.description}".lower()
            keywords = self.arxiv_keywords  # Reuse arxiv keywords for HF papers
            if not any(kw in searchable for kw in keywords):
                return False

        return True
