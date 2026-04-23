"""Entity detection helpers for spreadsheet chunks."""
# Simple: Identify people names and information in spreadsheets

import re


class SpreadsheetEntityMixin:
    def _looks_like_person_name(self, value: str) -> bool:
        if not value:
            return False

        text = re.sub(r"\s+", " ", value).strip()
        if len(text) < 5 or any(char.isdigit() for char in text):
            return False
        if not any(char.islower() for char in text):
            return False

        normalized = self._normalize_identifier(text)
        if not normalized:
            return False
        blocked_exact = {
            "nome",
            "tbd",
            "total",
            "totais",
            "subtotal",
            "sub total",
            "target",
            "rpa",
            "profissionais",
            "bolsas",
            "custo total de rh mensal",
            "encargos clt",
            "descricao",
            "descricoes",
            "rh direto bolsas",
            "rh direto celetistas",
            "rh indireto administrativo",
        }
        blocked_prefixes = ("rh ", "sub total", "subtotal", "total ", "totais ", "custo ", "historico ", "margem ")
        if normalized in blocked_exact or any(normalized.startswith(prefix) for prefix in blocked_prefixes):
            return False

        tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
        return len(tokens) >= 2

    def _extract_role_from_pairs(self, pairs: list[tuple[str, str]]) -> str | None:
        for header, value in pairs:
            if self._looks_like_role(header, value):
                return value
        return None

    def _looks_like_role(self, header: str, value: str) -> bool:
        if not value:
            return False

        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return False
        if self._to_number(text) is not None:
            return False
        if re.search(r"\d{4}-\d{2}-\d{2}", text):
            return False

        normalized = self._normalize_identifier(text)
        if not normalized:
            return False
        if normalized in {"ufc", "s vinculo", "total", "totais", "custo dell"}:
            return False

        tokens = re.findall(r"[A-Za-zÀ-ÿ]+", text)
        if not tokens or len(tokens) > 12:
            return False

        normalized_header = self._normalize_identifier(header)
        if normalized_header.startswith("column_") and len(tokens) <= 1:
            return False
        return True

    def _to_number(self, value: str) -> float | None:
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
