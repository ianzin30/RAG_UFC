"""Firecrawl client selection helpers."""
# Simple: Choose between local or cloud website scraping service

from __future__ import annotations

from urllib.error import URLError
from urllib.request import urlopen

from firecrawl import FirecrawlApp

from .Configuration import FIRECRAWL_CLOUD_URL, FIRECRAWL_LOCAL_URL


# Esta checagem tenta preferir um Firecrawl local antes de usar a nuvem.
def is_local_firecrawl_available() -> bool:
    try:
        with urlopen(FIRECRAWL_LOCAL_URL, timeout=2) as response:
            return response.status < 500
    except (URLError, TimeoutError, OSError):
        return False


# Esta fabrica escolhe entre cliente local e cliente cloud conforme o ambiente.
def build_firecrawl_client(api_key: str | None):
    if is_local_firecrawl_available():
        return FirecrawlApp(api_url=FIRECRAWL_LOCAL_URL), "local"

    if not api_key:
        raise Exception("Missing SCRAPING_API_KEY. Start the local Firecrawl or set SCRAPING_API_KEY in your .env file.")

    return FirecrawlApp(api_key=api_key, api_url=FIRECRAWL_CLOUD_URL), "cloud"
