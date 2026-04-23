"""Numeric parsing helpers for spreadsheet markdown extraction."""
# Simple: Parse and format numbers from spreadsheets

from __future__ import annotations


def to_number(value: str) -> float | None:
    if not value:
        return None

    cleaned = value.strip().replace("R$", "").replace("%", "").replace("\u00a0", " ")
    cleaned = cleaned.replace(" ", "")
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return None


def format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"
