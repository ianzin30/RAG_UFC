# Literature review and proposed agentic retrieval experiments

Reviewed: 2026-10-12. Research proposal only; no runtime, model, prompt or benchmark configuration changed.

The architectural hypothesis is credible, but the latest diagnostic does not establish that architecture is the dominant cause. It replayed initial planning observations for two questions, rather than executing and grading adaptive retrieval. Local Qwen 3.5 returned two validated legacy decisions and no validated compact decisions; Cumbuco returned three gateway timeouts. Protocol validity, documentary sufficiency and transport availability are different outcomes.

## Current implementation and adherence

Code inspected: `application/service/rag/v2/AdaptiveRetrieval.py`, `Providers.py`, and `benchmark/search/run.py`.

The adaptive controller already executes an observation–decision–search loop. It accumulates candidates, reranks against the original question, recomputes the final context, and returns the resulting observation to the planner. Its limits, explicit stopping reasons, retained context after failures and independent evaluator are useful foundations.

The current decision contract combines free-text needs, dependency IDs, support labels, copied quotations, documentary-scope justification, queries and stopping in one response. The observation combines the catalog permitted by scope, selected parents, optional retrieved children, previous searches and the ledger. The recent diagnostic used a schema in one user message without server-enforced decoding. This is an implementation choice, not an inherent requirement of agentic retrieval.

The model can request another search but cannot explicitly open an observed parent, inspect neighboring original text, or look up a phrase inside a chosen document. Candidate retention is already implemented; durable access to evidence for investigation is a separate question from the final 3,000-token context. The literal validator checks source correspondence, not semantic entailment. In the local H09 legacy decisions, the model represented the entire question as one need and declared sufficiency. That passed protocol checks; this diagnostic did not independently establish the complete relation chain.

These observations motivate experiments. They do not prove that a smaller action interface, more tools or a critic will improve retrieval.

## Literature and boundaries

| Work | Relevant contribution | Boundary for our project |
|---|---|---|
| [ReAct, Yao et al., ICLR 2023](https://arxiv.org/html/2210.03629) | Alternates reasoning, actions and observations; its Wikipedia environment exposes search, lookup and finish. Uses demonstrated trajectories. | Our controller follows the loop idea, not the original experimental protocol. Prompted smaller-model results and repetitive-action failures caution against assuming more steps automatically help. |
| [IRCoT, Trivedi et al., ACL 2023](https://aclanthology.org/2023.acl-long.557/) | Starts with retrieval, generates an incremental reasoning sentence, retrieves again using that sentence, and accumulates passages. Reports benefits with smaller models and transferred demonstrations. | Closely matches the retrieval-only objective, but its Wikipedia tasks, prompts, retrieval budgets and downstream reader differ from ours. |
| [Self-ask, Press et al., Findings of EMNLP 2023](https://arxiv.org/abs/2210.03350) | Explicit follow-up questions make compositional reasoning and search interaction easier to structure. | Follow-up answers must be grounded in our corpus; free-standing model guesses cannot become documentary facts. |
| [Grammar-Constrained Decoding, Geng et al., EMNLP 2023](https://aclanthology.org/2023.emnlp-main.674/) | Controls permissible output structures during decoding. | Structural compliance does not prove a query is useful, a citation supports a relationship, or an unfinished output can be accepted. |
| [Lost in the Middle, Liu et al., TACL](https://arxiv.org/abs/2307.03172) | Shows sensitivity to evidence position in long contexts. | Motivates observation-size and ordering controls; it does not diagnose our Qwen failures by itself. |
| [Sufficient Context, Joren et al., ICLR 2025](https://arxiv.org/abs/2411.06037) | Separates insufficient retrieved information from failure to use sufficient information. | The benchmark's frozen evidence requirements remain the independent quality check. A model's self-assessment is only an estimate. |
| [CRAG, Yan et al.](https://arxiv.org/abs/2401.15884) | Uses retrieval evaluation to trigger corrective actions. | A separate insufficiency check is an adaptation; we would not reproduce its web fallback or whole pipeline. |
| [Adaptive-RAG, Jeong et al., NAACL 2024](https://aclanthology.org/2024.naacl-long.389/) | A trained complexity classifier routes among different retrieval strategies. | Relevant to later cost control; our adaptive loop does not reproduce this classifier-based method. |
| [Self-RAG, Asai et al., ICLR 2024](https://arxiv.org/abs/2310.11511) | Trains retrieval and reflection behavior with specialized reflection tokens. | Adding a critique prompt to an untrained model would not reproduce this method. |
| [Search-R1, Jin et al., COLM 2025](https://arxiv.org/html/2503.09516v5) | Trains interaction with search through reinforcement learning, including smaller Qwen models. | Ordinary Qwen weights do not acquire that learned policy merely by receiving similar tags or instructions. Checkpoints require a separate integration and evaluation. |
| [Cherevichnik, master's thesis, LTU, 2025](https://ltu.diva-portal.org/smash/record.jsf?pid=diva2:2002498) | Evaluates retrieval variants on single- and multi-hop questions for a university assistant, separating retrieval and generation metrics. | Domain relevance, not proof that a particular agent architecture transfers. Repository abstract inspected; full-text fetch failed. |

Official implementation references: [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling) documents assistant/tool exchanges and an agent loop; [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) documents schema submission through `format`. Compatibility must be tested for the installed local runtime and the Cumbuco/Open WebUI route. Do not assume a schema included in prose activates constrained decoding.

## Proposed interventions, in priority order

1. **Reduce the action contract.** Separate choosing the next action from rebuilding the complete evidence assessment. Compare the current decision with a minimal search/finish contract on the same saved observations. Separately compare unconstrained and supported server-enforced output structures. Keep literals and source records in controller-owned storage. Measure format validity, reference validity, output exhaustion, time to executable action, and query usefulness separately.

2. **Expose search and reading as different actions.** Add bounded `read_parent` and document-local `lookup` actions alongside the unchanged hybrid search. Return short original excerpts with stable handles and provenance; retain full originals for reading. The agent chooses what to inspect. Search previews are navigational observations, not automatic proof. Cap and record reading actions independently of hybrid searches: equal search counts do not imply equal compute.

3. **Test a narrower incremental retrieval policy.** Compare one follow-up question at a time with the existing large decision contract, using grounded intermediate discoveries to generate the next query. Add generic synthetic demonstrations as a separate ablation, covering indirect references, conflicting entities, empty results and stopping. Do not use examples, fields, projects or answers taken from the 70 evaluated questions. A short factual progress note is enough; an extensive reasoning narrative is not an evaluation target.

4. **Separate evidence selection from quotation copying.** Provide stable source-span handles. When the model chooses a handle, the controller retrieves the exact original text; it does not fuzzy-match or repair invented quotations. This removes a mechanical copying burden. Test semantic support independently because an existing span can still identify the wrong person, role, document or period.

5. **Test a persistent evidence workspace.** Keep discovered source handles available for later reading even if global ranking removes their parents from the final context. Compare transient observations with retained access; do not assume ledger citations alone provide this capability. Investigative memory and final context have different purposes. Evaluate bridge-evidence retention under the unchanged final budget, including cases where whole parents cannot fit.

6. **Add a bounded sufficiency review.** On a proposed successful finish, check the original question against the actual final context, including indirect links and incompatible entities or periods. Permit a concise missing-information result to guide a remaining action. A second call to the same model is not automatically an independent or calibrated judge. Keep the documentary evaluator separate and audit false sufficiency and premature stopping.

Training search behavior or adopting a search-trained checkpoint is a later branch if the simpler interfaces are reliable but the policy remains weak. More agents, graph construction, unbounded loops and model replacement are not necessary to test these hypotheses.

## Controlled evaluation sequence

First isolate the execution contract locally on frozen observations. Evaluate thinking enabled versus disabled, where supported, as its own factor; do not change it simultaneously with the prompt and action interface. More output tokens allow more computation but guarantee neither an action nor better retrieval.

Then compare a working one-shot policy and adaptive policy using the same model, transport, action contract, original searches and final selector. Introduce reading tools, demonstrations, retained workspace and finish review in successive independent comparisons. Preserve original retrieval settings and final-answer blocking. Use all original 70 questions in both scopes for measured retrieval comparisons; no new evaluation datasets are proposed here.

Four search calls remains a useful search budget. Any new read actions, additional model decisions, validation calls and wall-time limits must be declared, bounded and charged separately. Keep controls for additional candidate volume or fixed extra searches so improvement is not attributed to adaptivity simply because it spent more compute.

Measure three levels: (1) operation: transport, schema, IDs, literal support and token limits; (2) investigation: grounded discoveries that changed later queries, novel useful evidence, repeated searches and premature stops; (3) outcome: frozen `evidence_v2` completeness and partial coverage, `literal_v1`, gains/regressions by category and shared fact, plus cost and latency. Review whether each proposed sufficient finish is actually sufficient under the independent annotations.

This preserves generic behavior: no benchmark IDs, categories, expected answers, project lists, fixed field templates or date heuristics in the agent. Testing on the same 70 questions can show robustness improvements there; it cannot establish transfer to an unseen domain. Adoption remains pending user review.
