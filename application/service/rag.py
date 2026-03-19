import os
import re
import json
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .collections.repository import CollectionRepository
from .retrieval.coordinator import RetrievalCoordinator
from .retrieval.query_planner import QueryPlanner


class RAGService:
    def __init__(self, collection_name=None):
        self.project_root = Path(__file__).resolve().parents[2]
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name="openai/gpt-oss-120b",
            temperature=0.2,
            reasoning_effort="medium",
            model_kwargs={"include_reasoning": False},
        )
        self.intent_decider_llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model_name=os.getenv("GROQ_INTENT_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ": ", "  ", " ", ""],
        )
        self.collection_repository = CollectionRepository(self.project_root)
        self.query_planner = QueryPlanner()
        self.retrieval_coordinator = RetrievalCoordinator(self.text_splitter)

        self.vector_store = None
        self.retriever = None
        self.answer_chain = None
        self.small_talk_chain = None
        self.query_rewrite_chain = None
        self.intent_decider_chain = None
        self.loaded_collection_id = None
        self.collection_name = None
        self.collection_manifest = None
        self.normalized_documents = []
        self.document_catalog = []
        self.spreadsheet_chunk_index = {}

        if collection_name:
            self.load_collection(collection_name)

    def load_collection(self, collection_name):
        normalized_collection = self.collection_repository.load_collection(collection_name)
        self.collection_manifest = normalized_collection.manifest
        self.normalized_documents = normalized_collection.documents
        self.document_catalog = self._build_document_catalog(normalized_collection.documents)

        (
            self.vector_store,
            self.retriever,
            self.spreadsheet_chunk_index,
        ) = self.retrieval_coordinator.build_indexes(
            normalized_collection.documents,
            self.document_catalog,
            self.embeddings,
        )

        self.loaded_collection_id = collection_name
        self.collection_name = collection_name
        self._build_chains()

    def ask_question(self, question: str, chat_history=None) -> str:
        if not self.retriever or not self.answer_chain or not self.small_talk_chain:
            raise Exception("No collection loaded. Please load a collection before asking questions.")

        history_text = self._format_chat_history(chat_history)
        collection_label = self.collection_name or self.loaded_collection_id or "colecao nao identificada"

        if self._is_casual_message(question):
            return self.small_talk_chain.invoke(
                {"collection_name": collection_label, "chat_history": history_text, "question": question}
            )

        resolved_question = self._rewrite_question_for_retrieval(question, history_text, chat_history)
        intent_decision = self._decide_query_intent(question, resolved_question, history_text)
        plan = self.query_planner.plan(
            question,
            resolved_question,
            self.document_catalog,
            intent_decision=intent_decision,
        )

        if plan.intent == "inventory":
            return self.query_planner.answer_inventory(plan, self.document_catalog)

        docs = self.retrieval_coordinator.retrieve(
            plan=plan,
            vector_store=self.vector_store,
            retriever=self.retriever,
            spreadsheet_chunk_index=self.spreadsheet_chunk_index,
            document_catalog=self.document_catalog,
        )
        context = self._format_docs(docs)
        return self.answer_chain.invoke(
            {
                "collection_name": collection_label,
                "chat_history": history_text,
                "resolved_question": plan.resolved_query,
                "target_document_names": self._format_target_document_names(plan.target_document_ids),
                "context": context,
                "question": question,
            }
        )

    def _build_chains(self):
        answer_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce e um assistente prestativo em uma aplicacao de chat com documentos. "
                "Sua base atual e a colecao selecionada pelo usuario. "
                "Responda em portugues, de forma natural, sem soar robotico. "
                "Nao mencione identificadores tecnicos, nomes internos de colecao, slugs ou IDs ao responder. "
                "Quando fizer referencia a base carregada, prefira expressoes naturais como 'os arquivos carregados', "
                "'os documentos enviados' ou o assunto identificado no contexto. "
                "Use o historico da conversa para entender mensagens curtas de continuacao. "
                "Quando a pergunta citar arquivos especificos, concentre a resposta neles e nao generalize para a colecao toda. "
                "Para perguntas sobre documentos, use apenas o contexto recuperado. "
                "Quando o contexto tiver entradas de pessoas ou registros de linha com nomes, liste os nomes diretamente. "
                "Quando houver um resumo de pessoas, use-o para entender a quantidade total de nomes disponiveis no arquivo. "
                "Nao diga que nao ha nomes explicitos se o contexto contiver campos como 'Pessoa:' ou linhas com nomes proprios. "
                "Em perguntas sobre trabalhadores, pessoas, equipe ou coordenadores, priorize nomes e funcoes antes de resumos genericos da planilha. "
                "Quando o usuario pedir nomes, liste os nomes exatos encontrados no contexto e nao os substitua por cargos ou resumos. "
                "Se o contexto for insuficiente, diga isso de forma natural e breve.",
            ),
            (
                "human",
                "Base carregada:\n{collection_name}\n\n"
                "Historico da conversa:\n{chat_history}\n\n"
                "Pergunta contextualizada para busca:\n{resolved_question}\n\n"
                "Arquivos-alvo identificados:\n{target_document_names}\n\n"
                "Contexto:\n{context}\n\n"
                "Pergunta original do usuario:\n{question}\n"
                "Resposta:"
            ),
        ])
        small_talk_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce e um assistente amigavel em uma aplicacao de chat com documentos. "
                "Sua base atual e a colecao selecionada pelo usuario. "
                "Responda em portugues, de forma breve e natural. "
                "Nao mencione identificadores tecnicos, nomes internos de colecao, slugs ou IDs ao responder. "
                "Quando fizer referencia a base carregada, prefira expressoes naturais como 'os arquivos carregados' ou 'os documentos enviados'. "
                "Fale com seguranca sobre a colecao carregada quando o assunto estiver claro. "
                "Evite expressoes hesitantes como 'parece ser' quando voce ja tiver contexto suficiente. "
                "Use o historico da conversa para entender respostas curtas como '??'. "
                "Se fizer sentido, mencione que voce pode responder perguntas sobre os documentos selecionados, mas sem forcar isso em toda resposta.",
            ),
            (
                "human",
                "Base carregada:\n{collection_name}\n\n"
                "Historico da conversa:\n{chat_history}\n\n"
                "Mensagem do usuario:\n{question}\n"
                "Resposta:"
            ),
        ])
        rewrite_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Reescreva a pergunta do usuario como uma consulta independente para recuperacao de documentos. "
                "Use o historico apenas para resolver referencias implicitas. "
                "Preserve nomes de arquivos, abas, pessoas, valores e termos importantes. "
                "Se a pergunta ja estiver clara sozinha, devolva a propria pergunta. "
                "Responda somente com a consulta reescrita.",
            ),
            (
                "human",
                "Historico da conversa:\n{chat_history}\n\n"
                "Pergunta atual:\n{question}\n\n"
                "Consulta reescrita:"
            ),
        ])
        intent_decider_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce e um classificador de intencao para uma aplicacao de chat com documentos. "
                "Sua tarefa e decidir se a pergunta atual deve ser tratada como uma consulta de inventario da colecao "
                "ou como uma pergunta geral sobre o conteudo dos documentos. "
                "Voce deve responder apenas com JSON valido, sem markdown, sem comentarios e sem texto extra. "
                'Use exatamente este schema: {{"intent": "inventory_query" | "general", "confidence": 0.0}}. '
                "A confidence deve ser um numero entre 0 e 1. "
                "Classifique como inventory_query apenas quando a pergunta pede informacoes sobre a colecao em si, "
                "como quantidade de arquivos, nomes dos arquivos, tipos de arquivos, quais planilhas, quais PDFs, "
                "se existe alguma imagem, o que foi carregado ou o que foi importado. "
                "Classifique como general quando a pergunta pede conteudo de algum documento, resumo, comparacao, "
                "informacoes de pessoas, assuntos, tabelas, valores, ou qualquer pergunta que dependa do conteudo dos arquivos. "
                "Se houver duvida relevante, prefira general com confidence menor. "
                "Nao classifique como inventory_query apenas porque a pergunta menciona a palavra documento ou arquivo; "
                "so use inventory_query se o foco for o inventario da colecao. "
                "Exemplos: "
                '{{"intent":"inventory_query","confidence":0.96}} para "quais arquivos foram carregados?"; '
                '{{"intent":"inventory_query","confidence":0.94}} para "quantos documentos voce leu?"; '
                '{{"intent":"general","confidence":0.92}} para "me fale sobre o arquivo planilha financeira"; '
                '{{"intent":"general","confidence":0.95}} para "compare AFO.pdf e AFO.xlsx".'
            ),
            (
                "human",
                "Historico da conversa:\n{chat_history}\n\n"
                "Pergunta original:\n{question}\n\n"
                "Pergunta reescrita:\n{resolved_question}\n\n"
                "JSON:"
            ),
        ])

        self.answer_chain = answer_prompt | self.llm | StrOutputParser()
        self.small_talk_chain = small_talk_prompt | self.llm | StrOutputParser()
        self.query_rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()
        self.intent_decider_chain = intent_decider_prompt | self.intent_decider_llm | StrOutputParser()

    def _build_document_catalog(self, documents) -> list[dict]:
        grouped_documents = {}
        for document in documents:
            logical_item_id = document.logical_item_id or document.document_id
            grouped_documents.setdefault(logical_item_id, []).append(document)

        catalog = []
        for logical_item_id, grouped in grouped_documents.items():
            visible_documents = [document for document in grouped if document.catalog_visibility != "internal"]
            if not visible_documents:
                continue
            primary_document = visible_documents[0]
            logical_item_name = primary_document.logical_item_name or primary_document.display_name
            logical_item_kind = primary_document.logical_item_kind or ("folder" if len(visible_documents) > 1 else "file")
            contained_types = sorted({document.document_type for document in grouped if document.document_type}) or ["document"]
            visible_types = sorted({document.document_type for document in visible_documents if document.document_type}) or contained_types
            document_type = visible_types[0] if len(visible_types) == 1 else "document"
            summary = self._build_catalog_summary(visible_documents, logical_item_name, logical_item_kind)
            child_documents = [document for document in grouped if document.catalog_visibility == "internal"]
            supports_doc_csv_hybrid = (
                primary_document.component_kind == "spreadsheet_parent"
                and any(document.component_kind == "csv_sheet_child" for document in child_documents)
            )
            catalog.append(
                self.query_planner.build_catalog_entry(
                    document_id=logical_item_id,
                    display_name=logical_item_name,
                    document_type=document_type,
                    summary=summary,
                    backing_document_ids=[document.document_id for document in grouped],
                    primary_document_id=primary_document.document_id,
                    child_document_ids=[document.document_id for document in child_documents],
                    supports_doc_csv_hybrid=supports_doc_csv_hybrid,
                    logical_item_kind=logical_item_kind,
                    member_count=len(visible_documents),
                    match_names=[document.display_name for document in grouped],
                    contained_document_types=contained_types,
                    child_components=[
                        {
                            "document_id": document.document_id,
                            "component_name": document.component_name,
                        }
                        for document in child_documents
                    ],
                )
            )
        return catalog

    def _build_catalog_summary(self, documents, logical_item_name: str, logical_item_kind: str) -> str:
        if logical_item_kind == "folder" and len(documents) > 1:
            return f"Pasta logica {logical_item_name} com {len(documents)} arquivos relevantes."
        return documents[0].summary if documents else ""

    def _format_chat_history(self, chat_history) -> str:
        if not chat_history:
            return "Sem conversa anterior."

        lines = []
        for message in chat_history:
            role = message.get("role") or "user"
            label = "Usuario" if role == "user" else "Assistente"
            content = (message.get("content") or "").strip()
            if not content:
                continue
            lines.append(f"{label}: {content}")
        return "\n".join(lines) if lines else "Sem conversa anterior."

    def _is_casual_message(self, question: str) -> bool:
        normalized = re.sub(r"\s+", " ", (question or "").strip().lower())
        if not normalized:
            return True
        greetings = {
            "oi",
            "ola",
            "olá",
            "bom dia",
            "boa tarde",
            "boa noite",
            "hello",
            "hi",
            "hey",
            "thanks",
            "obrigado",
            "valeu",
        }
        if normalized in greetings:
            return True
        return len(normalized.split()) <= 2 and normalized.endswith("?")

    def _should_rewrite_question(self, question: str, chat_history) -> bool:
        normalized = re.sub(r"\s+", " ", (question or "").strip().lower())
        if not normalized or not chat_history:
            return False

        follow_up_markers = {
            "e ",
            "e qual",
            "e quais",
            "e quem",
            "e quanto",
            "agora",
            "essa",
            "esse",
            "isso",
            "ela",
            "ele",
        }
        if any(normalized.startswith(marker) for marker in follow_up_markers):
            return True
        if any(marker in normalized for marker in follow_up_markers):
            return True
        return len(normalized.split()) <= 6

    def _rewrite_question_for_retrieval(self, question: str, history_text: str, chat_history) -> str:
        if not self.query_rewrite_chain or history_text == "Sem conversa anterior.":
            return question
        if not self._should_rewrite_question(question, chat_history):
            return question

        rewritten = self.query_rewrite_chain.invoke(
            {
                "chat_history": history_text,
                "question": question,
            }
        ).strip()
        rewritten = re.sub(r"^(consulta|pergunta reescrita|query)\s*:\s*", "", rewritten, flags=re.IGNORECASE).strip()
        return rewritten or question

    def _decide_query_intent(self, question: str, resolved_question: str, history_text: str) -> dict:
        if not self.intent_decider_chain:
            return {"intent": "general", "confidence": 0.0}

        raw_decision = self.intent_decider_chain.invoke(
            {
                "chat_history": history_text,
                "question": question,
                "resolved_question": resolved_question,
            }
        ).strip()
        return self._parse_intent_decision(raw_decision)

    def _parse_intent_decision(self, raw_decision: str) -> dict:
        candidate = (raw_decision or "").strip()
        if not candidate:
            return {"intent": "general", "confidence": 0.0}

        if "{" in candidate and "}" in candidate:
            candidate = candidate[candidate.find("{") : candidate.rfind("}") + 1]

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return {"intent": "general", "confidence": 0.0}

        intent = (parsed.get("intent") or "general").strip().lower()
        if intent not in {"inventory_query", "general"}:
            intent = "general"

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = 0.0
        confidence_value = max(0.0, min(1.0, confidence_value))

        return {"intent": intent, "confidence": confidence_value}

    def _format_docs(self, docs) -> str:
        if not docs:
            return "Nenhum trecho relevante foi recuperado."
        return "\n\n---\n\n".join(doc.page_content for doc in docs if doc.page_content)

    def _format_target_document_names(self, target_document_ids: list[str]) -> str:
        if not target_document_ids:
            return "nenhum arquivo especifico"
        names = []
        document_ids = set(target_document_ids)
        for entry in self.document_catalog:
            backing_ids = set(entry.get("backing_document_ids") or [entry["document_id"]])
            if backing_ids & document_ids:
                names.append(entry["display_name"])
        return ", ".join(names) if names else "nenhum arquivo especifico"
