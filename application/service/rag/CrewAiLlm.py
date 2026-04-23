"""CrewAI LLM adapter backed by the UFC Ollama-compatible endpoint."""
# Simple: Connect AI agents to local language model

from __future__ import annotations

from typing import Any

from pydantic import PrivateAttr

from ..UfcOllama import UFCOllamaClient

try:
    from crewai.llms.base_llm import BaseLLM
except Exception:  # pragma: no cover - CrewAI is optional at runtime.
    BaseLLM = None


if BaseLLM is not None:

    class CrewAIUFCOllamaLLM(BaseLLM):
        """Minimal BaseLLM adapter so CrewAI uses the project LLM instead of its OpenAI fallback."""

        provider: str = "ollama"
        llm_type: str = "base"
        _client: UFCOllamaClient = PrivateAttr()

        def __init__(
            self,
            *,
            api_key: str,
            model: str,
            base_url: str,
            temperature: float | None = None,
        ) -> None:
            super().__init__(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                provider="ollama",
            )
            self._client = UFCOllamaClient(
                api_key=api_key,
                model_name=model,
                api_url=base_url,
            )

        def call(
            self,
            messages,
            tools=None,
            callbacks=None,
            available_functions=None,
            from_task=None,
            from_agent=None,
            response_model=None,
        ) -> str:
            prompt = self._build_prompt(messages)
            response = self._client.invoke(prompt)
            return self._apply_stop_words(response)

        async def acall(
            self,
            messages,
            tools=None,
            callbacks=None,
            available_functions=None,
            from_task=None,
            from_agent=None,
            response_model=None,
        ) -> str:
            return self.call(
                messages,
                tools=tools,
                callbacks=callbacks,
                available_functions=available_functions,
                from_task=from_task,
                from_agent=from_agent,
                response_model=response_model,
            )

        def _build_prompt(self, messages: str | list[dict[str, Any]]) -> str:
            if isinstance(messages, str):
                return messages

            parts: list[str] = []
            for message in messages or []:
                role = str((message or {}).get("role") or "user").strip().upper()
                content = self._coerce_message_content((message or {}).get("content"))
                if not content:
                    continue
                parts.append(f"{role}:\n{content}")
            return "\n\n".join(parts).strip()

        def _coerce_message_content(self, content: Any) -> str:
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                blocks: list[str] = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text = str(item.get("text") or "").strip()
                            if text:
                                blocks.append(text)
                        elif "content" in item:
                            text = str(item.get("content") or "").strip()
                            if text:
                                blocks.append(text)
                    elif item is not None:
                        text = str(item).strip()
                        if text:
                            blocks.append(text)
                return "\n".join(blocks).strip()
            if content is None:
                return ""
            return str(content).strip()


def build_crewai_llm(
    *,
    api_key: str,
    model_name: str,
    api_url: str,
) -> object | None:
    """Build the CrewAI adapter only when CrewAI is available."""

    if BaseLLM is None:
        return None

    return CrewAIUFCOllamaLLM(
        api_key=api_key,
        model=model_name,
        base_url=api_url,
    )
