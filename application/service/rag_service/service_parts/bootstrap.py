"""Bootstrap and model setup for the RAG service."""

import os
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...ufc_ollama import DEFAULT_UFC_API_URL, UFCOllamaClient
from ..constants import MODE_CASUAL, MODE_RETRIEVAL, parse_bool
from ..crewai_agents import build_crewai_agent_bundle


# Este mixin prepara modelo, embeddings, agentes e estado inicial do servico.
class RAGServiceBootstrapMixin:
    # Esta etapa monta todo o estado base antes de qualquer pergunta ou carga de colecao.
    def __init__(self, collection_name=None, model_name: str | None = None):
        self.project_root = Path(__file__).resolve().parents[4]
        self.collections_root = self.project_root / "data" / "collections"
        ufc_api_key = os.getenv("UFC_API_KEY")
        if not ufc_api_key:
            raise RuntimeError(
                "Missing UFC_API_KEY. Create a `.env` in the project root based on `.env.example`."
            )

        self.api_key = ufc_api_key
        default_model_name = os.getenv("UFC_MODEL_NAME")
        if not default_model_name:
            raise RuntimeError("Missing UFC_MODEL_NAME in `.env`.")

        embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")
        if not embedding_model_name:
            raise RuntimeError("Missing EMBEDDING_MODEL_NAME in `.env`.")

        self.api_url = os.getenv("UFC_API_URL", DEFAULT_UFC_API_URL)
        self.embedding_model_name = embedding_model_name
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
        self.model_name = ""
        self.llm_client = None
        self.llm = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", "  ", " ", ""],
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
        self.agent_mode = (os.getenv("RAG_AGENT_MODE", "crewai") or "crewai").strip().lower()
        self.strict_grounding = parse_bool(os.getenv("RAG_STRICT_GROUNDING"), default=True)
        min_score_raw = os.getenv("RAG_MIN_EVIDENCE_SCORE", "0.22")
        try:
            self.min_evidence_score = max(0.0, float(min_score_raw))
        except ValueError:
            self.min_evidence_score = 0.22

        self.crewai_available = False
        self.crewai_casual_agent = None
        self.crewai_retrieval_agent = None
        self.crewai_scope_agent = None
        self.crewai_document_selection_agent = None
        self.crewai_evidence_planning_agent = None
        self._initialize_crewai_agents()

        self.set_model(model_name or default_model_name)
        if collection_name:
            self.load_collection(collection_name)

    # Esta troca recria apenas as cadeias dependentes do modelo atual.
    def set_model(self, model_name: str) -> None:
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

    # Esta etapa ativa os agentes opcionais sem quebrar o fluxo se o CrewAI nao estiver disponivel.
    def _initialize_crewai_agents(self) -> None:
        bundle = build_crewai_agent_bundle(self.agent_mode)
        self.crewai_available = bundle.available
        self.crewai_casual_agent = bundle.casual_agent
        self.crewai_retrieval_agent = bundle.retrieval_agent
        self.crewai_scope_agent = bundle.scope_agent
        self.crewai_document_selection_agent = bundle.document_selection_agent
        self.crewai_evidence_planning_agent = bundle.evidence_planning_agent
