"""Abstract base class for notifiers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trend_reader.models import DigestReport


class BaseNotifier(ABC):
    """Base class for all notification channels."""

    @abstractmethod
    async def send(self, report: DigestReport) -> bool:
        """Send a digest report. Returns True on success."""
        ...
