"""Abstract base class for data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ai_trend_reader.models import TrendItem


class BaseSource(ABC):
    """Base class for all data sources."""

    @abstractmethod
    async def fetch(self, target_date: date | None = None) -> list[TrendItem]:
        """Fetch trend items from the source.

        Args:
            target_date: 目标日期，如果为None则使用当天日期
        """
        ...
