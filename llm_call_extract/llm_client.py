from __future__ import annotations

import base64
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from openai import OpenAI


ROOT = Path(__file__).resolve().parent


@dataclass(slots=True)
class LLMResponse:
    content: str
    usage_metadata: dict[str, int]
    response_id: str | None = None


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def image_to_data_url(path: str | Path) -> str:
    image_path = Path(path)
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def text_part(text: str) -> dict[str, str]:
    return {"type": "text", "text": text}


def image_part(data_url_or_url: str) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": data_url_or_url}}


class Settings:
    def __init__(
        self,
        *,
        config_dir: str | Path = ROOT / "configs",
        secrets_path: str | Path | None = None,
        seed_models_path: str | Path | None = None,
        agent_seed_models_path: str | Path | None = None,
        timeout_seconds: float = 120,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.secrets_path = Path(secrets_path) if secrets_path else self.config_dir / "secrets.local.yaml"
        self.seed_models_path = Path(seed_models_path) if seed_models_path else self.config_dir / "seed_models.yaml"
        self.agent_seed_models_path = (
            Path(agent_seed_models_path) if agent_seed_models_path else self.config_dir / "agent_seed_models.yaml"
        )
        self.timeout_seconds = timeout_seconds
        self.secrets = load_yaml(self.secrets_path)
        self.http_proxy = self._secret_text("http_proxy") or os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or ""
        self.https_proxy = self._secret_text("https_proxy") or os.getenv("HTTPS_PROXY") or os.getenv("https_proxy") or ""
        if self.http_proxy and not self.https_proxy:
            self.https_proxy = self.http_proxy
        self.apply_proxy_environment()

    def load_seed_models_config(self) -> dict[str, Any]:
        return load_yaml(self.seed_models_path) or {"providers": {}, "seed_models": {}}

    def load_agent_seed_models_config(self) -> dict[str, Any]:
        return load_yaml(self.agent_seed_models_path) or {"tasks": {}}

    def api_key_for(self, *, secret_key: str | None, env_key: str | None, literal_key: str | None = None) -> str | None:
        if literal_key:
            return literal_key
        if secret_key:
            value = self._secret_text(secret_key)
            if value:
                return value
        if env_key:
            value = os.getenv(env_key)
            if value:
                return value
        return None

    def apply_proxy_environment(self) -> None:
        for key in ("ALL_PROXY", "all_proxy"):
            os.environ.pop(key, None)
        if self.http_proxy:
            os.environ["HTTP_PROXY"] = self.http_proxy
            os.environ["http_proxy"] = self.http_proxy
        if self.https_proxy:
            os.environ["HTTPS_PROXY"] = self.https_proxy
            os.environ["https_proxy"] = self.https_proxy

    def _secret_text(self, key: str) -> str:
        value = self.secrets.get(key)
        return str(value or "").strip()


class SeedChatModel:
    def __init__(
        self,
        *,
        model_name: str,
        api_key: str,
        base_url: str,
        api: str = "responses",
        temperature: float | None = 0,
        max_output_tokens: int = 1000,
        timeout: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        response_format: str | dict[str, Any] | None = None,
        reasoning: dict[str, Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.api = api
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.tools = tools or []
        self.response_format = response_format
        self.reasoning = reasoning
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def invoke(self, messages: list[dict[str, Any]]) -> LLMResponse:
        if self.api == "chat_completions":
            return self._invoke_chat_completions(messages)
        return self._invoke_responses(messages)

    def begin_session(self) -> "SeedChatSession":
        return SeedChatSession(self)

    def _invoke_responses(self, messages: list[dict[str, Any]], previous_response_id: str | None = None) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "input": [self._message_to_responses_item(message) for message in messages],
            "max_output_tokens": self.max_output_tokens,
        }
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.tools:
            kwargs["tools"] = self.tools
        if self.reasoning:
            kwargs["reasoning"] = self.reasoning
        response_format = self._response_format()
        if response_format:
            kwargs["text"] = {"format": response_format}
        response = self.client.responses.create(**kwargs)
        return LLMResponse(
            content=self._responses_text(response),
            usage_metadata=self._usage_metadata(getattr(response, "usage", None)),
            response_id=str(getattr(response, "id", "") or "") or None,
        )

    def _invoke_chat_completions(self, messages: list[dict[str, Any]]) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": [self._message_to_chat_item(message) for message in messages],
            "max_tokens": self.max_output_tokens,
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        response_format = self._response_format()
        if response_format:
            kwargs["response_format"] = response_format
        response = self.client.chat.completions.create(**kwargs)
        content = ""
        if response.choices:
            content = str(response.choices[0].message.content or "")
        return LLMResponse(content=content, usage_metadata=self._usage_metadata(getattr(response, "usage", None)))

    def _message_to_responses_item(self, message: dict[str, Any]) -> dict[str, Any]:
        role = str(message.get("role") or "user")
        content = message.get("content", "")
        if isinstance(content, list):
            return {"role": role, "content": [self._part_to_responses(part) for part in content]}
        return {"role": role, "content": str(content)}

    def _message_to_chat_item(self, message: dict[str, Any]) -> dict[str, Any]:
        return {"role": str(message.get("role") or "user"), "content": message.get("content", "")}

    def _part_to_responses(self, part: Any) -> dict[str, Any]:
        if not isinstance(part, dict):
            return {"type": "input_text", "text": str(part)}
        part_type = part.get("type")
        if part_type == "text":
            return {"type": "input_text", "text": str(part.get("text") or "")}
        if part_type == "image_url":
            image_url = part.get("image_url") if isinstance(part.get("image_url"), dict) else {}
            return {"type": "input_image", "image_url": str(image_url.get("url") or part.get("url") or "")}
        if part_type in {"input_text", "input_image"}:
            return part
        return {"type": "input_text", "text": str(part)}

    def _response_format(self) -> dict[str, Any] | None:
        if not self.response_format:
            return None
        if isinstance(self.response_format, dict):
            return self.response_format
        if str(self.response_format) == "json_object":
            return {"type": "json_object"}
        return None

    def _responses_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text)
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks).strip()

    def _usage_metadata(self, usage: Any) -> dict[str, int]:
        if usage is None:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        input_tokens = self._int_attr(usage, "input_tokens", "prompt_tokens")
        output_tokens = self._int_attr(usage, "output_tokens", "completion_tokens")
        total_tokens = self._int_attr(usage, "total_tokens") or input_tokens + output_tokens
        return {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens}

    def _int_attr(self, obj: Any, *names: str) -> int:
        for name in names:
            if isinstance(obj, dict) and name in obj:
                try:
                    return int(obj.get(name) or 0)
                except (TypeError, ValueError):
                    return 0
            if hasattr(obj, name):
                try:
                    return int(getattr(obj, name) or 0)
                except (TypeError, ValueError):
                    return 0
        return 0


class SeedChatSession:
    def __init__(self, model: SeedChatModel) -> None:
        self.model = model
        self.session_id = f"llm_session_{uuid4().hex[:12]}"
        self.previous_response_id: str | None = None
        self.history: list[dict[str, Any]] = []

    def invoke(self, messages: list[dict[str, Any]]) -> LLMResponse:
        if self.model.api != "responses":
            response = self.model.invoke([*self.history, *messages])
            self.history.extend(messages)
            self.history.append({"role": "assistant", "content": response.content})
            return response
        if self.previous_response_id:
            try:
                response = self.model._invoke_responses(messages, previous_response_id=self.previous_response_id)
            except Exception:
                response = self.model._invoke_responses([*self.history, *messages])
        else:
            response = self.model._invoke_responses([*self.history, *messages])
        self.history.extend(messages)
        self.history.append({"role": "assistant", "content": response.content})
        self.previous_response_id = response.response_id or self.previous_response_id
        return response


class ModelRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.seed_catalog = self.settings.load_seed_models_config()
        self.seed_selection = self.settings.load_agent_seed_models_config()
        self.model_config = self._resolve_all_task_configs()

    def get_chat_model(self, task: str) -> SeedChatModel:
        config = self.model_config.get(task)
        if not config:
            raise KeyError(f"No model config for task: {task}")
        api_key = self._api_key_for_config(config)
        if not api_key:
            raise RuntimeError(f"Missing API key for task `{task}` / provider `{config.get('provider')}`")
        return SeedChatModel(
            model_name=str(config["model_name"]),
            api_key=api_key,
            base_url=str(config.get("base_url") or "https://api.openai.com/v1"),
            api=str(config.get("api") or "responses"),
            temperature=None if config.get("omit_temperature") else float(config.get("temperature", 0)),
            max_output_tokens=int(config.get("max_output_tokens", 1000)),
            timeout=float(self.settings.timeout_seconds),
            tools=config.get("tools") if isinstance(config.get("tools"), list) else None,
            response_format=config.get("response_format"),
            reasoning=config.get("reasoning") if isinstance(config.get("reasoning"), dict) else None,
        )

    def begin_session(self, task: str) -> SeedChatSession:
        return self.get_chat_model(task).begin_session()

    def health_check(self, task: str) -> LLMResponse:
        model = self.get_chat_model(task)
        return model.invoke(
            [
                {"role": "system", "content": "You are a health check endpoint. Return strict JSON only."},
                {"role": "user", "content": "Return a JSON object with status OK and no other text."},
            ]
        )

    def _resolve_all_task_configs(self) -> dict[str, dict[str, Any]]:
        tasks = self.seed_selection.get("tasks") if isinstance(self.seed_selection.get("tasks"), dict) else {}
        return {task: self._resolve_task_config(task) for task in tasks}

    def _resolve_task_config(self, task: str) -> dict[str, Any]:
        selection = self._selection_for_task(task)
        seed_id = str(selection.get("seed_model") or selection.get("model") or selection.get("seed") or "").strip()
        if not seed_id:
            return dict(selection)
        seed_models = self.seed_catalog.get("seed_models") if isinstance(self.seed_catalog.get("seed_models"), dict) else {}
        seed = dict(seed_models.get(seed_id, {}))
        if not seed:
            raise KeyError(f"Seed model `{seed_id}` referenced by task `{task}` is not defined.")
        providers = self.seed_catalog.get("providers") if isinstance(self.seed_catalog.get("providers"), dict) else {}
        provider_id = str(seed.get("provider") or selection.get("provider") or "openai")
        provider = dict(providers.get(provider_id, {}))
        config = {**provider, **seed, **selection}
        config["seed_model"] = seed_id
        config["provider"] = provider_id
        config.setdefault("model_alias", seed.get("model_alias") or seed_id)
        config.setdefault("model_name", seed.get("model_name") or seed_id)
        if provider.get("tools") and not seed.get("tools") and not selection.get("tools"):
            config["tools"] = provider["tools"]
        return config

    def _selection_for_task(self, task: str) -> dict[str, Any]:
        tasks = self.seed_selection.get("tasks") if isinstance(self.seed_selection.get("tasks"), dict) else {}
        raw = tasks.get(task)
        if isinstance(raw, str):
            return {"seed_model": raw}
        if isinstance(raw, dict):
            return dict(raw)
        return {}

    def _api_key_for_config(self, config: dict[str, Any]) -> str | None:
        explicit = self.settings.api_key_for(
            secret_key=config.get("api_key_secret"),
            env_key=config.get("api_key_env"),
            literal_key=config.get("api_key"),
        )
        if explicit:
            return explicit
        provider = str(config.get("provider") or "")
        if provider == "volcengine_ark":
            return self.settings.api_key_for(secret_key="ark_api_key", env_key="ARK_API_KEY")
        if provider.startswith("openai"):
            return self.settings.api_key_for(secret_key="openai_api_key", env_key="OPENAI_API_KEY")
        return None
