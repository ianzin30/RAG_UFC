"""Exhaustive, deterministic table arithmetic over indexed row records."""

from decimal import Decimal, InvalidOperation


def decimal_value(value):
    text = str(value).strip().replace("R$", "").replace("\u00a0", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
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
        else:
            result = max(values)
    return {
        "operation": operation.model_dump(),
        "result": str(result),
        "input_chunk_ids": [row.chunk_id for row in selected],
        "scanned_rows": len(rows),
        "matched_rows": len(selected),
    }
