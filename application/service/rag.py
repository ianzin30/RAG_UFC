import os
import re
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
        self.document_catalog = [
            self.query_planner.build_catalog_entry(
                document_id=document.document_id,
                display_name=document.display_name,
                document_type=document.document_type,
                summary=document.summary,
            )
            for document in normalized_collection.documents
        ]

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
        plan = self.query_planner.plan(question, resolved_question, self.document_catalog)

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

        self.answer_chain = answer_prompt | self.llm | StrOutputParser()
        self.small_talk_chain = small_talk_prompt | self.llm | StrOutputParser()
        self.query_rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()

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
            if entry["document_id"] in document_ids:
                names.append(entry["display_name"])
        return ", ".join(names) if names else "nenhum arquivo especifico"
