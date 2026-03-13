"""Server酱 (ServerChan) notification integration."""

from __future__ import annotations

import asyncio

import httpx
import structlog

from ai_trend_reader.models import DigestReport, ScoredItem
from ai_trend_reader.notify.base import BaseNotifier

logger = structlog.get_logger()

SERVERCHAN_API = "https://sctapi.ftqq.com/{key}.send"


class ServerChanNotifier(BaseNotifier):
    def __init__(self, sendkey: str):
        self.sendkey = sendkey
        self.api_url = SERVERCHAN_API.format(key=sendkey)

    async def send(self, report: DigestReport) -> bool:
        title = f"AI 趋势日报 - {report.date}"
        body = self._format_report(report)

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        self.api_url,
                        data={"title": title, "desp": body},
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    if result.get("code") == 0:
                        logger.info("serverchan_sent", title=title)
                        return True
                    else:
                        logger.warning(
                            "serverchan_api_error",
                            code=result.get("code"),
                            message=result.get("message"),
                        )
                        return False

            except Exception:
                logger.warning("serverchan_send_error", attempt=attempt + 1)
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)

        logger.error("serverchan_send_failed", title=title)
        return False

    def _format_report(self, report: DigestReport) -> str:
        """Format the digest report as Markdown."""
        lines: list[str] = []
        stats = report.stats

        # Overview section
        lines.append("## 今日概览\n")
        lines.append(
            f"- GitHub Trending: 采集 {stats.github_fetched} 个项目, "
            f"规则筛选 {stats.github_after_rules} 个, "
            f"推荐 **{stats.github_recommended}** 个"
        )
        lines.append(
            f"- HuggingFace Papers: 采集 {stats.huggingface_fetched} 篇论文, "
            f"规则筛选 {stats.huggingface_after_rules} 篇, "
            f"推荐 **{stats.huggingface_recommended}** 篇"
        )
        lines.append(
            f"- Arxiv: 采集 {stats.arxiv_fetched} 篇论文, "
            f"规则筛选 {stats.arxiv_after_rules} 篇, "
            f"推荐 **{stats.arxiv_recommended}** 篇"
        )

        # GitHub section
        if report.github_items:
            lines.append("\n---\n")
            lines.append("## GitHub Trending 热门项目\n")
            for i, scored in enumerate(report.github_items, 1):
                lines.append(self._format_github_item(i, scored))

        # HuggingFace section
        if report.huggingface_items:
            lines.append("\n---\n")
            lines.append("## HuggingFace 每日精选论文\n")
            for i, scored in enumerate(report.huggingface_items, 1):
                lines.append(self._format_huggingface_item(i, scored))

        # Arxiv section
        if report.arxiv_items:
            lines.append("\n---\n")
            lines.append("## Arxiv 精选论文\n")
            for i, scored in enumerate(report.arxiv_items, 1):
                lines.append(self._format_arxiv_item(i, scored))

        # Footer
        lines.append("\n---\n")
        lines.append("*由 AI Trend Reader 自动生成*")

        body = "\n".join(lines)

        # Server酱 body limit is ~64KB, truncate if needed
        if len(body.encode("utf-8")) > 60000:
            body = body[:20000] + "\n\n...(内容已截断，完整内容请查看日志)"

        return body

    def _format_github_item(self, idx: int, scored: ScoredItem) -> str:
        item = scored.item
        stars = item.metadata.get("stars", "N/A")
        lang = item.metadata.get("language", "")
        lang_str = f" | {lang}" if lang else ""
        stars_today = item.metadata.get("stars_today", 0)

        score = scored.relevance_score
        header = (
            f"### {idx}. [{item.source_id}]({item.url})"
            f" | {stars} stars (+{stars_today} today){lang_str}"
            f" | 评分: {score:.1f}"
        )
        lines = [header]
        if item.description:
            lines.append(f"> {item.description[:200]}")
        if scored.summary_zh:
            lines.append(f"> {scored.summary_zh}")
        if scored.reason:
            lines.append(f"> 推荐理由: {scored.reason}")
        lines.append(f"> 领域: {scored.domain.value}\n")
        return "\n".join(lines)

    def _format_huggingface_item(self, idx: int, scored: ScoredItem) -> str:
        item = scored.item
        upvotes = item.metadata.get("upvotes", 0)
        org = item.metadata.get("organization", "")
        authors = item.metadata.get("authors", [])
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."
        github_repo = item.metadata.get("github_repo", "")

        score = scored.relevance_score
        header = (
            f"### {idx}. [{item.title}]({item.url})"
            f" | {upvotes} upvotes | 评分: {score:.1f}"
        )
        lines = [header]
        if scored.summary_zh:
            lines.append(f"> {scored.summary_zh}")
        if scored.reason:
            lines.append(f"> 推荐理由: {scored.reason}")
        org_str = f" | 机构: {org}" if org else ""
        lines.append(f"> 作者: {author_str}{org_str}")
        if github_repo:
            lines.append(f"> GitHub: {github_repo}")
        lines.append(f"> 领域: {scored.domain.value}\n")
        return "\n".join(lines)

    def _format_arxiv_item(self, idx: int, scored: ScoredItem) -> str:
        item = scored.item
        authors = item.metadata.get("authors", [])
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."
        categories = ", ".join(item.metadata.get("categories", [])[:3])

        lines = [
            f"### {idx}. [{item.title}]({item.url}) | 评分: {scored.relevance_score:.1f}",
        ]
        if scored.summary_zh:
            lines.append(f"> {scored.summary_zh}")
        if scored.reason:
            lines.append(f"> 推荐理由: {scored.reason}")
        lines.append(f"> 作者: {author_str} | 类别: {categories}\n")
        return "\n".join(lines)
