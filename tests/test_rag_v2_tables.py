from application.service.rag.v2.Models import Chunk, TableOperation
from application.service.rag.v2.Tables import aggregate


def test_aggregation_scans_all_rows_and_uses_decimal_arithmetic():
    rows = [
        Chunk(
            chunk_id=str(i),
            document_id="d",
            document_name="D",
            parent_id=str(i),
            text="row",
            chunk_kind="row_record",
            metadata={"row_values": {"Item": "A", "Valor": value}},
        )
        for i, value in enumerate(["0,10", "0,20", "1000,00"])
    ]
    result = aggregate(
        rows,
        ["d"],
        TableOperation(operation="sum", column="Valor", equals={"Item": "A"}),
    )
    assert result["result"] == "1000.30"
    assert result["scanned_rows"] == 3
    assert result["input_chunk_ids"] == ["0", "1", "2"]


def test_aggregation_rejects_unknown_scope_and_non_numeric_values():
    import pytest

    row = Chunk(
        chunk_id="1",
        document_id="d",
        document_name="D",
        parent_id="p",
        text="x",
        chunk_kind="row_record",
        metadata={"row_values": {"Value": "unknown"}},
    )
    with pytest.raises(ValueError):
        aggregate([row], [], TableOperation(operation="count"))
    with pytest.raises(ValueError):
        aggregate([row], None, TableOperation(operation="sum", column="Value"))
