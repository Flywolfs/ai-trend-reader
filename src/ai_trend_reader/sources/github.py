"""GitHub data source using Search API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import structlog

from ai_trend_reader.config import GitHubConfig
from ai_trend_reader.models import Source, TrendItem
from ai_trend_reader.sources.base import BaseSource

logger = structlog.get_logger()

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


class GitHubSource(BaseSource):
    def __init__(self, config: GitHubConfig, token: str):
        self.config = config
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def fetch(self) -> list[TrendItem]:
        if not self.config.enabled:
            logger.info("github_source_disabled")
            return []

        queries = self._build_queries()
        all_items: dict[str, TrendItem] = {}

        async with httpx.AsyncClient(headers=self.headers, timeout=30) as client:
            for query in queries:
                try:
                    items = await self._search(client, query)
                    for item in items:
                        if item.source_id not in all_items:
                            all_items[item.source_id] = item
                    # Respect GitHub rate limit: max 10 requests per minute for search
                    await asyncio.sleep(6)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 403:
                        reset = e.response.headers.get("X-RateLimit-Reset")
                        logger.warning("github_rate_limited", reset_at=reset)
                        if reset:
                            wait = int(reset) - int(datetime.now(timezone.utc).timestamp()) + 1
                            if 0 < wait < 120:
                                logger.info("github_waiting_for_reset", seconds=wait)
                                await asyncio.sleep(wait)
                                continue
                        break
                    logger.error("github_search_error", status=e.response.status_code, query=query)
                except Exception:
                    logger.exception("github_search_unexpected_error", query=query)

        logger.info("github_fetch_complete", total=len(all_items))
        return list(all_items.values())

    def _build_queries(self) -> list[str]:
        """Build multiple search queries for comprehensive coverage."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.search_days_back)
        date_str = cutoff.strftime("%Y-%m-%d")
        queries = []

        # Topic-based searches
        for topic in self.config.topics:
            queries.append(f"topic:{topic} created:>{date_str} sort:stars")

        # Keyword-based searches (group keywords to reduce query count)
        keyword_groups = [
            self.config.keywords[i : i + 3]
            for i in range(0, len(self.config.keywords), 3)
        ]
        for group in keyword_groups:
            q = " OR ".join(group)
            queries.append(f"{q} created:>{date_str} sort:stars")

        return queries

    async def _search(self, client: httpx.AsyncClient, query: str) -> list[TrendItem]:
        """Execute a single search query."""
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(self.config.max_results_per_query, 100),
        }

        logger.debug("github_search", query=query)
        resp = await client.get(GITHUB_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        items = []
        for repo in data.get("items", []):
            item = TrendItem(
                source=Source.GITHUB,
                source_id=repo["full_name"],
                title=repo["name"],
                url=repo["html_url"],
                description=repo.get("description") or "",
                metadata={
                    "stars": repo["stargazers_count"],
                    "language": repo.get("language"),
                    "topics": repo.get("topics", []),
                    "forks": repo["forks_count"],
                    "created_at": repo["created_at"],
                    "pushed_at": repo["pushed_at"],
                    "owner": repo["owner"]["login"],
                    "is_fork": repo.get("fork", False),
                },
            )
            items.append(item)

        logger.debug("github_search_results", query=query, count=len(items))
        return items
