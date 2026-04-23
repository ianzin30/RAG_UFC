"""Composable document resolution mixins."""
# Simple: Match documents to user questions

from .document_resolution.Aliases import DocumentAliasMixin
from .document_resolution.Matching import DocumentMatchingMixin
from .document_resolution.Registry import DocumentRegistryMixin


class DocumentResolutionMixin(
    DocumentRegistryMixin,
    DocumentAliasMixin,
    DocumentMatchingMixin,
):
    pass
