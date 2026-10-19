"""Validated generation and retrieval configuration for the V2 pipeline."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal


class ModelSelection(BaseModel):
    provider: str = "ollama"
    model: str = "phi4:latest"


class VLLMSamplingOptions(BaseModel):
    """Optional wire parameters; omitted values keep server defaults."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    top_p: float | None = Field(default=None, gt=0, le=1)
    top_k: int | None = Field(default=None, ge=-1)
    min_p: float | None = Field(default=None, ge=0, le=1)
    seed: int | None = Field(default=None, ge=0)
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    repetition_penalty: float | None = Field(default=None, gt=0)
    stop: str | list[str] | None = None

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, value):
        if value == 0:
            raise ValueError("top_k must be -1 (disabled) or a positive integer")
        return value

    @field_validator("stop")
    @classmethod
    def validate_stop(cls, value):
        if value is not None:
            values = [value] if isinstance(value, str) else value
            if not values or any(not item for item in values):
                raise ValueError("stop must contain nonempty strings")
        return value


class VLLMSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    base_url: str | None = None
    enable_thinking: bool | None = None
    options: VLLMSamplingOptions = Field(default_factory=VLLMSamplingOptions)


class SparkSettings(VLLMSettings):
    base_url: str = 'https://spark.ollama.atlab.ufc.br/api'
    enable_thinking: bool = False
    tokenizer: str = 'nvidia/Qwen3.6-35B-A3B-NVFP4'
    input_margin: int = Field(default=512, ge=0)
    api_key_env: str = 'LLM_API_KEY'


class LLMConfig(ModelSelection):
    roles: dict[str, ModelSelection] = Field(default_factory=dict)
    providers: dict[str, dict] = Field(default_factory=dict)
    temperature: float = 0
    num_ctx: int = Field(default=8192, ge=1024)
    timeout_seconds: int = Field(default=420, gt=0)
    max_output_tokens: int = Field(default=2048, gt=0)
    # Structured agent roles should not be allowed to consume the generic
    # answer budget.  This keeps local models from rambling until truncation
    # while leaving a configurable default for future providers/roles.
    role_max_output_tokens: dict[str, int] = Field(
        default_factory=lambda: {
            "planner": 512,
            "research": 384,
            "reasoning": 768,
            "answer": 768,
            "verification": 512,
            "source_focus": 384,
        }
    )

    @model_validator(mode="after")
    def validate_vllm_settings(self):
        if "vllm" in self.providers:
            VLLMSettings.model_validate(self.providers["vllm"])
        if "spark" in self.providers:
            SparkSettings.model_validate(self.providers["spark"])
        return self


class V2Config(BaseModel):
    chunking_strategy: Literal["legacy", "markdown_blocks_v1"] = "legacy"
    child_tokens: int = Field(default=384, ge=32)
    parent_tokens: int = Field(default=1536, ge=64)
    search_k: int = Field(default=30, gt=0)
    rrf_k: int = Field(default=60, gt=0)
    rerank_k: int = Field(default=30, gt=0)
    batch_size: int = Field(default=4, gt=0)
    device: str = "cpu"
    subset_cache_mb: int = Field(default=128, ge=0)
    max_hops: int = Field(default=3, ge=1, le=10)
    queries_per_hop: int = Field(default=3, ge=1, le=10)
    # BGE token counts are not identical to the generator tokenizer.  Leave
    # headroom inside Ollama's 8k default for the typed schema and response.
    context_tokens: int = Field(default=3000, ge=128)
    max_map_batches: int = Field(default=16, ge=1)
    embedding_model: str = "BAAI/bge-m3"
    embedding_provider: Literal["flagembedding", "ollama"] = "flagembedding"
    embedding_ollama_model: str = "embeddinggemma:latest"
    embedding_ollama_base_url: str = "http://localhost:11434"
    embedding_timeout_seconds: int = Field(default=120, gt=0)
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    @model_validator(mode="after")
    def validate_limits(self):
        if self.parent_tokens < self.child_tokens:
            raise ValueError("parent_tokens must be >= child_tokens")
        if self.parent_tokens > self.context_tokens:
            raise ValueError("parent_tokens must fit context_tokens")
        if self.device not in {"cpu", "mps", "cuda"}:
            raise ValueError("device must be cpu, mps or cuda")
        return self


def load_settings():
    from ...RuntimeConfig import _read_config_document, resolve_application_llm

    raw = _read_config_document()
    if raw.get("rag_v2", {}).get("enabled") is False:
        raise ValueError("This application supports only RAG V2; remove rag_v2.enabled=false")
    llm = LLMConfig.model_validate(resolve_application_llm(raw['llm']))
    if llm.provider not in {'spark', 'vllm', 'ufc', 'ollama'} or any(r.provider not in {'spark', 'vllm', 'ufc', 'ollama'} for r in llm.roles.values()):
        raise ValueError('Unknown provider in application configuration')
    return llm, V2Config.model_validate(raw.get('rag_v2', {}))
