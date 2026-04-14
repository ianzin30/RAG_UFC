"""Composable document resolution mixins."""

from .document_resolution_parts.aliases import DocumentAliasMixin
from .document_resolution_parts.matching import DocumentMatchingMixin
from .document_resolution_parts.registry import DocumentRegistryMixin


class DocumentResolutionMixin(
    DocumentRegistryMixin,
    DocumentAliasMixin,
    DocumentMatchingMixin,
):
    pass
