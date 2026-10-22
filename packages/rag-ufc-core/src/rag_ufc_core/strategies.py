"""Status of the strategies implemented inside the core.

Being in this package does not make a strategy part of the application pipeline.
Only modules reachable from ``RAGEngine`` run in applications; the experimental
modules below are kept here because research protocols import them, and a test
guards that the production import graph never reaches them. Promoting one means
wiring it into ``Flow``/``Engine`` in a release whose pipeline was evaluated, not
moving files.
"""

STRATEGIES = {
    "rag_v2.agentic_flow": {
        "status": "baseline",
        "modules": ["Engine", "Flow", "Agents", "Planning", "Decision", "Retrieval", "Dense",
                    "Documents", "Coverage", "Grounding", "Focus", "Tables", "Providers"],
        "in_application_pipeline": True,
    },
    "rag_v2.adaptive_retrieval": {
        "status": "experimental",
        "modules": ["AdaptiveRetrieval"],
        "in_application_pipeline": False,
        "evaluated_by": "benchmark/search (single-shot vs adaptive rounds, agent interface, budgets)",
        "promotion_requires": "Wire into RAGFlow retrieval hops; pipeline-level evaluation against the baseline.",
    },
    "rag_v2.directed_retrieval": {
        "status": "experimental",
        "modules": ["DirectedRetrieval"],
        "in_application_pipeline": False,
        "evaluated_by": "benchmark/search (directed retrieval rounds, 2026-10-06)",
        "promotion_requires": "Wire into RAGFlow; pipeline-level evaluation against the baseline.",
    },
    "rag_v2.evidence_selection": {
        "status": "experimental",
        "modules": ["EvidenceSelection"],
        "in_application_pipeline": False,
        "evaluated_by": "benchmark/selection and Track B E08/E09 (offline replays)",
        "promotion_requires": "Replace Coverage batching in RAGFlow; answer-level evaluation, not only selection metrics.",
    },
    "rag_v2.semantic_retrieval": {
        "status": "experimental",
        "modules": ["SemanticRetrieval"],
        "in_application_pipeline": False,
        "evaluated_by": "benchmark (semantic generalization round, 2026-10-07)",
        "promotion_requires": "Wire into RAGFlow; pipeline-level evaluation against the baseline.",
    },
}


def experimental_modules() -> set[str]:
    return {
        module for strategy in STRATEGIES.values() if not strategy["in_application_pipeline"]
        for module in strategy["modules"]
    }
