"""CrewAI agent builders for the RAG service."""

from __future__ import annotations

from dataclasses import dataclass


# Este bundle reune todos os agentes opcionais usados pelo fluxo de retrieval.
@dataclass
class CrewAIAgentBundle:
    available: bool = False
    casual_agent: object | None = None
    retrieval_agent: object | None = None
    scope_agent: object | None = None
    document_selection_agent: object | None = None
    evidence_planning_agent: object | None = None


# Esta fabrica liga ou desliga o conjunto de agentes de acordo com o modo atual.
def build_crewai_agent_bundle(agent_mode: str) -> CrewAIAgentBundle:
    bundle = CrewAIAgentBundle()
    if agent_mode != "crewai":
        return bundle

    try:
        from crewai import Agent
    except Exception:
        return bundle

    try:
        # Este agente cuida da conversa casual sem inventar fatos sobre arquivos.
        bundle.casual_agent = Agent(
            role="CasualAgent",
            goal="Responder cumprimentos e mensagens sociais de forma breve e natural, sem inventar fatos sobre documentos.",
            backstory="Especialista em conversas de abertura e mensagens sociais.",
            allow_delegation=False,
            verbose=False,
        )
        # Este agente decide se a pergunta continua no mesmo documento ou muda de escopo.
        bundle.scope_agent = Agent(
            role="ScopeAgent",
            goal="Determinar se a pergunta continua no documento atual, muda de documento ou pede resposta de escopo mais amplo.",
            backstory="Especialista em continuidade conversacional e mudanca de escopo em chats documentais.",
            allow_delegation=False,
            verbose=False,
        )
        # Este agente escolhe o melhor documento quando ha varios candidatos plausiveis.
        bundle.document_selection_agent = Agent(
            role="DocumentSelectionAgent",
            goal="Selecionar o melhor documento-alvo a partir de candidatos estruturados, evitando generalizacoes e chutes.",
            backstory="Especialista em ranking e desambiguacao de documentos com base em metadados e historico.",
            allow_delegation=False,
            verbose=False,
        )
        # Este agente classifica a intencao da pergunta antes da recuperacao de evidencias.
        bundle.evidence_planning_agent = Agent(
            role="EvidencePlanningAgent",
            goal="Classificar a intencao de retrieval da pergunta para orientar a recuperacao de evidencias.",
            backstory="Especialista em planejamento de retrieval e definicao de intencao de perguntas documentais.",
            allow_delegation=False,
            verbose=False,
        )
        bundle.available = True
        return bundle
    except Exception:
        return CrewAIAgentBundle()
