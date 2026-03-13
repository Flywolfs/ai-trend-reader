"""GitHub data source via GitHub Trending page scraping."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx
import structlog

from ai_trend_reader.config import GitHubConfig
from ai_trend_reader.models import Source, TrendItem
from ai_trend_reader.sources.base import BaseSource

logger = structlog.get_logger()

GITHUB_TRENDING_URL = "https://github.com/trending"


def _parse_number(text: str) -> int:
    """Parse a number string like '1,234' or '31,680' into an int."""
    return int(text.strip().replace(",", ""))


class GitHubSource(BaseSource):
    def __init__(self, config: GitHubConfig, token: str = ""):
        self.config = config

    async def fetch(self) -> list[TrendItem]:
        if not self.config.enabled:
            logger.info("github_source_disabled")
            return []

        logger.info("github_trending_fetch_start")
        items: list[TrendItem] = []

        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": "AI-Trend-Reader/1.0"},
                follow_redirects=True,
            ) as client:
                resp = await client.get(
                    GITHUB_TRENDING_URL,
                    params={"since": "daily"},
                )
                resp.raise_for_status()
                html = resp.text

            items = self._parse_trending_html(html)
            logger.info("github_trending_fetch_complete", total=len(items))

        except Exception:
            logger.exception("github_trending_fetch_error")

        return items

    def _parse_trending_html(self, html: str) -> list[TrendItem]:
        """Parse GitHub Trending HTML into TrendItems without BeautifulSoup.

        Each trending repo is inside an <article class="Box-row"> element.
        """
        items: list[TrendItem] = []

        # Split by article tags
        articles = re.split(r'<article\s+class="Box-row"', html)
        # First chunk is before the first article, skip it
        for article_html in articles[1:]:
            try:
                item = self._parse_article(article_html)
                if item:
                    items.append(item)
            except Exception:
                logger.debug("github_trending_parse_article_error", exc_info=True)
                continue

        return items

    def _parse_article(self, html: str) -> TrendItem | None:
        """Parse a single <article> block into a TrendItem."""
        # Extract repo path from the h2 link, e.g. href="/owner/repo"
        # First isolate the <h2>...</h2> block, then find the <a href> inside it
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', html, re.DOTALL)
        if not h2_match:
            return None
        h2_inner = h2_match.group(1)
        repo_match = re.search(r'<a\s[^>]*href="(/[^"]+)"', h2_inner, re.DOTALL)
        if not repo_match:
            return None
        repo_path = repo_match.group(1).strip().lstrip("/")
        # repo_path should be "owner/repo"
        parts = repo_path.split("/")
        if len(parts) != 2:
            return None

        url = f"https://github.com/{repo_path}"

        # Extract description: <p class="col-9 ...">...</p>
        desc = ""
        desc_match = re.search(r'<p\s+class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL)
        if desc_match:
            desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

        # Extract language: <span itemprop="programmingLanguage">Python</span>
        lang = ""
        lang_match = re.search(
            r'<span\s+itemprop="programmingLanguage">(.*?)</span>', html
        )
        if lang_match:
            lang = lang_match.group(1).strip()

        # Extract total stars: the first <a href="/owner/repo/stargazers"> ... number ... </a>
        stars = 0
        stars_match = re.search(
            rf'<a[^>]*href="/{re.escape(repo_path)}/stargazers"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        if stars_match:
            num = re.sub(r'<[^>]+>', '', stars_match.group(1)).strip().replace(",", "")
            if num.isdigit():
                stars = int(num)

        # Extract forks: <a href="/owner/repo/forks"> ... number ... </a>
        forks = 0
        forks_match = re.search(
            rf'<a[^>]*href="/{re.escape(repo_path)}/forks"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        if forks_match:
            num = re.sub(r'<[^>]+>', '', forks_match.group(1)).strip().replace(",", "")
            if num.isdigit():
                forks = int(num)

        # Extract stars today: "123 stars today" or "1,234 stars today"
        stars_today = 0
        today_match = re.search(r'([\d,]+)\s+stars?\s+today', html)
        if today_match:
            stars_today = _parse_number(today_match.group(1))

        repo_name = repo_path.split("/")[-1]

        return TrendItem(
            source=Source.GITHUB,
            source_id=repo_path,
            title=repo_name,
            url=url,
            description=desc,
            metadata={
                "stars": stars,
                "language": lang,
                "forks": forks,
                "stars_today": stars_today,
                "owner": repo_path.split("/")[0],
            },
            discovered_at=datetime.now(timezone.utc),
        )
