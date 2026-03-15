"""LLM-based intelligent scoring filter."""

from __future__ import annotations

import asyncio
import json
import math

import structlog

from ai_trend_reader.affiliations import get_affiliation_bonus, get_affiliation_label
from ai_trend_reader.config import LLMConfig
from ai_trend_reader.llm.client import LLMClient
from ai_trend_reader.models import AIDomain, ScoredItem, Source, TrendItem

logger = structlog.get_logger()

SYSTEM_PROMPT = """你是一位 AI 技术趋势分析师，专注于以下领域：
1. LLM/大语言模型 (GPT, LLaMA, 微调, 推理优化等)
2. AI图像生成 (Stable Diffusion, ComfyUI, 文生图等)
3. AI Agent/工具链 (LangChain, AutoGPT, MCP, Function Calling等)
4. ML基础设施 (MLOps, 模型服务, vLLM, 训练框架等)

你需要评估给定的开源项目或学术论文对从事 AI 领域工作的开发者的价值。
评估时请特别关注作者/团队的机构背景——来自顶级大学或知名AI公司的研究通常质量更高。
请严格按照 JSON 格式输出评估结果。"""

DOMAIN_MAP = {
    "LLM/大语言模型": AIDomain.LLM,
    "AI图像生成": AIDomain.IMAGE_GEN,
    "AI Agent/工具链": AIDomain.AGENT,
    "ML基础设施": AIDomain.ML_INFRA,
    "其他AI领域": AIDomain.OTHER,
}


def _build_user_prompt(items: list[TrendItem]) -> str:
    parts = ["请评估以下项目/论文，对每个项目输出JSON对象。\n"]

    for i, item in enumerate(items, 1):
        meta_str = ""
        if item.source == Source.GITHUB:
            stars = item.metadata.get("stars", "N/A")
            lang = item.metadata.get("language", "N/A")
            stars_today = item.metadata.get("stars_today", "N/A")
            meta_str = (
                f"Stars: {stars}, 今日新增: {stars_today}, 语言: {lang}"
            )
        elif item.source == Source.HUGGINGFACE:
            upvotes = item.metadata.get("upvotes", 0)
            org = item.metadata.get("organization", "")
            authors = ", ".join(item.metadata.get("authors", [])[:3])
            gh = item.metadata.get("github_repo", "")
            tier = item.metadata.get("affiliation_tier")
            tier_label = get_affiliation_label(tier) if tier else ""
            meta_str = f"Upvotes: {upvotes}, 机构: {org}, 作者: {authors}"
            if tier_label:
                meta_str += f", 机构等级: {tier_label}"
            if gh:
                meta_str += f", GitHub: {gh}"
        else:
            # Arxiv
            cats = ", ".join(item.metadata.get("categories", []))
            authors = ", ".join(item.metadata.get("authors", [])[:3])
            tier = item.metadata.get("affiliation_tier")
            tier_label = get_affiliation_label(tier) if tier else ""
            meta_str = f"类别: {cats}, 作者: {authors}"
            if tier_label:
                meta_str += f", 机构等级: {tier_label}"

        parts.append(f"""### 项目 {i} [{item.source.value}]
- 标题: {item.title}
- 描述: {item.description[:500]}
- {meta_str}
""")

    parts.append("""请返回JSON格式（必须是一个JSON对象，包含"results"数组）：
{
  "results": [
    {
      "index": 1,
      "relevance_score": 8.5,
      "domain": "LLM/大语言模型",
      "summary_zh": "中文摘要，100-150字，需涵盖论文/项目的核心方法、创新点和主要成果",
      "reason": "推荐理由(不超过30字)"
    }
  ]
}

domain 必须是以下之一: "LLM/大语言模型", "AI图像生成", "AI Agent/工具链", "ML基础设施", "其他AI领域"
relevance_score: 0-10分，越高表示对AI开发者越有价值。
评分时请考虑: 创新性、实用性、技术深度、作者机构背景。
summary_zh: 必须100-150字，详细概述核心内容、方法和贡献。""")

    return "\n".join(parts)


class LLMFilter:
    def __init__(self, config: LLMConfig, client: LLMClient):
        self.config = config
        self.client = client
        self.semaphore = asyncio.Semaphore(config.max_concurrent)

    async def score(
        self,
        items: list[TrendItem],
        top_percent: float | None = None,
    ) -> list[ScoredItem]:
        """Score a list of items using LLM.

        Args:
            items: Items to score.
            top_percent: If set (0-1), return only the top X% of scored items
                         instead of using score_threshold. E.g. 0.1 = top 10%.

        Returns:
            Scored items sorted by score descending.
        """
        if not items:
            return []

        # Split into batches
        batches = [
            items[i : i + self.config.batch_size]
            for i in range(0, len(items), self.config.batch_size)
        ]

        logger.info("llm_scoring_start", total_items=len(items), batches=len(batches))

        tasks = [self._score_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scored: list[ScoredItem] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("llm_batch_failed", error=str(result))
                continue
            scored.extend(result)

        # Apply affiliation bonus to scores
        for s in scored:
            tier = s.item.metadata.get("affiliation_tier")
            if tier is not None:
                bonus = get_affiliation_bonus(tier)
                s.relevance_score = min(10.0, s.relevance_score + bonus)

        # Sort by score descending
        scored.sort(key=lambda x: x.relevance_score, reverse=True)

        # Select output: top_percent or score_threshold
        if top_percent is not None and 0 < top_percent <= 1:
            n = max(1, math.ceil(len(scored) * top_percent))
            qualified = scored[:n]
        else:
            qualified = [s for s in scored if s.relevance_score >= self.config.score_threshold]

        logger.info(
            "llm_scoring_complete",
            scored=len(scored),
            qualified=len(qualified),
            tokens_used=self.client.total_tokens,
        )
        return qualified

    async def _score_batch(self, items: list[TrendItem]) -> list[ScoredItem]:
        """Score a single batch of items."""
        async with self.semaphore:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(items)},
            ]

            for attempt in range(3):
                try:
                    data = await self.client.chat_json(messages)
                    return self._parse_results(items, data)
                except json.JSONDecodeError:
                    logger.warning("llm_json_parse_error", attempt=attempt + 1)
                    if attempt == 2:
                        raise
                except Exception:
                    logger.warning("llm_batch_error", attempt=attempt + 1)
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 ** attempt)

            return []

    def _parse_results(self, items: list[TrendItem], data: dict | list) -> list[ScoredItem]:
        """Parse LLM response into ScoredItems."""
        results_list = data.get("results", []) if isinstance(data, dict) else data

        scored = []
        for result in results_list:
            idx = result.get("index", 0) - 1
            if 0 <= idx < len(items):
                domain_str = result.get("domain", "其他AI领域")
                domain = DOMAIN_MAP.get(domain_str, AIDomain.OTHER)

                score_val = float(result.get("relevance_score", 0))
                score_val = max(0, min(10, score_val))

                scored.append(ScoredItem(
                    item=items[idx],
                    relevance_score=score_val,
                    domain=domain,
                    summary_zh=result.get("summary_zh", ""),
                    reason=result.get("reason", ""),
                ))

        return scored
