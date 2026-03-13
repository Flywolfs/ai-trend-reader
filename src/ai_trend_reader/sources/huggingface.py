"""HuggingFace Daily Papers data source via API."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import structlog

from ai_trend_reader.config import HuggingFaceConfig
from ai_trend_reader.models import Source, TrendItem
from ai_trend_reader.sources.base import BaseSource

logger = structlog.get_logger()

HF_DAILY_PAPERS_API = "https://huggingface.co/api/daily_papers"


class HuggingFaceSource(BaseSource):
    def __init__(self, config: HuggingFaceConfig):
        self.config = config

    async def fetch(self) -> list[TrendItem]:
        if not self.config.enabled:
            logger.info("huggingface_source_disabled")
            return []

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info("huggingface_fetch_start", date=date_str)

        items: list[TrendItem] = []
        try:
            async with httpx.AsyncClient(
                timeout=30,
                headers={"User-Agent": "AI-Trend-Reader/1.0"},
            ) as client:
                resp = await client.get(
                    HF_DAILY_PAPERS_API,
                    params={
                        "date": date_str,
                        "limit": self.config.max_results,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            if not isinstance(data, list):
                logger.warning("huggingface_unexpected_response", type=type(data).__name__)
                return []

            for entry in data:
                try:
                    item = self._parse_entry(entry)
                    if item:
                        items.append(item)
                except Exception:
                    logger.debug("huggingface_parse_entry_error", exc_info=True)

            logger.info("huggingface_fetch_complete", total=len(items))

        except Exception:
            logger.exception("huggingface_fetch_error")

        return items

    def _parse_entry(self, entry: dict) -> TrendItem | None:
        """Parse a single HuggingFace daily paper API entry."""
        paper = entry.get("paper", {})
        paper_id = paper.get("id", "")
        if not paper_id:
            return None

        title = paper.get("title", "").strip()
        summary = paper.get("summary", "").strip()
        upvotes = paper.get("upvotes", 0)

        # Authors
        authors = []
        for author in paper.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # Organization
        org = ""
        org_data = entry.get("organization") or paper.get("organization")
        if org_data:
            org = org_data.get("fullname", "") or org_data.get("name", "")

        # GitHub repo link if available
        github_repo = paper.get("githubRepo", "")
        github_stars = paper.get("githubStars", 0)

        # AI-generated summary and keywords
        ai_summary = paper.get("ai_summary", "")
        ai_keywords = paper.get("ai_keywords", [])

        return TrendItem(
            source=Source.HUGGINGFACE,
            source_id=f"hf:{paper_id}",
            title=title,
            url=f"https://huggingface.co/papers/{paper_id}",
            description=summary,
            metadata={
                "upvotes": upvotes,
                "authors": authors[:10],
                "organization": org,
                "arxiv_id": paper_id,
                "pdf_url": f"https://arxiv.org/pdf/{paper_id}.pdf",
                "github_repo": github_repo,
                "github_stars": github_stars,
                "ai_summary": ai_summary,
                "ai_keywords": ai_keywords,
                "num_comments": entry.get("numComments", 0),
            },
            discovered_at=datetime.now(timezone.utc),
        )
