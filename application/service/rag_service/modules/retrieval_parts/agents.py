"""CrewAI invocation and answer-chain helpers."""


# Este mixin concentra as chamadas aos agentes e ao chain final de resposta.
class RetrievalAgentMixin:
    # Este helper executa um agente isolado e desliga o modo CrewAI se a chamada falhar.
    def _kickoff_crewai_agent(self, agent, description: str, expected_output: str) -> str | None:
        if not self.crewai_available or agent is None:
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
            result = crew.kickoff()
            text = str(result).strip()
            return text or None
        except Exception:
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
        return self.answer_chain.invoke(
            {
                "collection_name": collection_name,
                "chat_history": history_text,
                "resolved_question": resolved_question,
                "matched_documents": matched_documents,
                "target_document_name": target_document_name or "nenhum arquivo especifico",
                "context": context,
                "question": question,
            }
        )
