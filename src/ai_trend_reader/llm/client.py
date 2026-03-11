"""LLM client wrapper supporting any OpenAI-compatible API."""

from __future__ import annotations

import json

import structlog
from openai import AsyncOpenAI

from ai_trend_reader.config import LLMConfig

logger = structlog.get_logger()


class LLMClient:
    def __init__(self, config: LLMConfig, api_key: str):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
        self.total_tokens = 0

    async def chat(
        self,
        messages: list[dict[str, str]],
        response_format: dict | None = None,
    ) -> str:
        """Send a chat completion request and return the response text."""
        kwargs: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            if resp.usage:
                self.total_tokens += resp.usage.total_tokens
            content = resp.choices[0].message.content or ""
            return content
        except Exception:
            logger.exception("llm_chat_error")
            raise

    async def chat_json(self, messages: list[dict[str, str]]) -> dict | list:
        """Send a chat request expecting JSON response."""
        text = await self.chat(
            messages,
            response_format={"type": "json_object"},
        )
        return json.loads(text)
