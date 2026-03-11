"""Abstract base class for filters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trend_reader.models import TrendItem


class BaseFilter(ABC):
    """Base class for all filters."""

    @abstractmethod
    async def filter(self, items: list[TrendItem]) -> list[TrendItem]:
        """Filter items and return those that pass."""
        ...
