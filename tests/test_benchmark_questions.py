from pathlib import Path

import pytest

from benchmark.questions import load_questions


def test_load_questions_accepts_optional_fields(tmp_path: Path) -> None:
    questions_path = tmp_path / "questions.json"
    questions_path.write_text(
        """
        [
          {
            "id": 1,
            "collection": "google_drive_rag",
            "question": "Quem coordena o projeto?",
            "expected_answer": "Paulo Rego",
            "accepted_answers": ["Paulo Antonio Leal Rego"],
            "category": "projects",
            "source_document": "RACK.pdf",
            "metadata": {"source": "manual"},
            "custom_flag": true
          }
        ]
        """,
        encoding="utf-8",
    )

    questions = load_questions(questions_path)

    assert len(questions) == 1
    assert questions[0].collection == "google_drive_rag"
    assert questions[0].accepted_answers == ("Paulo Antonio Leal Rego",)
    assert questions[0].metadata == {"source": "manual"}
    assert questions[0].extras == {"custom_flag": True}


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        (
            """
            [
              {
                "id": 1,
                "question": "Pergunta sem colecao",
                "expected_answer": "Dell"
              }
            ]
            """,
            "collection",
        ),
        (
            """
            [
              {
                "id": 1,
                "collection": "google_drive_rag",
                "question": "Pergunta sem resposta esperada"
              }
            ]
            """,
            "expected_answer",
        ),
        (
            """
            [
              {
                "id": 1,
                "collection": "google_drive_rag",
                "question": "Primeira",
                "expected_answer": "Dell"
              },
              {
                "id": 1,
                "collection": "google_drive_rag",
                "question": "Segunda",
                "expected_answer": "UFC"
              }
            ]
            """,
            "Duplicate benchmark question id",
        ),
    ],
)
def test_load_questions_rejects_invalid_entries(
    tmp_path: Path,
    payload: str,
    expected_message: str,
) -> None:
    questions_path = tmp_path / "questions.json"
    questions_path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match=expected_message):
        load_questions(questions_path)


def test_benchmark_fixture_has_source_documents_for_source_scoped_edge_cases() -> None:
    questions = {question.normalized_id: question for question in load_questions(Path("benchmark/questions.json"))}

    assert questions["16"].source_document == "29_04-2025_Ata_de_Reuniao.md"
    assert questions["20"].source_document == "24_09-2025_Ata_de_Reuniao.pdf_Extraordina_ria.md"
    assert "regime de 40 horas" in questions["20"].question

