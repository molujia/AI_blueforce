#!/usr/bin/env python3
"""Standalone LLM caller extracted from the red-team decision system.

Copy this file into another project when you need the same LLM calling layer.

What it supports:
- Online test path: gpt-5-nano via official OpenAI API.
- Offline/local path: OpenAI-compatible local gateways, such as OpenWebUI,
  LM Studio, vLLM, Ollama-compatible gateways, or other /v1 chat endpoints.
- Config file + environment variable overrides.
- Connectivity preflight before running a workflow.
- <think>...</think> stripping for local reasoning models.
- JSON-object extraction for agent-style structured outputs.

Minimal dependency:
    pip install openai

Recommended online config:
    model = "gpt-5-nano"
    base_url = ""  # blank uses official OpenAI client default / Responses API
    api_key = "$OPENAI_API_KEY"

Recommended local config:
    model = "your-local-model"
    base_url = "http://127.0.0.1:3000/api/v1"
    api_key = "your-local-token-or-placeholder"
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


DEFAULT_CONFIG_FILE = "llm_migration_config.json"


@dataclass
class LLMConfig:
    model: str = "gpt-5-nano"
    base_url: str = ""
    api_key: str = ""
    proxy_url: str = ""
    timeout_seconds: float = 20
    retries: int = 1


class LLMConnectionError(RuntimeError):
    """Raised when the configured LLM endpoint cannot be reached."""


def load_llm_config(config_file: str | Path = DEFAULT_CONFIG_FILE) -> LLMConfig:
    """Load config from JSON, then apply environment variable overrides.

    Environment variable priority:
    - RED_TEAM_MODEL / RED_TEAM_BASE_URL / RED_TEAM_API_KEY
    - OPENWEBUI_BASE_URL / OPENWEBUI_API_KEY
    - OPENAI_BASE_URL / OPENAI_API_KEY
    """

    data: Dict[str, Any] = {}
    path = Path(config_file)
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data.update(loaded)

    model = os.getenv("RED_TEAM_MODEL", str(data.get("model") or "gpt-5-nano"))
    base_url = os.getenv(
        "RED_TEAM_BASE_URL",
        os.getenv("OPENWEBUI_BASE_URL", os.getenv("OPENAI_BASE_URL", str(data.get("base_url") or ""))),
    )
    api_key = os.getenv(
        "RED_TEAM_API_KEY",
        os.getenv("OPENWEBUI_API_KEY", os.getenv("OPENAI_API_KEY", str(data.get("api_key") or ""))),
    )
    proxy_url = os.getenv(
        "RED_TEAM_PROXY_URL",
        os.getenv("OPENAI_PROXY_URL", os.getenv("HTTPS_PROXY", str(data.get("proxy_url") or ""))),
    )
    timeout = float(data.get("timeout_seconds") or data.get("llm_timeout_seconds") or 20)
    retries = int(data.get("retries") or 1)
    return LLMConfig(model=model, base_url=base_url, api_key=api_key, proxy_url=proxy_url, timeout_seconds=timeout, retries=retries)


def create_llm_client(*, base_url: str = "", api_key: str = "") -> OpenAI:
    """Create an OpenAI SDK client.

    If base_url is blank, this uses official OpenAI defaults.
    If base_url is set, this targets an OpenAI-compatible gateway.
    """

    key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENWEBUI_API_KEY") or "sk-no-key-required"
    proxy_url = os.getenv("RED_TEAM_PROXY_URL") or os.getenv("OPENAI_PROXY_URL")
    if proxy_url:
        os.environ.setdefault("HTTP_PROXY", proxy_url)
        os.environ.setdefault("HTTPS_PROXY", proxy_url)
    kwargs: Dict[str, Any] = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def call_llm_chat(
    messages: List[Dict[str, str]],
    *,
    model: str,
    base_url: str = "",
    api_key: str = "",
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
    timeout: Optional[float] = None,
    retries: int = 1,
    extra_create_kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    """Call an online or local OpenAI-compatible LLM and return assistant text.

    Behavior:
    - gpt-5* + blank base_url: use OpenAI Responses API.
    - otherwise: use Chat Completions, suitable for OpenWebUI/local gateways.
    """

    client = create_llm_client(base_url=base_url, api_key=api_key)
    use_responses_api = model.lower().startswith("gpt-5") and not base_url

    if use_responses_api:
        response_kwargs: Dict[str, Any] = {"model": model, "input": messages}
        if max_tokens is not None:
            response_kwargs["max_output_tokens"] = max_tokens
        response_kwargs["reasoning"] = {"effort": "minimal"}
        if timeout is not None:
            response_kwargs["timeout"] = timeout
        if extra_create_kwargs:
            response_kwargs.update(extra_create_kwargs)
        resp = client.responses.create(**response_kwargs)
        output_text = getattr(resp, "output_text", "") or ""
        if not output_text and getattr(resp, "status", None) == "incomplete":
            raise RuntimeError("LLM response incomplete before final text; increase max_tokens.")
        return output_text

    create_kwargs: Dict[str, Any] = {"model": model, "messages": messages}
    if not model.lower().startswith("gpt-5"):
        create_kwargs["temperature"] = temperature
    if max_tokens is not None:
        if model.lower().startswith("gpt-5"):
            create_kwargs["max_completion_tokens"] = max_tokens
        else:
            create_kwargs["max_tokens"] = max_tokens
    if timeout is not None:
        create_kwargs["timeout"] = timeout
    if extra_create_kwargs:
        create_kwargs.update(extra_create_kwargs)

    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(**create_kwargs)
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_err = exc
            if attempt == retries:
                raise
            time.sleep(1.5 * attempt)

    if last_err is not None:
        raise last_err
    raise RuntimeError("Unreachable LLM call state")


def is_connection_failure(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    markers = [
        "connection",
        "connect",
        "timeout",
        "timed out",
        "readtimeout",
        "api connection",
        "network",
        "connection error",
    ]
    return any(marker in text for marker in markers)


def preflight_llm_connection(config: LLMConfig) -> None:
    """Fail fast before a workflow starts if the LLM endpoint is unreachable."""

    if config.proxy_url:
        os.environ.setdefault("HTTP_PROXY", config.proxy_url)
        os.environ.setdefault("HTTPS_PROXY", config.proxy_url)
    try:
        call_llm_chat(
            [{"role": "user", "content": "Return exactly OK."}],
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=0.0,
            max_tokens=256,
            timeout=max(2.0, min(8.0, config.timeout_seconds)),
            retries=1,
        )
    except Exception as exc:
        if is_connection_failure(exc):
            raise LLMConnectionError("Connection error.") from exc
        raise


def split_think_blocks(text: str) -> Tuple[str, str]:
    """Remove <think> blocks from model output.

    Returns:
        (cleaned_text, extracted_thoughts)
    """

    thoughts: List[str] = []

    def collect(match: re.Match[str]) -> str:
        thoughts.append(match.group(1).strip())
        return ""

    cleaned = re.sub(r"<think>(.*?)</think>", collect, text or "", flags=re.I | re.S)
    return cleaned.strip(), "\n\n".join(part for part in thoughts if part)


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from a model response."""

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text or ""):
        try:
            obj, _ = decoder.raw_decode(text[match.start() :])
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def call_json_agent(
    messages: List[Dict[str, str]],
    *,
    config: LLMConfig,
    max_tokens: int = 1400,
) -> Tuple[Dict[str, Any], str, str]:
    """Call an LLM and parse a JSON object from its response.

    Returns:
        (parsed_json, thoughts, cleaned_text)
    """

    text = call_llm_chat(
        messages,
        model=config.model,
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=0.2,
        max_tokens=max_tokens,
        timeout=config.timeout_seconds,
        retries=config.retries,
    )
    cleaned, thoughts = split_think_blocks(text)
    parsed = extract_json_object(cleaned)
    if not parsed:
        raise ValueError("LLM response is not valid JSON")
    return parsed, thoughts, cleaned


def smoke_test(config_file: str | Path = DEFAULT_CONFIG_FILE) -> str:
    """Small online/local connectivity test."""

    config = load_llm_config(config_file)
    if config.proxy_url:
        os.environ.setdefault("HTTP_PROXY", config.proxy_url)
        os.environ.setdefault("HTTPS_PROXY", config.proxy_url)
    preflight_llm_connection(config)
    return call_llm_chat(
        [
            {"role": "system", "content": "You are a concise test assistant. Reply with exactly: smoke test ok."},
            {"role": "user", "content": "Reply with exactly: smoke test ok"},
        ],
        model=config.model,
        base_url=config.base_url,
        api_key=config.api_key,
        temperature=0,
        max_tokens=256,
        timeout=config.timeout_seconds,
        retries=config.retries,
    ).strip()


if __name__ == "__main__":
    cfg = load_llm_config()
    print(f"model={cfg.model!r} base_url={cfg.base_url!r} api_key={'set' if cfg.api_key else 'missing'}")
    try:
        print(smoke_test())
    except LLMConnectionError as exc:
        raise SystemExit(str(exc))
