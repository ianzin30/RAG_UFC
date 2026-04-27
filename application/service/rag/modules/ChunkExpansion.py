"""
Chunk expansion to recover from poor chunk boundaries.

When a chunk is selected for context, expand it with surrounding sentences
to ensure complete statements and answers are included.

Problem solved:
- Answers that span chunk boundaries (e.g., "deseja realizar Pós-Doutorado...
  [chunk boundary] Rio de Janeiro")
- Incomplete facts due to hard chunk boundaries
- Selection of chunks that are fragments of larger ideas

Solution:
- Window expansion: add ±N sentences around selected chunk
- Semantic boundary preservation: don't cut mid-clause if possible
- Configurable expansion limits to control context size
"""
from __future__ import annotations

import re
from typing import Optional


class ChunkExpansionMixin:
    """Expand selected chunks to include surrounding context."""

    def _expand_chunk_window(
        self,
        document_text: str,
        chunk_start_offset: int,
        chunk_end_offset: int,
        left_sentences: int = 2,
        right_sentences: int = 2,
        max_expansion_chars: int = 2000,
    ) -> tuple[int, int]:
        """Expand chunk boundaries to include surrounding sentences.

        Args:
            document_text: Full document text
            chunk_start_offset: Start position of chunk
            chunk_end_offset: End position of chunk
            left_sentences: Number of sentences to add before chunk
            right_sentences: Number of sentences to add after chunk
            max_expansion_chars: Maximum total chars to add

        Returns:
            Tuple of (new_start, new_end) offsets
        """
        new_start = chunk_start_offset
        new_end = chunk_end_offset

        # Find sentence boundaries
        sentence_pattern = r'[.!?]+\s+'

        # Expand left
        if left_sentences > 0 and new_start > 0:
            search_area = document_text[:new_start]
            sentence_matches = list(re.finditer(sentence_pattern, search_area))

            if sentence_matches:
                # Get the last N sentence boundaries
                boundary_indices = [m.end() for m in sentence_matches[-left_sentences:]]
                # Start from the earliest boundary that leaves room
                if boundary_indices:
                    new_start = max(0, boundary_indices[0])

        # Expand right
        if right_sentences > 0 and new_end < len(document_text):
            search_area = document_text[new_end:]
            sentence_matches = list(re.finditer(sentence_pattern, search_area))

            if sentence_matches:
                # Get the first N sentence boundaries
                boundary_indices = [
                    new_end + m.end() for m in sentence_matches[:right_sentences]
                ]
                if boundary_indices:
                    new_end = min(len(document_text), boundary_indices[-1])

        # Respect max expansion
        current_expansion = (new_start - chunk_start_offset) + (new_end - chunk_end_offset)
        if current_expansion > max_expansion_chars:
            # Scale back proportionally
            scale_factor = max_expansion_chars / max(current_expansion, 1)
            left_reduction = int((new_start - chunk_start_offset) * (1 - scale_factor))
            right_reduction = int((new_end - chunk_end_offset) * (1 - scale_factor))

            new_start = max(chunk_start_offset, new_start - left_reduction)
            new_end = min(len(document_text), new_end - right_reduction)

        return new_start, new_end

    def _expand_selected_chunks(
        self,
        selected_chunks: list[dict[str, object]],
        document_lookup: dict[str, str],
        left_sentences: int = 2,
        right_sentences: int = 2,
    ) -> list[dict[str, object]]:
        """Expand selected chunks with surrounding context.

        Args:
            selected_chunks: List of selected chunk candidates
            document_lookup: Map of document_name -> full text
            left_sentences: Sentences to add before each chunk
            right_sentences: Sentences to add after each chunk

        Returns:
            List of expanded chunks
        """
        expanded = []

        for chunk in selected_chunks:
            expanded_chunk = dict(chunk)
            document_name = chunk.get("document_name", "")
            original_text = chunk.get("text", "")

            # Skip if document not available
            if document_name not in document_lookup:
                expanded.append(expanded_chunk)
                continue

            full_text = document_lookup[document_name]
            chunk_start = full_text.find(original_text)

            # If text not found exactly, skip expansion
            if chunk_start == -1:
                expanded.append(expanded_chunk)
                continue

            chunk_end = chunk_start + len(original_text)

            # Expand boundaries
            new_start, new_end = self._expand_chunk_window(
                full_text,
                chunk_start,
                chunk_end,
                left_sentences=left_sentences,
                right_sentences=right_sentences,
            )

            # Update chunk text with expanded version
            expanded_text = full_text[new_start:new_end].strip()
            expanded_chunk["text"] = expanded_text
            expanded_chunk["expansion_reason"] = "window_expansion"
            expanded_chunk["original_text_length"] = len(original_text)
            expanded_chunk["expanded_text_length"] = len(expanded_text)

            expanded.append(expanded_chunk)

        return expanded

    def _should_expand_chunk(self, chunk: dict[str, object]) -> bool:
        """Determine if chunk should be expanded.

        Chunks are expanded if:
        - They're small (< 200 chars) relative to context
        - They contain incomplete sentences
        - They end mid-clause

        Args:
            chunk: Chunk to evaluate

        Returns:
            True if chunk should be expanded
        """
        text = str(chunk.get("text", "")).strip()

        # Always expand small chunks that might be fragments
        if len(text) < 200:
            return True

        # Don't expand if already quite large
        if len(text) > 1000:
            return False

        # Expand if text appears to end mid-sentence
        if not text.endswith(('.', '!', '?', ':', '"', "'")):
            return True

        return False
