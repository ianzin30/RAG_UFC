"""Validated generation and retrieval configuration for the V2 pipeline."""

from pydantic import BaseModel, Field, model_validator


class ModelSelection(BaseModel):
    provider: str = "ollama"
    model: str = "phi4:latest"


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


class V2Config(BaseModel):
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
    from ...RuntimeConfig import _read_config_document

    raw = _read_config_document()
    if raw.get("rag_v2", {}).get("enabled") is False:
        raise ValueError("This application supports only RAG V2; remove rag_v2.enabled=false")
    return LLMConfig.model_validate(raw["llm"]), V2Config.model_validate(raw.get("rag_v2", {}))
