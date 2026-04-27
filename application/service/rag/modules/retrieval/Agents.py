"""CrewAI invocation and answer-chain helpers."""
# Simple: Run specialized AI agents to improve search results

import contextlib
import io
import json


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
                "Regras: nao invente fatos sobre arquivos, apenas mantenha conversa social."
            ),
            expected_output="Resposta breve em portugues para conversa casual.",
        )
        if crewai_answer:
            return crewai_answer

        return self.small_talk_chain.invoke(
            {"collection_name": collection_name, "chat_history": history_text, "question": question}
        )

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
            self._update_retrieval_diagnostics_summary(
                prompt_text=prompt_text,
                raw_llm_response=raw_response,
            )
            return raw_response
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
