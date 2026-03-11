"""Arxiv data source using the arxiv Python package."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial

import arxiv
import structlog

from ai_trend_reader.config import ArxivConfig
from ai_trend_reader.models import Source, TrendItem
from ai_trend_reader.sources.base import BaseSource

logger = structlog.get_logger()


class ArxivSource(BaseSource):
    def __init__(self, config: ArxivConfig):
        self.config = config

    async def fetch(self) -> list[TrendItem]:
        if not self.config.enabled:
            logger.info("arxiv_source_disabled")
            return []

        all_items: dict[str, TrendItem] = {}
        loop = asyncio.get_event_loop()

        for category in self.config.categories:
            try:
                items = await loop.run_in_executor(
                    None, partial(self._search_category, category)
                )
                for item in items:
                    if item.source_id not in all_items:
                        all_items[item.source_id] = item
                # Respect arxiv rate limit: 3 seconds between requests
                await asyncio.sleep(3)
            except Exception:
                logger.exception("arxiv_search_error", category=category)

        logger.info("arxiv_fetch_complete", total=len(all_items))
        return list(all_items.values())

    def _search_category(self, category: str) -> list[TrendItem]:
        """Search papers in a single arxiv category (runs in thread)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.config.search_hours_back)

        # Build query: category + recent date
        query = f"cat:{category}"

        client = arxiv.Client(
            page_size=100,
            delay_seconds=3,
            num_retries=3,
        )

        search = arxiv.Search(
            query=query,
            max_results=self.config.max_results_per_category,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        items = []
        for result in client.results(search):
            # Filter by submission date
            published = result.published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                break

            paper_id = result.entry_id.split("/abs/")[-1]
            item = TrendItem(
                source=Source.ARXIV,
                source_id=paper_id,
                title=result.title.replace("\n", " ").strip(),
                url=result.entry_id,
                description=result.summary.replace("\n", " ").strip(),
                metadata={
                    "authors": [a.name for a in result.authors[:5]],
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "pdf_url": result.pdf_url,
                    "published": published.isoformat(),
                },
                discovered_at=datetime.now(timezone.utc),
            )
            items.append(item)

        logger.debug("arxiv_search_results", category=category, count=len(items))
        return items
