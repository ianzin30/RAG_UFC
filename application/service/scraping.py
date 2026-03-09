import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# override=True forces dotenv to overwrite any stale OS-level env vars
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COLLECTIONS_ROOT = PROJECT_ROOT / "data" / "collections"

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

FIRECRAWL_LOCAL_URL = os.getenv("FIRECRAWL_LOCAL_URL") or os.getenv("SCRAPING_API_URL", "http://localhost:3002")
FIRECRAWL_CLOUD_URL = "https://api.firecrawl.dev"

class ScrapingService:
    def __init__(self):
        self.api_key = os.getenv("SCRAPING_API_KEY") or os.getenv("FIRECRAWL_API_KEY")
        self.api_source = None
        self.app = self._build_firecrawl_client()

    def _is_local_firecrawl_available(self):
        try:
            with urlopen(FIRECRAWL_LOCAL_URL, timeout=2) as response:
                return response.status < 500
        except (URLError, TimeoutError, OSError):
            return False

    def _build_firecrawl_client(self):
        if self._is_local_firecrawl_available():
            self.api_source = "local"
            return FirecrawlApp(api_url=FIRECRAWL_LOCAL_URL)

        if not self.api_key:
            raise Exception("Missing SCRAPING_API_KEY. Start the local Firecrawl or set SCRAPING_API_KEY in your .env file.")

        self.api_source = "cloud"
        return FirecrawlApp(api_key=self.api_key, api_url=FIRECRAWL_CLOUD_URL)

    def _extract_urls_from_links(self, links):
        urls = []
        for item in links or []:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, dict):
                url = item.get("url") or item.get("link")
                if url:
                    urls.append(url)
            else:
                url = getattr(item, "url", None) or getattr(item, "link", None)
                if url:
                    urls.append(url)
        return urls

    def scrape_website(self, url, collection_name):
        try:
            # Use v1 map_url to discover links
            map_result = self.app.v1.map_url(url, limit=10)
            links = map_result.links or [] if map_result else []

            if not links:
                # Fallback: scrape just the root URL
                doc = self.app.v1.scrape_url(url, formats=["markdown"])
                if not doc or not doc.markdown:
                    raise Exception("Scrape returned no content.")
                collection_path = COLLECTIONS_ROOT / collection_name
                collection_path.mkdir(parents=True, exist_ok=True)
                (collection_path / "page_1.md").write_text(doc.markdown, encoding="utf-8")
                return {
                    "ok": True,
                    "files": 1,
                    "message": f"1 page saved to '{collection_name}'.",
                    "source": self.api_source,
                }

            print(f"Found {len(links)} links. Starting scraping...")

            # Use v1 batch_scrape_urls to scrape all links
            scrape_result = self.app.v1.batch_scrape_urls(links, formats=["markdown"])
            scraped_data = scrape_result.data if scrape_result and scrape_result.data else []

            collection_path = COLLECTIONS_ROOT / collection_name
            collection_path.mkdir(parents=True, exist_ok=True)

            count = 0
            for i, page in enumerate(scraped_data, 1):
                content = None
                if hasattr(page, "markdown") and page.markdown:
                    content = page.markdown
                elif isinstance(page, dict) and page.get("markdown"):
                    content = page["markdown"]
                if not content:
                    continue
                (collection_path / f"page_{i}.md").write_text(content, encoding="utf-8")
                count += 1

            return {
                "ok": True,
                "files": count,
                "message": f"{count} pages saved to '{collection_name}'.",
                "source": self.api_source,
            }

        except Exception as e:
            error_msg = f"Error during scraping: {str(e)}"
            print(error_msg)
            return {"ok": False, "error": error_msg, "source": self.api_source}
