"""Small planning helpers shared by the retrieval orchestration flow."""

import json
import re


# Este mixin concentra utilitarios pequenos usados pelo planejamento principal.
class RAGServicePlanningSupportMixin:
    # Este parser tenta recuperar JSON mesmo quando o agente devolve markdown ou cercas de codigo.
    def _parse_agent_payload(self, raw_text: str | None) -> dict[str, object] | None:
        text = str(raw_text or "").strip()
        if not text:
            return None

        candidates = [re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()]
        object_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if object_match:
            candidates.append(object_match.group(0).strip())

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        return None

    # Este helper chama um agente esperando resposta estruturada em JSON.
    def _invoke_json_crewai_agent(
        self,
        agent,
        description: str,
        expected_output: str,
    ) -> dict[str, object] | None:
        if not self.crewai_available or agent is None:
            return None

        raw_output = self._kickoff_crewai_agent(agent, description=description, expected_output=expected_output)
        return self._parse_agent_payload(raw_output)

    # Esta heuristica detecta quando a pergunta quer fugir do documento atual e olhar a colecao inteira.
    def _question_requests_collection_scope(self, question: str, resolved_question: str | None = None) -> bool:
        normalized = self._normalize_identifier(" ".join(part for part in [question, resolved_question or ""] if part))
        if not normalized:
            return False

        collection_markers = (
            "todos os documentos",
            "todos os arquivos",
            "arquivos carregados",
            "documentos carregados",
            "na colecao",
            "na colecao toda",
            "na base",
            "nessa base",
            "nos documentos",
            "nos arquivos",
        )
        return any(marker in normalized for marker in collection_markers)

    # Este payload reduz o catalogo de documentos a um formato simples para o agente de selecao.
    def _build_candidate_documents_payload(self, candidate_names: list[str]) -> list[dict[str, object]]:
        payload = []
        for document_name in candidate_names:
            entry = self._get_document_entry(document_name)
            if entry is None:
                continue
            payload.append(
                {
                    "document_name": entry.get("name"),
                    "document_type": entry.get("document_type"),
                    "title": entry.get("title"),
                    "normalized_stem": entry.get("normalized_stem"),
                    "document_date": entry.get("document_date"),
                    "meeting_date": entry.get("meeting_date"),
                    "meeting_month": entry.get("meeting_month"),
                    "meeting_year": entry.get("meeting_year"),
                    "description_excerpt": entry.get("description_excerpt"),
                    "keyword_summary": entry.get("keyword_summary"),
                    "aliases": [alias.get("display") for alias in list(entry.get("aliases") or [])[:6]],
                }
            )
        return payload

    # Esta checagem evita responder no chute quando a referencia interna continua ambigua.
    def _should_request_retrieval_clarification(
        self,
        question: str,
        target_document_name: str | None,
        retrieval_intent: str,
        docs,
    ) -> list[dict[str, str]]:
        if not target_document_name or retrieval_intent not in {"entity_lookup", "list_extraction"}:
            return []

        normalized = self._normalize_identifier(question)
        referential_markers = (
            " dele",
            " dela",
            " disso",
            " disto",
            " dessa",
            " desse",
            " dessa",
            " dessa reuniao",
            " dessa ata",
            " dessa parte",
            " dessa secao",
            " dessa seção",
            " sobre ela",
            " sobre ele",
        )
        if not any(marker.strip() in normalized for marker in referential_markers) and len(normalized.split()) > 6:
            return []
        return self._build_clarification_options(question, docs)
