"""Arxiv data source using the arxiv Python package."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
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

    async def fetch(self, target_date: date | None = None) -> list[TrendItem]:
        if not self.config.enabled:
            logger.info("arxiv_source_disabled")
            return []

        # 使用目标日期或当天日期
        fetch_date = target_date or date.today()
        logger.info("arxiv_fetch_start", date=fetch_date.isoformat())

        all_items: dict[str, TrendItem] = {}
        loop = asyncio.get_event_loop()

        for category in self.config.categories:
            try:
                items = await loop.run_in_executor(
                    None, partial(self._search_category, category, fetch_date)
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

    def _search_category(self, category: str, target_date: date | None = None) -> list[TrendItem]:
        """Search papers in a single arxiv category (runs in thread)."""
        # 如果有目标日期，使用该日期的开始和结束时间
        if target_date:
            start_time = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
            end_time = datetime.combine(target_date, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.config.search_hours_back)
            start_time = cutoff
            end_time = datetime.now(timezone.utc)

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
            # 如果指定了目标日期，只获取该日期的论文
            if target_date:
                # 检查论文是否发布在目标日期
                if published.date() != target_date:
                    continue
            elif published < start_time:
                break

            paper_id = result.entry_id.split("/abs/")[-1]

            # Collect all author names (not just first 5) for affiliation matching
            all_authors = [a.name for a in result.authors]

            item = TrendItem(
                source=Source.ARXIV,
                source_id=paper_id,
                title=result.title.replace("\n", " ").strip(),
                url=result.entry_id,
                description=result.summary.replace("\n", " ").strip(),
                metadata={
                    "authors": all_authors[:10],
                    "all_authors_text": ", ".join(all_authors),
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "pdf_url": result.pdf_url,
                    "published": published.isoformat(),
                },
                discovered_at=datetime.combine(target_date or date.today(), datetime.min.time(), tzinfo=timezone.utc),
            )
            items.append(item)

        logger.debug("arxiv_search_results", category=category, count=len(items), target_date=str(target_date) if target_date else None)
        return items
