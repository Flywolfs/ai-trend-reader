"""Rule-based filter for GitHub repos, Arxiv papers, and HuggingFace papers.

For Arxiv papers, affiliation-based filtering is applied:
- Papers from authors NOT affiliated with top-500 universities or known AI companies
  are discarded (returned in the `filtered_out` list for DB recording).
- Papers that pass affiliation check get a `affiliation_tier` in metadata.
"""

from __future__ import annotations

import structlog

from ai_trend_reader.affiliations import (
    extract_affiliation_text,
    match_affiliation_tier,
)
from ai_trend_reader.config import ArxivConfig, GitHubConfig, HuggingFaceConfig, RuleFilterConfig
from ai_trend_reader.filters.base import BaseFilter
from ai_trend_reader.models import Source, TrendItem

logger = structlog.get_logger()


class RuleFilterResult:
    """Result of rule filtering, separating passed and filtered-out items."""

    def __init__(self, passed: list[TrendItem], filtered_out: list[TrendItem]):
        self.passed = passed
        self.filtered_out = filtered_out


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
        """Filter items, return only those that pass."""
        result = await self.filter_with_rejects(items)
        return result.passed

    async def filter_with_rejects(self, items: list[TrendItem]) -> RuleFilterResult:
        """Filter items and also return the rejected ones (for DB recording)."""
        passed = []
        filtered_out = []

        for item in items:
            if item.source == Source.GITHUB:
                if self._check_github(item):
                    passed.append(item)
                else:
                    filtered_out.append(item)
            elif item.source == Source.ARXIV:
                if self._check_arxiv(item):
                    passed.append(item)
                else:
                    filtered_out.append(item)
            elif item.source == Source.HUGGINGFACE:
                if self._check_huggingface(item):
                    passed.append(item)
                else:
                    filtered_out.append(item)

        logger.info(
            "rule_filter_complete",
            input=len(items),
            output=len(passed),
            filtered_out=len(filtered_out),
        )
        return RuleFilterResult(passed=passed, filtered_out=filtered_out)

    def _check_github(self, item: TrendItem) -> bool:
        """GitHub Trending items already have high signal.
        Only apply basic filters; let LLM decide AI relevance."""
        meta = item.metadata
        rules = self.config.github

        if rules.exclude_forks and meta.get("is_fork", False):
            return False

        if meta.get("stars", 0) < rules.min_stars:
            return False

        if rules.language_whitelist:
            lang = meta.get("language")
            if lang and lang not in rules.language_whitelist:
                return False

        return True

    def _check_arxiv(self, item: TrendItem) -> bool:
        """Check arxiv paper: keyword match + affiliation check.

        Papers from authors not in top-500 universities or known AI companies
        are directly discarded.
        """
        rules = self.config.arxiv

        # Step 1: keyword match (if enabled)
        if rules.require_keyword_match:
            searchable = f"{item.title} {item.description}".lower()
            if not any(kw.lower() in searchable for kw in self.arxiv_keywords):
                return False

        # Step 2: affiliation check
        # Build text to search for affiliations from authors + abstract
        affiliation_text = extract_affiliation_text(item.metadata)
        # Also scan the abstract/description for institutional mentions
        full_text = f"{affiliation_text} {item.description}"
        tier = match_affiliation_tier(full_text)

        if tier is None:
            # No recognized affiliation found -> discard
            logger.debug(
                "arxiv_affiliation_rejected",
                paper=item.source_id,
                title=item.title[:60],
            )
            return False

        # Store tier in metadata for downstream use (LLM scoring bonus)
        item.metadata["affiliation_tier"] = tier
        return True

    def _check_huggingface(self, item: TrendItem) -> bool:
        rules = self.config.huggingface

        if item.metadata.get("upvotes", 0) < rules.min_upvotes:
            return False

        if rules.require_keyword_match:
            searchable = f"{item.title} {item.description}".lower()
            keywords = self.arxiv_keywords
            if not any(kw in searchable for kw in keywords):
                return False

        # Also compute affiliation tier for HuggingFace papers (for LLM bonus)
        affiliation_text = extract_affiliation_text(item.metadata)
        full_text = f"{affiliation_text} {item.description}"
        tier = match_affiliation_tier(full_text)
        if tier is not None:
            item.metadata["affiliation_tier"] = tier

        return True
