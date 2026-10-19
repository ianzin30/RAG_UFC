"""Source-backed document references and the shared question contract."""

import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from .Models import (
    QuestionContract,
    AnswerRequirement,
    RetrievalQuery,
    Scope,
    RequirementDocumentScope,
)


def normalized(text):
    return " ".join(
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode()
        .casefold()
        .split()
    )


MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "janeiro",
            "fevereiro",
            "marco",
            "abril",
            "maio",
            "junho",
            "julho",
            "agosto",
            "setembro",
            "outubro",
            "novembro",
            "dezembro",
        ),
        1,
    )
}


def explicit_entities(text):
    """Conservative named surface forms, not capitalization-as-entity.

    A generic label such as ``Edital`` is not an entity merely because it is
    capitalized. Document/date constraints have their own resolver. This is a
    lexical safeguard, not semantic entailment or a complete NER system.
    """
    grammatical = {
        "Quem",
        "Qual",
        "Quais",
        "Quando",
        "Como",
        "No",
        "Na",
        "Nos",
        "Nas",
        "Informe",
        "Segundo",
        "Compare",
        "De",
        "O",
        "A",
        "Os",
        "As",
        "Então",
    }
    proper = r"[A-ZÀ-Ý][a-zà-ÿ]+"
    patterns = (
        r"\b[A-Z]{2,}[A-Z0-9-]*\b",  # acronyms and codes
        rf"\b{proper}(?:[A-ZÀ-Ý][a-zà-ÿ]+)+\b",  # internal capitals
        rf"\b{proper}(?:(?:\s+(?:de|da|do|dos|das))?\s+{proper})+\b",
        rf"\b(?:via|tecnologia|ferramenta|sistema|projeto)\s+({proper})\b",
        r'["“]([^"”\n]{2,100})["”]',
    )
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = match.group(1) if match.lastindex else match.group()
            # Exclude question-leading grammar without stripping names.
            words = value.split()
            while words and words[0] in grammatical:
                words.pop(0)
            value = " ".join(words)
            if value:
                matches.append((match.start(), value))
    return list(dict.fromkeys(value for _, value in sorted(matches)))


def dates_in(text):
    found = set()
    for day, month, year in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text):
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            found.add(f"{int(day):02}/{int(month):02}/{year}")
    for day, month, year in re.findall(
        r"\b(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", normalized(text)
    ):
        if month in MONTHS:
            found.add(f"{int(day):02}/{MONTHS[month]:02}/{year}")
    return sorted(found)


class DocumentResolver:
    def __init__(self, catalog, chunks):
        grouped = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.document_id].append(chunk)
        self.records = []
        self.references = {}
        for index, entry in enumerate(catalog, 1):
            doc_id = entry["document_id"]
            reference = f"D{index}"
            self.references[reference] = doc_id
            items = grouped[doc_id]
            meeting_dates, dates_provenance = set(), []
            for chunk in items:
                # Only meeting headers, never electronic-signature timestamps.
                for match in re.finditer(
                    r"(?:realizad[ao]|reuni[aã]o)[^\n.]{0,230}",
                    chunk.section_title + "\n" + chunk.text[:400],
                    re.I,
                ):
                    dates = dates_in(match.group())
                    if dates:
                        meeting_dates.update(dates)
                        dates_provenance.append(
                            {
                                "chunk_id": chunk.chunk_id,
                                "quote": match.group(),
                                "dates": dates,
                            }
                        )
            stem = Path(entry.get("document_name", "")).stem
            aliases = (
                {normalized(stem)}
                if stem and normalized(stem) not in {"ata", "reuniao", "documento"}
                else set()
            )
            # Acronyms/names come from the actual document name, not a gold list.
            if aliases and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,24}", stem):
                aliases.add(normalized(stem))
            alias_provenance = []
            for chunk in items:
                if normalized(chunk.section_title) in {
                    "projeto",
                    "titulo do projeto",
                    "nome do projeto",
                }:
                    title = chunk.text.strip()
                    if normalized(title).startswith(
                        normalized(chunk.section_title) + " "
                    ):
                        title = title[len(chunk.section_title) :].strip()
                    if title and len(title) <= 200 and "\n\n" not in title:
                        aliases.add(normalized(title))
                        alias_provenance.append(
                            {"chunk_id": chunk.chunk_id, "quote": title}
                        )
            capabilities = {
                "structured_rows": any(c.chunk_kind == "row_record" for c in items),
                "markdown_tables": any(
                    "|" in c.text and re.search(r"\|\s*:?-{2,}", c.text) for c in items
                ),
            }
            self.records.append(
                {
                    **entry,
                    "ref": reference,
                    "aliases": sorted(aliases),
                    "alias_provenance": alias_provenance,
                    "meeting_dates": sorted(meeting_dates),
                    "date_provenance": dates_provenance,
                    "capabilities": capabilities,
                }
            )

    def prompt_catalog(self):
        return [
            {
                "document_id": r["ref"],
                "name": r.get("document_name", r["document_id"]),
                "project_aliases": [p["quote"] for p in r["alias_provenance"]],
                "meeting_dates": r["meeting_dates"],
                "capabilities": r["capabilities"],
            }
            for r in self.records
        ]

    def translate(self, ids):
        allowed = {r["document_id"] for r in self.records}
        result = [self.references.get(i, i) for i in ids]
        if not set(result) <= allowed:
            raise ValueError("Planner returned unknown document references")
        return list(dict.fromkeys(result))

    def resolve(self, question, history=()):
        contextual = bool(
            re.search(
                r"\b(dele|dela|desse|dessa|nesse|nessa|tamb[eé]m|ele|ela)\b|^e\s",
                question,
                re.I,
            )
        )
        users = [str(h.get("content", "")) for h in history if h.get("role") == "user"]
        text = " ".join(users[-1:] + [question]) if contextual else question
        norm = normalized(text)
        requested_dates = dates_in(text)
        matched, entities = [], []
        for record in self.records:
            alias_match = any(
                alias and re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", norm)
                for alias in record["aliases"]
            )
            month_match = re.search(r"\b(?:ata\s+)(\d{2})[-/](\d{4})\b", norm)
            month_hit = bool(
                month_match
                and re.search(
                    month_match[1] + r"[-_]" + month_match[2],
                    record.get("document_name", ""),
                )
            )
            date_hit = bool(set(requested_dates) & set(record["meeting_dates"]))
            if alias_match or date_hit or month_hit:
                matched.append(record["document_id"])
                if alias_match:
                    entities.append(record.get("document_name", ""))
        collections = {
            normalized(m[1])
            for m in re.finditer(r"\bcole[cç][aã]o\s+([\w-]+)", text, re.I)
        }
        if collections:
            matched = [
                d
                for d in matched
                if any(
                    r["document_id"] == d
                    and normalized(r.get("relative_path", "").split("/")[0])
                    in collections
                    for r in self.records
                )
            ]
        return {
            "ids": list(dict.fromkeys(matched)),
            "dates": requested_dates,
            "entities": list(dict.fromkeys(entities + explicit_entities(text))),
            "contextual": contextual,
            "resolution_text": text,
            "qualified_collections": sorted(collections),
        }

    def contract(self, question, history, plan):
        resolved = self.resolve(question, history)
        plan.scope.document_ids = self.translate(plan.scope.document_ids)
        for query in plan.queries:
            query.document_ids = self.translate(query.document_ids)
        facts = plan.requested_facts or plan.expected_evidence or [question]
        facts = list(dict.fromkeys(f.strip() for f in facts if f.strip())) or [question]
        mandatory = resolved["ids"]
        names = {
            normalized(r.get("document_name", ""))
            for r in self.records
            if r["document_id"] in mandatory
        }
        if (
            len(mandatory) > 1
            and len(names) == 1
            and len(resolved["qualified_collections"]) < len(mandatory)
        ):
            plan.scope = Scope(kind="ambiguous_document", document_ids=mandatory)
            plan.clarification = (
                "Qual coleção contém o documento que você deseja consultar?"
            )
            mandatory = []
        users = [str(h.get("content", "")) for h in history if h.get("role") == "user"]
        unchanged = normalized(plan.resolved_question) == normalized(question)
        if resolved["contextual"] and unchanged and len(mandatory) == 1 and users:
            # A unique source-bound conversational reference is retained
            # explicitly, rather than guessed away by a model rewrite.
            plan.resolved_question = (
                "Referência da conversa: " + users[-1] + "\nPergunta: " + question
            )
            unchanged = False
        internal_reference = not users and len(facts) > 1 and bool(mandatory)
        unresolved = resolved["contextual"] and unchanged and not internal_reference
        # A date attached to the second temporal leg is not an instruction
        # to discover the earlier fact in that same document. Explicit
        # 'only this document' restrictions always remain exclusive.
        years = set(re.findall(r"\b20\d{2}\b", resolved["resolution_text"]))
        exclusive = not (
            len(facts) > 1 and len(resolved["dates"]) == 1 and len(years) > 1
        )
        if re.search(r"\b(somente|exclusivamente|apenas)\b", normalized(question)):
            exclusive = True
        requirement_scopes = []
        for i, fact in enumerate(facts, 1):
            selected = (
                mandatory
                if exclusive
                else [d for d in self.resolve(fact)["ids"] if d in mandatory]
            )
            requirement_scopes.append(
                RequirementDocumentScope(
                    requirement_id=f"R{i}",
                    document_ids=selected,
                    origin="source_resolved" if selected else "collection_discovery",
                )
            )
        if mandatory:
            plan.scope = Scope(
                kind=(
                    "explicit_single_document"
                    if len(mandatory) == 1
                    else "explicit_multi_document"
                ),
                document_ids=mandatory,
            )
            if not exclusive:
                plan.scope = Scope()
        elif plan.scope.kind != "ambiguous_document":
            # Inferred candidates cannot permanently exclude undiscovered answers.
            candidates = list(plan.scope.document_ids)
            plan.scope = Scope()
            return QuestionContract(
                original_question=question,
                resolved_question=plan.resolved_question,
                requirements=[
                    AnswerRequirement(requirement_id=f"R{i}", text=f)
                    for i, f in enumerate(facts, 1)
                ],
                candidate_document_ids=candidates,
                requirement_scopes=requirement_scopes,
                explicit_dates=resolved["dates"],
                explicit_entities=resolved["entities"],
                contextual_reference=(
                    resolved["resolution_text"] if resolved["contextual"] else ""
                ),
                unresolved_reference=unresolved,
            )
        return QuestionContract(
            original_question=question,
            resolved_question=plan.resolved_question,
            requirements=[
                AnswerRequirement(requirement_id=f"R{i}", text=f)
                for i, f in enumerate(facts, 1)
            ],
            mandatory_document_ids=mandatory,
            scope_is_exclusive=exclusive,
            requirement_scopes=requirement_scopes,
            candidate_document_ids=list(plan.scope.document_ids),
            explicit_entities=resolved["entities"],
            explicit_dates=resolved["dates"],
            scope_origin=(
                (
                    "source_resolved"
                    if exclusive
                    else "requirement_scoped_temporal_discovery"
                )
                if mandatory
                else "ambiguous_document"
            ),
            contextual_reference=(
                resolved["resolution_text"] if resolved["contextual"] else ""
            ),
            unresolved_reference=unresolved,
        )

    def searches(self, plan, contract):
        queries = plan.queries or [
            RetrievalQuery(text=q)
            for q in list(
                dict.fromkeys([contract.resolved_question] + plan.initial_queries)
            )
        ]
        for query in queries:
            # Initial planner queries precede the controller-created contract.
            # Unbound/foreign labels cannot refer to those requirements yet.
            # Keep valid bindings; otherwise conservatively bind all requirements.
            # Later reasoning searches remain subject to Flow's strict ID guard.
            canonical = [r.requirement_id for r in contract.requirements]
            if not query.requirement_ids or not set(query.requirement_ids) <= set(canonical):
                query.requirement_ids = canonical
            if contract.mandatory_document_ids and contract.scope_is_exclusive:
                refs = self.resolve(query.text)["ids"]
                selected = [
                    i
                    for i in (query.document_ids or refs)
                    if i in contract.mandatory_document_ids
                ]
                query.document_ids = selected or contract.mandatory_document_ids
            elif contract.mandatory_document_ids:
                constraint_map = {
                    r.requirement_id: r.document_ids
                    for r in contract.requirement_scopes
                }
                constrained = [
                    constraint_map.get(rid, []) for rid in query.requirement_ids
                ]
                refs = self.resolve(query.text)["ids"]
                query.document_ids = (
                    list(dict.fromkeys(d for group in constrained for d in group))
                    if constrained and all(constrained)
                    else [d for d in refs if d in contract.mandatory_document_ids]
                )
            else:
                query.document_ids = []
        return queries
