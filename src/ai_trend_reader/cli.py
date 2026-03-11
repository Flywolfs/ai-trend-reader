"""CLI entry point for AI Trend Reader."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import structlog

from ai_trend_reader.config import load_settings
from ai_trend_reader.orchestrator import Orchestrator


def configure_logging(level: str) -> None:
    """Configure structlog with the given level."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ai-trend-reader",
        description="Daily AI trend tracker for GitHub repos and Arxiv papers",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config.yaml (default: config.yaml or config.example.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full pipeline but don't send notifications",
    )
    parser.add_argument(
        "--source",
        choices=["github", "arxiv"],
        default=None,
        help="Only fetch from a specific source",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Load settings
    settings = load_settings(args.config)

    # Configure logging
    log_level = "DEBUG" if args.debug else settings.logging.level
    configure_logging(log_level)

    logger = structlog.get_logger()
    logger.info(
        "starting",
        dry_run=args.dry_run,
        source=args.source,
        log_level=log_level,
    )

    # Validate required settings
    if not args.dry_run:
        missing = []
        if not settings.github_token and settings.github.enabled:
            missing.append("GITHUB_TOKEN")
        if not settings.serverchan_sendkey and settings.notify.serverchan.enabled:
            missing.append("SERVERCHAN_SENDKEY")
        if missing:
            logger.warning("missing_env_vars", vars=missing)
    logger.debug("settings", settings=settings)
    # Run orchestrator
    orchestrator = Orchestrator(
        settings=settings,
        dry_run=args.dry_run,
        source=args.source,
    )

    try:
        report = asyncio.run(orchestrator.run())
        logger.info(
            "finished",
            github=report.stats.github_recommended,
            arxiv=report.stats.arxiv_recommended,
        )
        return 0
    except KeyboardInterrupt:
        logger.info("interrupted")
        return 130
    except Exception:
        logger.exception("fatal_error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
