"""HTML parsing helpers for documentation discovery."""
# Simple: Parse HTML web pages to find documentation links

from __future__ import annotations

from html.parser import HTMLParser
from urllib.request import urlopen


# Este parser extrai hrefs simples para ajudar a inferir a raiz da documentacao.
class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)
                break


# Esta leitura baixa a pagina inicial e coleta links para a etapa de descoberta.
def extract_page_links(url: str) -> list[str]:
    parser = AnchorParser()
    with urlopen(url, timeout=10) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="ignore")
    parser.feed(html)
    return parser.links
