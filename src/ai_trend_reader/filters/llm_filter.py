"""LLM-based intelligent scoring filter."""

from __future__ import annotations

import asyncio
import json

import structlog

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
            topics = ", ".join(item.metadata.get("topics", []))
            meta_str = f"Stars: {stars}, 语言: {lang}, Topics: {topics}"
        else:
            cats = ", ".join(item.metadata.get("categories", []))
            authors = ", ".join(item.metadata.get("authors", [])[:3])
            meta_str = f"类别: {cats}, 作者: {authors}"

        parts.append(f"""### 项目 {i} [{item.source.value}]
- 标题: {item.title}
- 描述: {item.description[:300]}
- {meta_str}
""")

    parts.append("""请返回JSON格式（必须是一个JSON对象，包含"results"数组）：
{
  "results": [
    {
      "index": 1,
      "relevance_score": 8.5,
      "domain": "LLM/大语言模型",
      "summary_zh": "一句话中文摘要(不超过50字)",
      "reason": "推荐理由(不超过30字)"
    }
  ]
}

domain 必须是以下之一: "LLM/大语言模型", "AI图像生成", "AI Agent/工具链", "ML基础设施", "其他AI领域"
relevance_score: 0-10分，6分以上为推荐。""")

    return "\n".join(parts)


class LLMFilter:
    def __init__(self, config: LLMConfig, client: LLMClient):
        self.config = config
        self.client = client
        self.semaphore = asyncio.Semaphore(config.max_concurrent)

    async def score(self, items: list[TrendItem]) -> list[ScoredItem]:
        """Score a list of items using LLM. Returns scored items above threshold."""
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

        # Filter by threshold and sort by score
        qualified = [s for s in scored if s.relevance_score >= self.config.score_threshold]
        qualified.sort(key=lambda x: x.relevance_score, reverse=True)

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
                except json.JSONDecodeError as json_err:
                    logger.error("llm_json_parse_error", attempt=attempt + 1)
                    logger.error("llm_json_parse_error", err=json_err)
                    if attempt == 2:
                        raise
                except Exception:
                    logger.error("llm_batch_error", attempt=attempt + 1)
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
