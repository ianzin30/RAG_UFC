"""Bootstrap and model setup for the RAG service."""
# Simple: Start up search system and load language models

import importlib.util
import os
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
import torch
from transformers import BitsAndBytesConfig

from ...UfcOllama import DEFAULT_UFC_API_URL, UFCOllamaClient
from ..CrewAiAgents import build_crewai_agent_bundle
from ..CrewAiLlm import build_crewai_llm
from ...RuntimeConfig import get_runtime_config


# Este mixin prepara modelo, embeddings, agentes e estado inicial do servico.
class RAGServiceBootstrapMixin:
    # Esta etapa monta todo o estado base antes de qualquer pergunta ou carga de colecao.
    def __init__(self, collection_name=None, model_name: str | None = None):
        self.project_root = Path(__file__).resolve().parents[4]
        self.collections_root = self.project_root / "data" / "collections"
        self.runtime_config = get_runtime_config()
        ufc_api_key = os.getenv("UFC_API_KEY")
        if not ufc_api_key:
            raise RuntimeError(
                "Missing UFC_API_KEY. Create a `.env` in the project root based on `.env.example`."
            )

        self.api_key = ufc_api_key
        self.default_model_name = self.runtime_config.ufc_model_name
        embedding_model_name = self.runtime_config.embedding.model_name
        self.api_url = os.getenv("UFC_API_URL", DEFAULT_UFC_API_URL)
        self.embedding_model_name = embedding_model_name
        self.embedding_device = self._resolve_embedding_device(self.runtime_config.embedding.device)
        self.embedding_quantization = self.runtime_config.embedding.quantization
        self.embedding_batch_size = self.runtime_config.embedding.batch_size
        self.embedding_max_length = self.runtime_config.embedding.max_length
        embedding_model_kwargs, encode_kwargs = self._build_embedding_settings()
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_name,
            model_kwargs=embedding_model_kwargs,
            encode_kwargs=encode_kwargs,
        )
        self.embeddings._client.max_seq_length = self.embedding_max_length
        self.model_name = ""
        self.llm_client = None
        self.llm = None
        self.splitter_config = self.runtime_config.splitter
        self.retrieval_config = self.runtime_config.retrieval
        self.aggregation_config = self.runtime_config.aggregation
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.splitter_config.chunk_size,
            chunk_overlap=self.splitter_config.chunk_overlap,
            separators=list(self.splitter_config.separators),
        )

        self.vector_store = None
        self.retriever = None
        self.answer_chain = None
        self.small_talk_chain = None
        self.query_rewrite_chain = None
        self.rag_index_cache_root = self.project_root / "data" / "cache" / "rag_index"
        self.collection_name = None
        self.collection_names = []
        self.document_catalog = []
        self.document_registry = []
        self.spreadsheet_chunk_index = {}
        self.last_retrieval_focus = None
        self._retrieval_diagnostics_enabled = False
        self._retrieval_diagnostics_state = None
        self.agent_mode = self.runtime_config.rag.agent_mode
        self.strict_grounding = self.runtime_config.rag.strict_grounding
        self.min_evidence_score = self.runtime_config.rag.min_evidence_score

        self.crewai_available = False
        self.crewai_casual_agent = None
        self.crewai_retrieval_agent = None
        self.crewai_scope_agent = None
        self.crewai_document_selection_agent = None
        self.crewai_evidence_planning_agent = None
        self.crewai_llm = None

        self.set_model(model_name or self.default_model_name, rebuild_crewai_agents=False)
        self._initialize_crewai_agents()
        if collection_name:
            self.load_collection(collection_name)

    def _resolve_embedding_device(self, requested_device: str) -> str:
        if requested_device in {"cuda", "gpu"}:
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "embeddings.device=cuda was requested in config/config.toml, but this Python environment "
                    "does not have CUDA-enabled PyTorch. Install a CUDA build of torch or set embeddings.device=cpu."
                )
            return "cuda"

        if requested_device == "cpu":
            return "cpu"

        raise RuntimeError(
            f"Unsupported embeddings.device='{requested_device}'. Use 'cuda' or 'cpu'."
        )

    def _build_embedding_settings(self) -> tuple[dict, dict]:
        encode_kwargs = {"batch_size": self.embedding_batch_size}
        quantization = self.embedding_quantization

        if quantization == "none":
            return {"device": self.embedding_device}, encode_kwargs

        if quantization != "4bit":
            raise RuntimeError(
                f"Unsupported embeddings.quantization='{quantization}'. Use 'none' or '4bit'."
            )

        if self.embedding_device != "cuda":
            raise RuntimeError(
                "embeddings.quantization=4bit requires embeddings.device=cuda in config/config.toml."
            )

        if importlib.util.find_spec("bitsandbytes") is None:
            raise RuntimeError(
                "embeddings.quantization=4bit requires the `bitsandbytes` package. "
                "Run `uv sync` after updating dependencies."
            )

        return {
            "device": self.embedding_device,
            "model_kwargs": {
                "device_map": "auto",
                "torch_dtype": torch.float16,
                "quantization_config": BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                ),
            },
        }, encode_kwargs

    # Esta troca recria apenas as cadeias dependentes do modelo atual.
    def set_model(self, model_name: str, rebuild_crewai_agents: bool = True) -> None:
        normalized_model_name = (model_name or "").strip()
        if not normalized_model_name:
            raise RuntimeError("Missing UFC model name.")
        if normalized_model_name == self.model_name and self.answer_chain and self.small_talk_chain:
            return

        self.model_name = normalized_model_name
        self.llm_client = UFCOllamaClient(
            api_key=self.api_key,
            model_name=self.model_name,
            api_url=self.api_url,
        )
        self.llm = RunnableLambda(self.llm_client.invoke)
        self._build_prompt_chains()
        if rebuild_crewai_agents:
            self._initialize_crewai_agents()

    # Esta etapa ativa os agentes opcionais sem quebrar o fluxo se o CrewAI nao estiver disponivel.
    def _initialize_crewai_agents(self) -> None:
        self.crewai_llm = build_crewai_llm(
            api_key=self.api_key,
            model_name=self.default_model_name,
            api_url=self.api_url,
        )
        bundle = build_crewai_agent_bundle(self.agent_mode, llm=self.crewai_llm)
        self.crewai_available = bundle.available
        self.crewai_casual_agent = bundle.casual_agent
        self.crewai_retrieval_agent = bundle.retrieval_agent
        self.crewai_scope_agent = bundle.scope_agent
        self.crewai_document_selection_agent = bundle.document_selection_agent
        self.crewai_evidence_planning_agent = bundle.evidence_planning_agent
