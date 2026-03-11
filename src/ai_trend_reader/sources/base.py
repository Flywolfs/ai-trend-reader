"""Abstract base class for data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trend_reader.models import TrendItem


class BaseSource(ABC):
    """Base class for all data sources."""

    @abstractmethod
    async def fetch(self) -> list[TrendItem]:
        """Fetch trend items from the source."""
        ...
