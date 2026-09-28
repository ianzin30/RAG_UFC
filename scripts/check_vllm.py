"""One-shot connectivity and chat smoke test for the configured vLLM server."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.service.rag.v2.Config import load_settings, ModelSelection
from application.service.rag.v2.Providers import ProviderError, VLLMProvider


def main() -> int:
    config, _ = load_settings()
    if config.provider != "vllm":
        print(f"Configured provider is {config.provider!r}, expected 'vllm'", file=sys.stderr)
        return 1
    smoke_config = config.model_copy(update={"temperature": 0, "max_output_tokens": 16})
    provider = VLLMProvider(
        ModelSelection(provider="vllm", model=config.model), smoke_config
    )
    try:
        provider.resolve()  # Exactly one GET /models.
        print("vLLM reachable")
        print("served models:")
        for model in provider.served_models:
            print(f"  - {model}")
        answer = provider.generate("Responda apenas: OK")  # Exactly one POST.
    except ProviderError as exc:
        print(f"vLLM smoke test failed: {exc}", file=sys.stderr)
        return 1
    print(f"chat completion: {answer!r}")
    if not re.search(r"\b(?:ok|okay)\b", answer, re.IGNORECASE):
        print("Response was not equivalent to OK", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
