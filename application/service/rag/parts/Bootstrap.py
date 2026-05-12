"""Bootstrap and model setup for the RAG service."""
# Simple: Start up search system and load language models

import importlib.util
import logging
import os
import platform
from pathlib import Path
from typing import Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnableLambda
from langchain_text_splitters import RecursiveCharacterTextSplitter
import torch
from transformers import BitsAndBytesConfig

from ...UfcOllama import DEFAULT_UFC_API_URL, UFCOllamaClient
from ..CrewAiAgents import build_crewai_agent_bundle
from ..CrewAiLlm import build_crewai_llm
from ...RuntimeConfig import get_runtime_config


logger = logging.getLogger(__name__)
CPU_INT8_INVALID_MARKER_FILE_NAME = ".invalid_cpu_int8"
_EMBEDDING_INSTANCE_CACHE: dict[tuple[Any, ...], HuggingFaceEmbeddings] = {}


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
        logger.info("Default UFC LLM model loaded from config: %s", self.default_model_name)
        embedding_model_name = self.runtime_config.embedding.model_name
        self.api_url = os.getenv("UFC_API_URL", DEFAULT_UFC_API_URL)
        self.embedding_model_name = embedding_model_name
        self.embedding_model_cache_root = self.project_root / "data" / "cache" / "embedding_models"
        self.embedding_device = self._resolve_embedding_device(self.runtime_config.embedding.device)
        self.embedding_quantization = self._resolve_embedding_quantization(
            self.runtime_config.embedding.quantization,
            self.embedding_device,
        )
        self.embedding_batch_size = self.runtime_config.embedding.batch_size
        self.embedding_max_length = self.runtime_config.embedding.max_length
        self.embeddings = self._build_huggingface_embeddings()
        self.model_name = ""
        self.llm_client = None
        self.llm = None
        self.splitter_config = self.runtime_config.splitter
        self.retrieval_config = self.runtime_config.retrieval
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
        self._response_status_callback = None
        self.agent_mode = self.runtime_config.rag.agent_mode
        self.strict_grounding = self.runtime_config.rag.strict_grounding
        self.min_evidence_score = self.runtime_config.rag.min_evidence_score
        self.generation_config = self.runtime_config.generation

        self.crewai_available = False
        self.crewai_router_agent = None
        self.crewai_casual_agent = None
        self.crewai_retrieval_agent = None
        self.crewai_scope_agent = None
        self.crewai_document_selection_agent = None
        self.crewai_evidence_planning_agent = None
        self.crewai_benchmark_grading_agent = None
        self.crewai_llm = None

        self.set_model(model_name or self.default_model_name, rebuild_crewai_agents=False)
        self._initialize_crewai_agents()
        if collection_name:
            self.load_collection(collection_name)

    def _resolve_embedding_device(self, requested_device: str) -> str:
        normalized_device = (requested_device or "cpu").strip().lower()
        if normalized_device == "gpu":
            normalized_device = "cuda"

        if normalized_device == "cuda":
            if torch.cuda.is_available():
                return "cuda"
            logger.warning(
                "embeddings.device=%s was requested in config/config.toml, but CUDA is unavailable. "
                "Falling back to CPU.",
                requested_device,
            )
            return "cpu"

        if normalized_device == "cpu":
            return "cpu"

        if normalized_device == "mps":
            mps_backend = getattr(torch.backends, "mps", None)
            if mps_backend is not None and mps_backend.is_available():
                return "mps"
            logger.warning(
                "embeddings.device=%s was requested in config/config.toml, but MPS is unavailable. "
                "Falling back to CPU.",
                requested_device,
            )
            return "cpu"

        raise RuntimeError(
            f"Unsupported embeddings.device='{requested_device}'. Use 'cuda', 'mps', or 'cpu'."
        )

    def _resolve_embedding_quantization(self, requested_quantization: str, device: str) -> str:
        normalized_quantization = (requested_quantization or "none").strip().lower()
        if normalized_quantization == "none":
            return "none"

        if normalized_quantization != "4bit":
            if normalized_quantization == "int8":
                if device != "cpu":
                    logger.warning(
                        "embeddings.quantization=int8 was requested in config/config.toml, but the effective "
                        "embedding device is %s. Falling back to embeddings.quantization=none.",
                        device,
                    )
                    return "none"
                return "int8"
            raise RuntimeError(
                f"Unsupported embeddings.quantization='{requested_quantization}'. Use 'none', '4bit', or 'int8'."
            )

        if device != "cuda":
            logger.warning(
                "embeddings.quantization=4bit was requested in config/config.toml, but the effective "
                "embedding device is %s. Falling back to embeddings.quantization=none.",
                device,
            )
            return "none"

        if importlib.util.find_spec("bitsandbytes") is None:
            logger.warning(
                "embeddings.quantization=4bit was requested in config/config.toml, but the "
                "`bitsandbytes` package is unavailable. Falling back to embeddings.quantization=none."
            )
            return "none"

        return "4bit"

    def _build_embedding_settings(self) -> tuple[str, dict, dict]:
        encode_kwargs = {"batch_size": self.embedding_batch_size}
        quantization = self.embedding_quantization

        if quantization == "none":
            return self.embedding_model_name, {"device": self.embedding_device}, encode_kwargs

        if quantization == "int8":
            try:
                model_path, quantized_file_name = self._ensure_cpu_int8_embedding_model()
            except Exception as exc:
                logger.warning(
                    "Failed to prepare CPU int8 embeddings for %s. Falling back to non-quantized embeddings: %s",
                    self.embedding_model_name,
                    exc,
                )
                self.embedding_quantization = "none"
                return self.embedding_model_name, {"device": self.embedding_device}, encode_kwargs
            return (
                str(model_path),
                {
                    "backend": "onnx",
                    "model_kwargs": {
                        "provider": "CPUExecutionProvider",
                        "file_name": quantized_file_name,
                    },
                },
                encode_kwargs,
            )

        return self.embedding_model_name, {
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

    def _build_huggingface_embeddings(self):
        embedding_model_reference, embedding_model_kwargs, encode_kwargs = self._build_embedding_settings()
        cache_key = self._build_embedding_instance_cache_key(
            embedding_model_reference,
            embedding_model_kwargs,
            encode_kwargs,
        )
        cached_embeddings = _EMBEDDING_INSTANCE_CACHE.get(cache_key)
        if cached_embeddings is not None:
            return cached_embeddings

        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model_reference,
                model_kwargs=embedding_model_kwargs,
                encode_kwargs=encode_kwargs,
            )
        except Exception as exc:
            if self.embedding_quantization == "none":
                raise
            failed_quantization = self.embedding_quantization
            logger.warning(
                "Failed to load %s embeddings with quantization=%s. "
                "Falling back to non-quantized embeddings: %s",
                self.embedding_model_name,
                failed_quantization,
                exc,
            )
            if failed_quantization == "int8":
                self._mark_cpu_int8_embedding_model_invalid(exc)
            self.embedding_quantization = "none"
            fallback_cache_key = self._build_embedding_instance_cache_key(
                self.embedding_model_name,
                {"device": self.embedding_device},
                encode_kwargs,
            )
            cached_embeddings = _EMBEDDING_INSTANCE_CACHE.get(fallback_cache_key)
            if cached_embeddings is not None:
                return cached_embeddings
            embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={"device": self.embedding_device},
                encode_kwargs=encode_kwargs,
            )
            cache_key = fallback_cache_key
        embeddings._client.max_seq_length = self.embedding_max_length
        _EMBEDDING_INSTANCE_CACHE[cache_key] = embeddings
        return embeddings

    def _build_embedding_instance_cache_key(
        self,
        model_name: str,
        model_kwargs: dict,
        encode_kwargs: dict,
    ) -> tuple[Any, ...]:
        return (
            HuggingFaceEmbeddings,
            str(model_name),
            repr(model_kwargs),
            repr(encode_kwargs),
            int(self.embedding_max_length),
        )

    def _ensure_cpu_int8_embedding_model(self) -> tuple[Path, str]:
        cpu_target = self._resolve_cpu_int8_quantization_target()
        model_dir = self._get_cpu_int8_embedding_model_dir(cpu_target)
        invalid_marker_path = self._get_cpu_int8_invalid_marker_path(cpu_target)
        if invalid_marker_path.exists():
            raise RuntimeError(
                "CPU int8 embedding cache was disabled after a previous ONNX load failure. "
                f"Remove {invalid_marker_path} and the onnx-int8 cache directory to retry."
            )

        try:
            from sentence_transformers import SentenceTransformer
            from sentence_transformers.backend import export_dynamic_quantized_onnx_model
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                "embeddings.quantization=int8 requires Sentence Transformers ONNX support. "
                "Run `uv sync` to install the project dependencies."
            ) from exc

        quantized_file_name = f"onnx/model_qint8_{cpu_target}.onnx"
        quantized_file_path = model_dir / quantized_file_name
        if quantized_file_path.exists():
            self._patch_onnx_output_names(quantized_file_path)
            return model_dir, quantized_file_name

        model_dir.mkdir(parents=True, exist_ok=True)
        logger.warning(
            "Exporting a CPU int8 ONNX embedding model for %s (%s). This can take a while on the first run.",
            self.embedding_model_name,
            cpu_target,
        )

        # HuggingFace Hub stores all files as symlinks to content-addressed blobs.
        # ONNX Runtime rejects symlinked external data files, so we copy the entire
        # snapshot to model_dir first, resolving every symlink to a real file.
        snapshot_path = Path(snapshot_download(self.embedding_model_name))
        self._copy_resolving_symlinks(snapshot_path, model_dir)

        model = SentenceTransformer(
            str(model_dir),
            backend="onnx",
            model_kwargs={
                "provider": "CPUExecutionProvider",
                "file_name": "onnx/model.onnx",
            },
        )
        export_dynamic_quantized_onnx_model(
            model=model,
            quantization_config=cpu_target,
            model_name_or_path=str(model_dir),
        )

        if not quantized_file_path.exists():
            raise RuntimeError(
                "Failed to export the CPU int8 ONNX embedding model. "
                "Check the previous logs for export or dependency errors."
            )
        self._patch_onnx_output_names(quantized_file_path)
        return model_dir, quantized_file_name

    @staticmethod
    def _patch_onnx_output_names(onnx_path: Path) -> None:
        """Rename token_embeddings → last_hidden_state in the ONNX graph.

        BAAI/bge-m3 exports token-level hidden states under the name
        'token_embeddings'. optimum's ORTModelForFeatureExtraction expects
        'last_hidden_state'. This rename makes the two compatible without
        changing any values — it is a no-op if the name is already correct.
        """
        import onnx

        model = onnx.load(str(onnx_path))
        needs_patch = any(o.name == "token_embeddings" for o in model.graph.output)
        needs_patch = needs_patch or any(
            "token_embeddings" in list(node.input) or "token_embeddings" in list(node.output)
            for node in model.graph.node
        )
        if not needs_patch:
            return
        for output in model.graph.output:
            if output.name == "token_embeddings":
                output.name = "last_hidden_state"
        for node in model.graph.node:
            node.input[:] = [
                "last_hidden_state" if name == "token_embeddings" else name
                for name in node.input
            ]
            node.output[:] = [
                "last_hidden_state" if name == "token_embeddings" else name
                for name in node.output
            ]
        onnx.save(model, str(onnx_path))

    @staticmethod
    def _copy_resolving_symlinks(src: Path, dst: Path) -> None:
        import shutil
        for item in src.rglob("*"):
            if item.is_dir():
                continue
            relative = item.relative_to(src)
            dst_file = dst / relative
            if dst_file.exists():
                continue
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item.resolve(), dst_file)

    def _resolve_cpu_int8_quantization_target(self) -> str:
        machine = platform.machine().strip().lower()
        if machine in {"arm64", "aarch64"}:
            return "arm64"
        if machine in {"x86_64", "amd64"}:
            return "avx2"
        raise RuntimeError(
            f"Unsupported CPU architecture '{machine}' for embeddings.quantization=int8. "
            "Supported targets are arm64 and x86_64/amd64."
        )

    def _get_cpu_int8_embedding_model_dir(self, cpu_target: str) -> Path:
        normalized_model_name = (
            str(self.embedding_model_name or "embedding-model")
            .strip()
            .replace("\\", "--")
            .replace("/", "--")
            .replace(":", "--")
        )
        return self.embedding_model_cache_root / normalized_model_name / f"onnx-int8-{cpu_target}"

    def _get_cpu_int8_invalid_marker_path(self, cpu_target: str) -> Path:
        return self._get_cpu_int8_embedding_model_dir(cpu_target) / CPU_INT8_INVALID_MARKER_FILE_NAME

    def _mark_cpu_int8_embedding_model_invalid(self, exc: Exception) -> None:
        try:
            cpu_target = self._resolve_cpu_int8_quantization_target()
            marker_path = self._get_cpu_int8_invalid_marker_path(cpu_target)
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_text(
                (
                    "CPU int8 ONNX embedding cache disabled after load failure.\n"
                    f"Model: {self.embedding_model_name}\n"
                    f"Error: {exc}\n"
                    "Delete this marker and the onnx-int8 cache directory to force a retry.\n"
                ),
                encoding="utf-8",
            )
        except Exception:
            logger.debug("Failed to write CPU int8 invalid-cache marker.", exc_info=True)

    def _build_ollama_generation_options(self) -> dict:
        """Translate the [generation] config into Ollama options.

        Sampling params live in `options`. We use temperature=0 by default for
        copy-fidelity on factual answers; downstream code can override per-call
        if needed (e.g. small_talk).
        """
        gen = self.generation_config
        options: dict = {
            "temperature": float(gen.temperature),
            "top_p": float(gen.top_p),
            "repeat_penalty": float(gen.repeat_penalty),
        }
        if gen.seed is not None:
            options["seed"] = int(gen.seed)
        if gen.num_ctx is not None:
            options["num_ctx"] = int(gen.num_ctx)
        return options

    # Esta troca recria apenas as cadeias dependentes do modelo atual.
    def set_model(self, model_name: str, rebuild_crewai_agents: bool = True) -> None:
        normalized_model_name = (model_name or "").strip()
        if not normalized_model_name:
            raise RuntimeError("Missing UFC model name.")
        if normalized_model_name == self.model_name and self.answer_chain and self.small_talk_chain:
            return

        self.model_name = normalized_model_name
        logger.info("Activating UFC LLM model for RAG service: %s", self.model_name)
        self.llm_client = UFCOllamaClient(
            api_key=self.api_key,
            model_name=self.model_name,
            api_url=self.api_url,
            generation_options=self._build_ollama_generation_options(),
        )
        self.llm = RunnableLambda(self.llm_client.invoke)
        self._build_prompt_chains()
        if rebuild_crewai_agents:
            self._initialize_crewai_agents()

    # Esta etapa ativa os agentes opcionais sem quebrar o fluxo se o CrewAI nao estiver disponivel.
    def _initialize_crewai_agents(self) -> None:
        active_model_name = self.model_name or self.default_model_name
        logger.info("Initializing CrewAI agents with model: %s", active_model_name)
        self.crewai_llm = build_crewai_llm(
            api_key=self.api_key,
            model_name=active_model_name,
            api_url=self.api_url,
        )
        bundle = build_crewai_agent_bundle(self.agent_mode, llm=self.crewai_llm)
        self.crewai_available = bundle.available
        self.crewai_router_agent = bundle.router_agent
        self.crewai_casual_agent = bundle.casual_agent
        self.crewai_retrieval_agent = bundle.retrieval_agent
        self.crewai_scope_agent = bundle.scope_agent
        self.crewai_document_selection_agent = bundle.document_selection_agent
        self.crewai_evidence_planning_agent = bundle.evidence_planning_agent
        self.crewai_benchmark_grading_agent = bundle.benchmark_grading_agent
