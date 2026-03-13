"""Main orchestrator that coordinates the entire pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import structlog

from ai_trend_reader.config import Settings
from ai_trend_reader.filters.llm_filter import LLMFilter
from ai_trend_reader.filters.rule_filter import RuleFilter
from ai_trend_reader.llm.client import LLMClient
from ai_trend_reader.models import DigestReport, DigestStats, ScoredItem, Source, TrendItem
from ai_trend_reader.notify.serverchan import ServerChanNotifier
from ai_trend_reader.sources.arxiv import ArxivSource
from ai_trend_reader.sources.github import GitHubSource
from ai_trend_reader.sources.huggingface import HuggingFaceSource
from ai_trend_reader.storage.database import Database

logger = structlog.get_logger()


class Orchestrator:
    def __init__(self, settings: Settings, dry_run: bool = False, source: str | None = None):
        self.settings = settings
        self.dry_run = dry_run
        self.source_filter = source  # "github", "arxiv", "huggingface", or None (all)

    async def run(self) -> DigestReport:
        """Execute the full pipeline."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info("pipeline_start", date=today, dry_run=self.dry_run)

        stats = DigestStats()

        # Initialize database
        db = Database(self.settings.storage)
        await db.initialize()

        try:
            # Step 1: Fetch from sources
            github_items, arxiv_items, hf_items = await self._fetch_sources()
            stats.github_fetched = len(github_items)
            stats.arxiv_fetched = len(arxiv_items)
            stats.huggingface_fetched = len(hf_items)
            logger.info(
                "fetch_complete",
                github=len(github_items),
                arxiv=len(arxiv_items),
                huggingface=len(hf_items),
            )

            all_items = github_items + arxiv_items + hf_items

            # Step 2: Deduplicate against seen items
            if all_items:
                unseen_ids = await db.filter_unseen([i.source_id for i in all_items])
                all_items = [i for i in all_items if i.source_id in unseen_ids]
                logger.info("dedup_complete", remaining=len(all_items))

            # Step 3: Rule-based filtering
            rule_filter = RuleFilter(
                self.settings.rule_filter,
                self.settings.github,
                self.settings.arxiv,
                self.settings.huggingface,
            )
            filtered_items = await rule_filter.filter(all_items)

            github_filtered = [i for i in filtered_items if i.source == Source.GITHUB]
            arxiv_filtered = [i for i in filtered_items if i.source == Source.ARXIV]
            hf_filtered = [i for i in filtered_items if i.source == Source.HUGGINGFACE]
            stats.github_after_rules = len(github_filtered)
            stats.arxiv_after_rules = len(arxiv_filtered)
            stats.huggingface_after_rules = len(hf_filtered)

            # Step 4: LLM scoring (if API key is configured)
            github_scored: list[ScoredItem] = []
            arxiv_scored: list[ScoredItem] = []
            hf_scored: list[ScoredItem] = []

            if self.settings.llm_api_key:
                llm_client = LLMClient(self.settings.llm, self.settings.llm_api_key)
                llm_filter = LLMFilter(self.settings.llm, llm_client)

                if github_filtered:
                    github_scored = await llm_filter.score(github_filtered)
                if arxiv_filtered:
                    arxiv_scored = await llm_filter.score(arxiv_filtered)
                if hf_filtered:
                    hf_scored = await llm_filter.score(hf_filtered)
            else:
                logger.warning("llm_api_key_not_set_skipping_scoring")
                # Fallback: create ScoredItems without LLM scoring
                github_scored = [
                    ScoredItem(item=i, relevance_score=7.0) for i in github_filtered
                ]
                arxiv_scored = [
                    ScoredItem(item=i, relevance_score=7.0) for i in arxiv_filtered
                ]
                hf_scored = [
                    ScoredItem(item=i, relevance_score=7.0) for i in hf_filtered
                ]

            # Step 5: Take top N
            github_top = github_scored[: self.settings.notify.max_github_items]
            arxiv_top = arxiv_scored[: self.settings.notify.max_arxiv_items]
            hf_top = hf_scored[: self.settings.notify.max_huggingface_items]

            stats.github_recommended = len(github_top)
            stats.arxiv_recommended = len(arxiv_top)
            stats.huggingface_recommended = len(hf_top)

            # Build report
            report = DigestReport(
                date=today,
                github_items=github_top,
                arxiv_items=arxiv_top,
                huggingface_items=hf_top,
                stats=stats,
            )

            # Step 6: Send notification
            if not self.dry_run:
                if self.settings.serverchan_sendkey and self.settings.notify.serverchan.enabled:
                    notifier = ServerChanNotifier(self.settings.serverchan_sendkey)
                    success = await notifier.send(report)

                    if not success:
                        self._save_backup(report, notifier)
                else:
                    logger.warning("serverchan_not_configured")

                # Mark all fetched items as seen
                seen_pairs = [
                    (i.source_id, i.source.value)
                    for i in github_items + arxiv_items + hf_items
                ]
                await db.mark_seen(seen_pairs)

                # Save digest history
                await db.save_digest(
                    today, stats.github_recommended, stats.arxiv_recommended, ""
                )

                # Cleanup old records
                await db.cleanup_old_records()
            else:
                logger.info("dry_run_skipping_notification")
                notifier = ServerChanNotifier(self.settings.serverchan_sendkey or "dry-run")
                preview = notifier._format_report(report)
                print("\n" + "=" * 60)
                print("DRY RUN - Report Preview:")
                print("=" * 60)
                print(preview)
                print("=" * 60 + "\n")

            logger.info(
                "pipeline_complete",
                github_recommended=stats.github_recommended,
                arxiv_recommended=stats.arxiv_recommended,
                huggingface_recommended=stats.huggingface_recommended,
            )
            return report

        finally:
            await db.close()

    async def _fetch_sources(
        self,
    ) -> tuple[list[TrendItem], list[TrendItem], list[TrendItem]]:
        """Fetch items from enabled sources concurrently."""
        github_items: list[TrendItem] = []
        arxiv_items: list[TrendItem] = []
        hf_items: list[TrendItem] = []

        tasks = []

        if self.source_filter in (None, "github") and self.settings.github.enabled:
            github_source = GitHubSource(self.settings.github, self.settings.github_token)
            tasks.append(("github", github_source.fetch()))

        if self.source_filter in (None, "arxiv") and self.settings.arxiv.enabled:
            arxiv_source = ArxivSource(self.settings.arxiv)
            tasks.append(("arxiv", arxiv_source.fetch()))

        if self.source_filter in (None, "huggingface") and self.settings.huggingface.enabled:
            hf_source = HuggingFaceSource(self.settings.huggingface)
            tasks.append(("huggingface", hf_source.fetch()))

        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        for (name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error("source_fetch_failed", source=name, error=str(result))
                continue
            if name == "github":
                github_items = result
            elif name == "arxiv":
                arxiv_items = result
            elif name == "huggingface":
                hf_items = result

        return github_items, arxiv_items, hf_items

    def _save_backup(self, report: DigestReport, notifier: ServerChanNotifier) -> None:
        """Save report to local file as backup when notification fails."""
        try:
            backup_dir = Path("data")
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / f"backup_{report.date}.md"
            content = notifier._format_report(report)
            backup_file.write_text(content, encoding="utf-8")
            logger.info("backup_saved", path=str(backup_file))
        except Exception:
            logger.exception("backup_save_failed")
