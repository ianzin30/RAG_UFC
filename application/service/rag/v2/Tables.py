"""Exhaustive, deterministic table arithmetic over indexed row records."""

from decimal import Decimal, InvalidOperation
import re
import hashlib


def decimal_value(value, locale="pt_BR"):
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("Non-finite table value")
        return result
    text = str(value).strip().replace("R$", "").replace("\u00a0", "").replace(" ", "")
    if locale == "pt_BR":
        if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?", text):
            raise ValueError(f"Ambiguous/non-numeric pt_BR value: {value}")
        text = text.replace(".", "").replace(",", ".")
    elif locale != "en_US":
        raise ValueError("Unsupported numeric locale")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Non-numeric table value: {value}") from exc
    if not result.is_finite():
        raise ValueError("Non-finite table value")
    return result


def aggregate(chunks, scope, operation):
    allowed = None if scope is None else set(scope)
    rows = [
        chunk
        for chunk in chunks
        if chunk.chunk_kind == "row_record"
        and (allowed is None or chunk.document_id in allowed)
    ]
    selected = []
    for row in rows:
        values = row.metadata.get("row_values", {})
        if all(
            str(values.get(key, "")).casefold() == expected.casefold()
            for key, expected in operation.equals.items()
        ):
            selected.append(row)
    if not rows:
        raise ValueError("No structured table rows in requested scope")
    if operation.operation == "count":
        result = Decimal(len(selected))
    else:
        if not selected:
            raise ValueError("No matching rows for numeric aggregation")
        values = [
            decimal_value(row.metadata.get("row_values", {}).get(operation.column, ""))
            for row in selected
        ]
        if operation.operation == "sum":
            result = sum(values, Decimal(0))
        elif operation.operation == "mean":
            result = sum(values, Decimal(0)) / len(values)
        elif operation.operation == "min":
            result = min(values)
        elif operation.operation == "difference":
            if len(values) != 2:
                raise ValueError("Difference requires exactly two ordered operands")
            result = values[0] - values[1]
        else:
            result = max(values)
    return {
        "operation": operation.model_dump(),
        "result": str(result),
        "input_chunk_ids": [row.chunk_id for row in selected],
        "scanned_rows": len(rows),
        "matched_rows": len(selected),
    }


def textual_operands(evidence):
    """Regular Markdown cells only: retain literal offsets and row/header context.

    Irregular PDF text is not silently interpreted as a structured spreadsheet.
    A semantic role selects operand IDs; it cannot manufacture their values.
    """
    result = []
    money_documents = {e.document_id for e in evidence if "R$" in e.excerpt}
    for item in evidence:
        lines = list(re.finditer(r"[^\n]+", item.excerpt))
        headers = None
        for index, line in enumerate(lines):
            text = line.group()
            if not text.strip().startswith("|") or not text.strip().endswith("|"):
                headers = None
                continue
            cells = list(re.finditer(r"(?<=\|)[^|]*(?=\|)", text))
            values = [cell.group().strip() for cell in cells]
            if index + 1 < len(lines) and re.fullmatch(
                r"\s*\|(?:\s*:?-{2,}:?\s*\|)+\s*", lines[index + 1].group()
            ):
                headers = values
                continue
            if headers is None or len(values) != len(headers):
                continue
            if all(re.fullmatch(r":?-+:?", value) for value in values):
                continue
            for column, cell in enumerate(cells):
                literal = cell.group().strip()
                if not literal:
                    continue
                try:
                    number = decimal_value(literal)
                except ValueError:
                    continue
                start = (
                    line.start()
                    + cell.start()
                    + len(cell.group())
                    - len(cell.group().lstrip())
                )
                end = start + len(literal)
                row_label = values[0]
                if re.search(r"horas", row_label + " " + headers[column], re.I):
                    unit = "hour"
                elif re.search(r"pessoas", row_label + " " + headers[column], re.I):
                    unit = "person"
                elif "R$" in literal or "R$" in row_label or "R$" in headers[column]:
                    unit = "BRL"
                elif re.search(
                    r"gastos|valor|custo|sal[aá]rio|remunera|receita|despesa",
                    item.section_title + " " + headers[column],
                    re.I,
                ):
                    unit = (
                        "BRL"
                        if item.document_id in money_documents
                        else "monetary_unspecified"
                    )
                else:
                    unit = headers[column].strip()
                operand_id = (
                    "N"
                    + hashlib.sha256(
                        f"{item.evidence_id}:{start}:{end}".encode()
                    ).hexdigest()[:12]
                )
                result.append(
                    {
                        "operand_id": operand_id,
                        "literal": literal,
                        "value": str(number),
                        "unit": unit,
                        "locale": "pt_BR",
                        "document_id": item.document_id,
                        "evidence_id": item.evidence_id,
                        "start": start,
                        "end": end,
                        "header": headers[column],
                        "row": values,
                    }
                )
        # Explicit currency in narrative text is also a proposed operand,
        # anchored literally; never derive numbers from a paraphrase.
        for match in re.finditer(
            r"R\$\s*[+-]?\d+(?:\.\d{3})*(?:,\d{1,2})?(?!\d|[.,]\d)", item.excerpt
        ):
            if any(
                o["evidence_id"] == item.evidence_id
                and o["start"] <= match.start() < o["end"]
                for o in result
            ):
                continue
            literal = match.group()
            operand_id = (
                "N"
                + hashlib.sha256(
                    f"{item.evidence_id}:{match.start()}:{match.end()}".encode()
                ).hexdigest()[:12]
            )
            result.append(
                {
                    "operand_id": operand_id,
                    "literal": literal,
                    "value": str(decimal_value(literal)),
                    "unit": "BRL",
                    "locale": "pt_BR",
                    "document_id": item.document_id,
                    "evidence_id": item.evidence_id,
                    "start": match.start(),
                    "end": match.end(),
                    "header": "explicit_currency",
                    "row": [
                        item.excerpt[max(0, match.start() - 100) : match.end() + 100]
                    ],
                }
            )
    return result


def calculate(request, operands, evidence, requirement_ids):
    by_id = {o["operand_id"]: o for o in operands}
    by_evidence = {e.evidence_id: e for e in evidence}
    ids = request.operand_ids + (
        [request.printed_total_id] if request.printed_total_id else []
    )
    if not set(request.requirement_ids) <= set(requirement_ids) or not set(ids) <= set(
        by_id
    ):
        raise ValueError("Invalid calculation requirements/operands")
    if len(set(request.operand_ids)) != len(request.operand_ids):
        raise ValueError("Repeated numeric operand")
    selected = [by_id[i] for i in ids]
    if len({o["unit"] for o in selected}) != 1:
        raise ValueError("Incompatible operand units")
    if any(o["unit"] in {"", "monetary_unspecified"} for o in selected):
        raise ValueError("Operand unit not established by source")
    for operand in selected:
        item = by_evidence.get(operand["evidence_id"])
        if (
            item is None
            or item.excerpt[operand["start"] : operand["end"]] != operand["literal"]
        ):
            raise ValueError("Operand lost literal provenance")
    values = [Decimal(by_id[i]["value"]) for i in request.operand_ids]
    if request.operation == "difference":
        if len(values) != 2:
            raise ValueError("Difference requires two operands")
        value = values[0] - values[1]
    elif request.operation == "sum":
        value = sum(values, Decimal(0))
    elif request.operation == "mean":
        value = sum(values, Decimal(0)) / len(values)
    elif request.operation == "min":
        value = min(values)
    else:
        value = max(values)
    result = {
        **request.model_dump(),
        "result": str(value),
        "operands": selected,
        "unit": selected[0]["unit"],
        "evidence_ids": list(dict.fromkeys(o["evidence_id"] for o in selected)),
    }
    if request.printed_total_id:
        printed = Decimal(by_id[request.printed_total_id]["value"])
        result.update(printed_total=str(printed), difference=str(printed - value))
    return result


def calculation_matches_claim(claim, calculations, required=False):
    """A repair may omit a claim, never change its authoritative result."""
    if not claim.calculation_id:
        return not required and not any(
            set(c["requirement_ids"]) & set(claim.requirement_ids) for c in calculations
        )
    calculation = next(
        (c for c in calculations if c["calculation_id"] == claim.calculation_id), None
    )
    if calculation is None or claim.calculation_field not in calculation:
        return False
    if not set(claim.requirement_ids) <= set(calculation["requirement_ids"]):
        return False
    if not set(calculation["evidence_ids"]) <= set(claim.evidence_ids):
        return False
    num = r"\d+(?:[.,]\d+)*"
    for expression in re.finditer(
        rf"({num}(?:\s*[+-]\s*{num})+)\s*=\s*({num})", claim.text
    ):
        pieces = re.findall(rf"([+-]?)\s*({num})", expression[1])
        try:
            computed = sum(
                (
                    (-1 if sign == "-" else 1) * decimal_value(value)
                    for sign, value in pieces
                ),
                Decimal(0),
            )
            if computed != decimal_value(expression[2]):
                return False
        except ValueError:
            return False
    numbers = []
    for match in re.finditer(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?!\w)", claim.text):
        try:
            numbers.append(decimal_value(match.group()))
        except ValueError:
            pass
    return Decimal(calculation[claim.calculation_field]) in numbers


def requests_calculation(text):
    return bool(
        re.search(
            r"\b(soma|diferença|redução|média|calculad\w*|subtra\w*)\b", text, re.I
        )
    )
