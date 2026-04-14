"""Public entrypoint for spreadsheet-to-markdown extraction."""

try:
    from .spreadsheet_markdown_support.loading import load_spreadsheet_sheets
    from .spreadsheet_markdown_support.rendering import render_sheet
except ImportError:
    from spreadsheet_markdown_support.loading import load_spreadsheet_sheets
    from spreadsheet_markdown_support.rendering import render_sheet


def extract_spreadsheet_markdown(file_bytes: bytes, suffix: str, file_name: str) -> str:
    sheets = load_spreadsheet_sheets(file_bytes, suffix)
    normalized_suffix = (suffix or "").lower()
    sheet_names = ", ".join(sheet.name for sheet in sheets) or "Sem abas detectadas"
    lines = [
        "Document type: spreadsheet",
        f"Spreadsheet format: {normalized_suffix.lstrip('.') or 'unknown'}",
        f"Spreadsheet file: {file_name}",
        f"Total sheets: {len(sheets)}",
        f"Sheet names: {sheet_names}",
        "",
    ]

    for sheet in sheets:
        lines.extend(render_sheet(sheet, file_name))

    return "\n".join(line for line in lines if line is not None).strip()
