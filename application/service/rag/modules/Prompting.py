"""System and answer prompt templates for the RAG LLM.

Builds LangChain ChatPromptTemplate instances with instructions for:
- Copy-fidelity: exact copying of names, dates, numbers from context
- Grounding: using only provided context (no external knowledge)
- Format: Portuguese, max 2 sentences, no saudações or disclaimers
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


class PromptingMixin:
    """Build answer and small-talk prompt chains."""

    def _build_prompt_chains(self) -> None:
        answer_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce responde perguntas sobre uma colecao de documentos a partir de trechos recuperados. "
                "Evite mencionar o nome exato dos arquivos (como '07_05_ata.pdf'). Se necessario referenciar o documento, faca-o pelo titulo ou assunto. "
            ),
            (
                "human",
                "Base carregada:\n{collection_name}\n\n"
                "Historico da conversa:\n{chat_history}\n\n"
                "Pergunta contextualizada:\n{resolved_question}\n\n"
                "Documentos identificados:\n{matched_documents}\n\n"
                "Arquivo-alvo:\n{target_document_name}\n\n"
                "CONTEXTO:\n{context}\n\n"
                "Pergunta original:\n{question}\n\n"
                "Resposta:"
            ),
        ])
        small_talk_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Voce e um assistente amigavel em uma aplicacao de chat com documentos. "
                "Responda em portugues, de forma breve, direta e natural. "
                "Nao encerre com ofertas genericas de ajuda como 'estou a disposicao', "
                "'nao hesite em perguntar', 'se precisar de algo' ou frases semelhantes. "
                "Nao use emojis a menos que o usuario use emojis primeiro. "
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

        self._answer_prompt_template = answer_prompt
        self.answer_chain = answer_prompt | self.llm | StrOutputParser()
        self.small_talk_chain = small_talk_prompt | self.llm | StrOutputParser()
        self.query_rewrite_chain = rewrite_prompt | self.llm | StrOutputParser()
