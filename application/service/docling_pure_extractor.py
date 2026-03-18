import tempfile
from pathlib import Path


class DoclingPureExtractor:
    def __init__(self):
        self._converter = None

    def _get_converter(self):
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
            except ImportError as exc:
                raise RuntimeError(
                    "Docling não está instalado. Adicione 'docling' às dependências do projeto."
                ) from exc

            self._converter = DocumentConverter()

        return self._converter

    def extract_markdown(self, file_bytes: bytes, suffix: str) -> str:
        converter = self._get_converter()

        with tempfile.NamedTemporaryFile(suffix=suffix or ".bin", delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file.flush()
            temp_path = Path(temp_file.name)

        try:
            result = converter.convert(str(temp_path))
            return result.document.export_to_markdown().strip()
        finally:
            temp_path.unlink(missing_ok=True)
