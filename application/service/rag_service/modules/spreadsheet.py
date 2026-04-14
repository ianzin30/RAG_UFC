"""Composable spreadsheet chunking mixins."""

from .spreadsheet_parts.chunks import SpreadsheetChunkBuilderMixin
from .spreadsheet_parts.entities import SpreadsheetEntityMixin
from .spreadsheet_parts.parsing import SpreadsheetParsingMixin


class SpreadsheetMixin(
    SpreadsheetEntityMixin,
    SpreadsheetParsingMixin,
    SpreadsheetChunkBuilderMixin,
):
    pass
