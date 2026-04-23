"""Composable spreadsheet chunking mixins."""
# Simple: Break down spreadsheets into searchable chunks

from .spreadsheet.Chunks import SpreadsheetChunkBuilderMixin
from .spreadsheet.Entities import SpreadsheetEntityMixin
from .spreadsheet.Parsing import SpreadsheetParsingMixin


class SpreadsheetMixin(
    SpreadsheetEntityMixin,
    SpreadsheetParsingMixin,
    SpreadsheetChunkBuilderMixin,
):
    pass
