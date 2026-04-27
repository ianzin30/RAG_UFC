#!/usr/bin/env python3
"""Test script to validate response cleaning function."""

import re
import sys


def clean_retrieval_response(raw_response: str) -> str:
    """
    Remove conversation history markers and UI navigation text from LLM response.
    Extracts only the actual answer content.
    """
    if not raw_response or not isinstance(raw_response, str):
        return raw_response

    response = raw_response.strip()

    # Remove "**RETRIEVAL**" markers and surrounding asterisks/bold formatting
    response = re.sub(r'\*{2,}RETRIEVAL\*{2,}', '', response)
    response = re.sub(r'(?:^|\n)\*{2,}RETRIEVAL\*{2,}(?:\n|$)', '\n', response)

    # Remove lines containing conversation/mode indicators
    lines_to_remove = [
        r'.*Base carregada:.*',
        r'.*Historico da conversa:.*',
        r'.*Modo retrieval ativado.*',
        r'.*Para sair do modo de retrieval.*',
        r'.*Assistente:.*RETRIEVAL.*',
        r'.*Modo de retrieval.*',
        r'.*fim da conversa.*',
    ]

    for pattern in lines_to_remove:
        response = re.sub(pattern, '', response, flags=re.IGNORECASE | re.MULTILINE)

    # Remove excessive newlines
    response = re.sub(r'\n{3,}', '\n\n', response)

    # Clean up leading/trailing whitespace
    response = response.strip()

    return response


# Test cases with examples of contaminated responses
test_cases = [
    {
        "name": "Response with RETRIEVAL marker",
        "input": "**RETRIEVAL**\n\nA resposta é que sim, os pacientes podem se beneficiar.\n\nPara sair do modo de retrieval, use /exit",
        "expected_contains": ["resposta é que sim", "beneficiar"],
        "expected_not_contains": ["RETRIEVAL", "Para sair", "modo de retrieval"],
    },
    {
        "name": "Response with conversation history",
        "input": "Base carregada: covid_data.pdf\n\nHistorico da conversa: Usuario perguntou sobre sintomas\n\nAssistante: **RETRIEVAL**\n\nOs sintomas incluem febre, tosse e fadiga.",
        "expected_contains": ["sintomas incluem", "febre", "tosse", "fadiga"],
        "expected_not_contains": ["Base carregada", "Historico da conversa", "RETRIEVAL"],
    },
    {
        "name": "Clean response (no markers)",
        "input": "A COVID-19 é uma doença infecciosa causada pelo novo coronavírus.",
        "expected_contains": ["COVID-19", "doença infecciosa"],
        "expected_not_contains": [],
    },
    {
        "name": "Response with navigation text",
        "input": "Modo retrieval ativado\n\nA hipertensão pode levar a complicações cardíacas.\n\nPara sair do modo de retrieval, digite /exit",
        "expected_contains": ["hipertensão", "complicações cardíacas"],
        "expected_not_contains": ["Modo retrieval ativado", "Para sair", "digite /exit"],
    },
    {
        "name": "Response with excessive newlines",
        "input": "A resposta é:\n\n\n\n\n\nO diabetes é uma condição metabólica.\n\n\n\nFim da conversa",
        "expected_contains": ["diabetes", "condição metabólica"],
        "expected_not_contains": ["Fim da conversa"],
    },
]

def run_tests():
    """Run all test cases."""
    print("=" * 70)
    print("RESPONSE CLEANING VALIDATION TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_case in test_cases:
        print("\n[*] Test: {0}".format(test_case['name']))
        print("-" * 70)

        cleaned = clean_retrieval_response(test_case["input"])

        # Check expected content is present
        all_present = all(content in cleaned for content in test_case["expected_contains"])
        # Check unwanted content is removed
        all_removed = all(content not in cleaned for content in test_case["expected_not_contains"])

        if all_present and all_removed:
            print("[OK] PASSED")
            passed += 1
        else:
            print("[FAIL] FAILED")
            failed += 1

            if not all_present:
                missing = [c for c in test_case["expected_contains"] if c not in cleaned]
                print("   Missing expected content: {0}".format(missing))

            if not all_removed:
                not_removed = [c for c in test_case["expected_not_contains"] if c in cleaned]
                print("   Content not removed: {0}".format(not_removed))

        print(f"\n   INPUT ({len(test_case['input'])} chars):")
        print("   " + test_case["input"][:100].replace("\n", "\n   "))
        if len(test_case["input"]) > 100:
            print("   ...")

        print(f"\n   OUTPUT ({len(cleaned)} chars):")
        print("   " + cleaned[:100].replace("\n", "\n   "))
        if len(cleaned) > 100:
            print("   ...")

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
