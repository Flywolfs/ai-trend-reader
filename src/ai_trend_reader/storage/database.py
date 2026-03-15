"""SQLite storage for deduplication and history tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite
import structlog

from ai_trend_reader.config import StorageConfig

logger = structlog.get_logger()


class Database:
    def __init__(self, config: StorageConfig):
        self.db_path = Path(config.db_path)
        self.retention_days = config.retention_days
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database and tables if needed."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS seen_items (
                source_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'seen',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS digest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                github_count INTEGER DEFAULT 0,
                arxiv_count INTEGER DEFAULT 0,
                huggingface_count INTEGER DEFAULT 0,
                sent_at TEXT NOT NULL,
                raw_content TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_seen_source ON seen_items(source);
            CREATE INDEX IF NOT EXISTS idx_seen_first ON seen_items(first_seen_at);
            CREATE INDEX IF NOT EXISTS idx_seen_status ON seen_items(status);
        """)
        await self._db.commit()
        logger.info("database_initialized", path=str(self.db_path))

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def filter_unseen(self, source_ids: list[str]) -> set[str]:
        """Return the subset of source_ids that have NOT been seen before."""
        if not source_ids or not self._db:
            return set(source_ids)

        placeholders = ",".join("?" for _ in source_ids)
        cursor = await self._db.execute(
            f"SELECT source_id FROM seen_items WHERE source_id IN ({placeholders})",
            source_ids,
        )
        rows = await cursor.fetchall()
        seen = {row[0] for row in rows}
        return set(source_ids) - seen

    async def mark_seen(self, items: list[tuple[str, str]], status: str = "seen") -> None:
        """Mark items as seen. Each item is (source_id, source).

        Args:
            items: List of (source_id, source) tuples.
            status: 'seen' for normal items, 'filtered' for discarded items.
        """
        if not items or not self._db:
            return

        now = datetime.now(timezone.utc).isoformat()
        await self._db.executemany(
            """INSERT INTO seen_items (source_id, source, status, first_seen_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(source_id) DO UPDATE SET last_seen_at = ?, status = ?""",
            [(sid, src, status, now, now, now, status) for sid, src in items],
        )
        await self._db.commit()

    async def save_digest(
        self,
        date: str,
        github_count: int,
        arxiv_count: int,
        content: str,
        huggingface_count: int = 0,
    ) -> None:
        """Save digest history."""
        if not self._db:
            return

        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            """INSERT OR REPLACE INTO digest_history
               (date, github_count, arxiv_count, huggingface_count, sent_at, raw_content)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date, github_count, arxiv_count, huggingface_count, now, content),
        )
        await self._db.commit()

    async def cleanup_old_records(self) -> None:
        """Remove records older than retention_days."""
        if not self._db:
            return

        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        ).isoformat()

        await self._db.execute(
            "DELETE FROM seen_items WHERE first_seen_at < ?", (cutoff,)
        )
        await self._db.execute(
            "DELETE FROM digest_history WHERE date < ?",
            (cutoff[:10],),
        )
        await self._db.commit()
        logger.info("database_cleanup_complete", retention_days=self.retention_days)
