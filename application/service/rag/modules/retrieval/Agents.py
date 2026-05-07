"""CrewAI invocation and answer-chain helpers."""
# Simple: Run specialized AI agents to improve search results

import contextlib
import io
import json
import re


# Este mixin concentra as chamadas aos agentes e ao chain final de resposta.
class RetrievalAgentMixin:
    # Este helper executa um agente isolado e desliga o modo CrewAI se a chamada falhar.
    def _kickoff_crewai_agent(
        self,
        agent,
        description: str,
        expected_output: str,
        *,
        disable_on_failure: bool = True,
        require_available: bool = True,
    ) -> str | None:
        if agent is None or (require_available and not self.crewai_available):
            return None

        try:
            from crewai import Crew, Process, Task

            task = Task(
                description=description,
                expected_output=expected_output,
                agent=agent,
            )
            crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            )
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = crew.kickoff()
            text = str(result).strip()
            return text or None
        except Exception:
            if disable_on_failure:
                self.crewai_available = False
            return None

    # Esta resposta tenta usar o agente casual antes de cair no prompt-chain tradicional.
    def _invoke_casual_agent(self, collection_name: str, history_text: str, question: str) -> str:
        crewai_answer = self._kickoff_crewai_agent(
            self.crewai_casual_agent,
            description=(
                "Responda de forma breve e amigavel em portugues.\n\n"
                f"Base carregada: {collection_name}\n"
                f"Historico: {history_text}\n"
                f"Mensagem do usuario: {question}\n"
                "Regras: nao invente fatos sobre arquivos, apenas mantenha conversa social. "
                "Nao encerre com frases genericas como 'estou a disposicao', "
                "'nao hesite em perguntar', 'se precisar de algo' ou similares. "
                "Nao use emojis a menos que o usuario use emojis primeiro."
            ),
            expected_output="Resposta breve em portugues para conversa casual, sem rodape de disponibilidade.",
        )
        if crewai_answer:
            return self._clean_casual_response(crewai_answer)

        casual_answer = self.small_talk_chain.invoke(
            {"collection_name": collection_name, "chat_history": history_text, "question": question}
        )
        return self._clean_casual_response(casual_answer)

    # Esta limpeza remove encerramentos genericos que modelos tendem a anexar em conversa casual.
    def _clean_casual_response(self, raw_response: str) -> str:
        if not raw_response or not isinstance(raw_response, str):
            return raw_response

        response = raw_response.strip()
        trailing_patterns = (
            r"(?:^|[\n.!?]\s*)se\s+houver\s+algo\b.*?(?:n[aã]o\s+hesite\s+em\s+perguntar|estou\s+(?:a|à)\s+disposi[cç][aã]o|possa\s+ser\s+[uú]til).*?$",
            r"(?:^|[\n.!?]\s*)se\s+precisar\s+de\s+(?:algo|mais\s+alguma\s+coisa|ajuda)\b.*?$",
            r"(?:^|[\n.!?]\s*)caso\s+precise\s+de\s+(?:algo|ajuda)\b.*?$",
            r"(?:^|[\n.!?]\s*)nao\s+hesite\s+em\s+(?:perguntar|me\s+chamar|pedir)\b.*?$",
            r"(?:^|[\n.!?]\s*)não\s+hesite\s+em\s+(?:perguntar|me\s+chamar|pedir)\b.*?$",
            r"(?:^|[\n.!?]\s*)estou\s+(?:a|à)\s+disposicao\b.*?$",
            r"(?:^|[\n.!?]\s*)estou\s+(?:a|à)\s+disposição\b.*?$",
            r"(?:^|[\n.!?]\s*)i(?:'| a)m\s+here\s+to\s+help\b.*?$",
            r"(?:^|[\n.!?]\s*)feel\s+free\s+to\s+ask\b.*?$",
            r"(?:^|[\n.!?]\s*)let\s+me\s+know\s+if\s+you\s+need\b.*?$",
            r"(?:^|\n)\s*(?:-)*\s*\n*\s*\(Note:.*?\)\s*$",
            r"(?:^|\n)\s*(?:-)*\s*\n*\s*Nota:.*?\s*$",
        )
        previous = None
        while previous != response:
            previous = response
            for pattern in trailing_patterns:
                response = re.sub(pattern, "", response, flags=re.IGNORECASE | re.DOTALL).strip()
            response = re.sub(r"[\s\U0001F300-\U0001FAFF\u2600-\u27BF]+$", "", response).strip()

        response = re.sub(r"\n{3,}", "\n\n", response).strip()
        return response or raw_response.strip()

    # Esta funcao limpa a resposta bruta do LLM removendo artefatos de conversa.
    def _clean_retrieval_response(self, raw_response: str) -> str:
        """
        Remove conversation history markers and UI navigation text from LLM response.
        Extracts only the actual answer content.
        """
        if not raw_response or not isinstance(raw_response, str):
            return raw_response

        response = raw_response.strip()

        # Remove "**RETRIEVAL**" markers and surrounding asterisks/bold formatting
        response = re.sub(r'\*{2,}RETRIEVAL\*{2,}', '', response)
        response = re.sub(r'(?:^|\n)\*{2,}RETRIEVAL\*{2,}(?:\n|$)', '\n', response)

        # Remove lines containing conversation/mode indicators
        lines_to_remove = [
            r'.*Base carregada:.*',
            r'.*Historico da conversa:.*',
            r'.*Modo retrieval ativado.*',
            r'.*Para sair do modo de retrieval.*',
            r'.*Assistente:.*RETRIEVAL.*',
            r'.*Modo de retrieval.*',
            r'.*fim da conversa.*',
        ]

        for pattern in lines_to_remove:
            response = re.sub(pattern, '', response, flags=re.IGNORECASE | re.MULTILINE)

        # Remove excessive newlines
        response = re.sub(r'\n{3,}', '\n\n', response)

        # Clean up leading/trailing whitespace
        response = response.strip()

        return response

    # Esta chamada monta o payload final que o chain de retrieval usa para responder.
    def _invoke_retrieval_agent(
        self,
        collection_name: str,
        history_text: str,
        resolved_question: str,
        matched_documents: str,
        target_document_name: str | None,
        context: str,
        question: str,
    ) -> str:
        input_dict = {
            "collection_name": collection_name,
            "chat_history": history_text,
            "resolved_question": resolved_question,
            "matched_documents": matched_documents,
            "target_document_name": target_document_name or "nenhum arquivo especifico",
            "context": context,
            "question": question,
        }
        prompt_template = getattr(self, "_answer_prompt_template", None)
        llm_client = getattr(self, "llm_client", None)
        if self._is_retrieval_diagnostics_enabled() and prompt_template is not None and llm_client is not None:
            prompt_value = prompt_template.invoke(input_dict)
            prompt_text = prompt_value.to_string()
            raw_response = llm_client.invoke(prompt_value)
            cleaned_response = self._clean_retrieval_response(raw_response)
            self._update_retrieval_diagnostics_summary(
                prompt_text=prompt_text,
                raw_llm_response=raw_response,
            )
            return cleaned_response
        return self.answer_chain.invoke(input_dict)

    def _invoke_benchmark_grading_agent(self, grading_payload: dict[str, object]) -> dict[str, object]:
        agent = getattr(self, "crewai_benchmark_grading_agent", None)
        if not self.crewai_available or agent is None:
            return {
                "status": "fallback",
                "reason": "benchmark_grading_agent_unavailable",
            }

        payload_json = json.dumps(grading_payload, ensure_ascii=False, indent=2)
        raw_output = self._kickoff_crewai_agent(
            agent,
            description=(
                "Avalie uma resposta de benchmark RAG usando a resposta esperada, "
                "a resposta gerada e o contexto selecionado.\n"
                "Use as metricas deterministicas apenas como diagnostico auxiliar.\n"
                "Retorne somente JSON valido.\n\n"
                f"Payload:\n{payload_json}\n\n"
                "Classificacoes permitidas:\n"
                '- correctness: "correct", "partially_correct", "incorrect" ou "abstained"\n'
                '- grounding_status: "grounded", "weakly_grounded" ou "unsupported"\n'
                '- failure_classification: "no_failure", "retrieval_failure", "selection_failure", '
                '"generation_failure", "document_resolution_failure" ou "benchmark_data_mismatch"\n'
                '- evidence_support: "direct", "partial" ou "none"\n'
                "- confidence: numero entre 0.0 e 1.0\n"
                "- rationale: explicacao curta\n"
            ),
            expected_output=(
                "JSON valido com correctness, grounding_status, failure_classification, "
                "evidence_support, confidence e rationale."
            ),
            disable_on_failure=False,
            require_available=False,
        )
        parser = getattr(self, "_parse_agent_payload", None)
        parsed = parser(raw_output) if callable(parser) else None
        if not isinstance(parsed, dict):
            return {
                "status": "fallback",
                "reason": "invalid_agent_json",
                "raw_response": raw_output,
            }

        return {
            "status": "graded",
            "raw_response": raw_output,
            "parsed": parsed,
        }
