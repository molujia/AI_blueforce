"""LLM routing shim for GraphRAG extraction."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMExtractionConfig:
    provider: str = "volcengine_ark"
    task: str = "knowledge_extraction"
    model_name: str = "ep-20260615114505-247zc"
    local_base_url: str = "http://127.0.0.1:8000/v1"


class KnowledgeLLMRouter:
    """OpenAI-compatible router; tests can instantiate without network calls."""

    def __init__(self, config: LLMExtractionConfig | None = None) -> None:
        self.config = config or LLMExtractionConfig()

    def provider_summary(self) -> dict[str, Any]:
        return {
            "provider": self.config.provider,
            "task": self.config.task,
            "model_name": self.config.model_name,
            "ark_key_configured": bool(os.getenv("ARK_API_KEY")),
            "local_base_url": self.config.local_base_url,
            "live_call_requires_user_approval": True,
            "vision_model_requires_user_approval": True,
            "recommended_test_model": "ep-20260615114505-247zc",
        }

    def extract_json(self, text: str) -> dict[str, Any]:
        """Call llm_call_extract when configured; otherwise return a deterministic fallback."""

        try:
            from llm_call_extract.llm_client import ModelRouter

            router = ModelRouter()
            model = router.get_chat_model(self.config.task)
            response = model.invoke([
                {"role": "system", "content": "Extract entities, relations, and rules as strict JSON."},
                {"role": "user", "content": text[:6000]},
            ])
            return json.loads(response.content)
        except Exception:
            return {"entities": [], "relations": [], "rules": [], "fallback": True}