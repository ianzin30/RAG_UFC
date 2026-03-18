import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from firecrawl.v1.client import V1ScrapeOptions

# override=True forces dotenv to overwrite any stale OS-level env vars
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COLLECTIONS_ROOT = PROJECT_ROOT / "data" / "collections"

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

FIRECRAWL_LOCAL_URL = os.getenv("FIRECRAWL_LOCAL_URL") or os.getenv("SCRAPING_API_URL", "http://localhost:3002")
FIRECRAWL_CLOUD_URL = "https://api.firecrawl.dev"

DOCS_PATH_MARKERS = ("docs", "documentation", "guide", "guides", "manual", "help", "learn")
DOCS_DISCOVERY_LIMIT = 120
DOCS_MAP_TIMEOUT_MS = 120000
DOCS_BATCH_SIZE = 25
GENERIC_CRAWL_LIMIT = 40
SCRAPE_TIMEOUT_MS = 60000
SCRAPE_WAIT_MS = 1000
STATIC_FILE_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".css",
    ".js",
    ".xml",
    ".json",
    ".txt",
    ".zip",
    ".mp4",
    ".mov",
    ".avi",
    ".webm",
)


class _AnchorParser(HTMLParser):
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

    def _normalize_url(self, url):
        raw_url = (url or "").strip()
        if not raw_url:
            raise ValueError("URL is required.")

        parsed = urlparse(raw_url)
        if not parsed.scheme:
            raw_url = f"https://{raw_url}"
            parsed = urlparse(raw_url)

        if not parsed.netloc:
            raise ValueError("Invalid URL.")

        path = parsed.path or "/"
        if path != "/":
            path = path.rstrip("/") or "/"

        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))

    def _same_site(self, host_a: str, host_b: str) -> bool:
        return host_a == host_b or host_a.endswith(f".{host_b}") or host_b.endswith(f".{host_a}")

    def _docs_prefix_from_parsed(self, parsed):
        host_prefix = parsed.netloc.split(".", 1)[0].lower()
        if host_prefix == "docs":
            return "/"

        segments = [segment for segment in parsed.path.split("/") if segment]
        for index, segment in enumerate(segments):
            if segment.lower() in DOCS_PATH_MARKERS:
                return "/" + "/".join(segments[: index + 1])

        return None

    def _is_static_asset(self, path: str) -> bool:
        normalized_path = (path or "").lower()
        return any(normalized_path.endswith(extension) for extension in STATIC_FILE_EXTENSIONS)

    def _build_include_paths(self, url):
        parsed = urlparse(url)
        docs_prefix = self._docs_prefix_from_parsed(parsed)
        if docs_prefix:
            return [f"^{docs_prefix}$", f"^{docs_prefix}/.*$"]

        base_path = parsed.path.rstrip("/")
        if not base_path:
            return None
        return [f"^{base_path}$", f"^{base_path}/.*$"]

    def _extract_page_links(self, url):
        parser = _AnchorParser()
        with urlopen(url, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset, errors="ignore")
        parser.feed(html)
        return parser.links

    def _infer_docs_root_from_page(self, url):
        parsed = urlparse(url)
        candidates = {}

        try:
            links = self._extract_page_links(url)
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, ValueError):
            return None

        for href in links:
            try:
                normalized_link = self._normalize_url(urljoin(url, href))
            except ValueError:
                continue

            link_parsed = urlparse(normalized_link)
            if not self._same_site(parsed.netloc, link_parsed.netloc):
                continue

            docs_prefix = self._docs_prefix_from_parsed(link_parsed)
            if not docs_prefix:
                continue

            candidate = urlunparse((link_parsed.scheme, link_parsed.netloc, docs_prefix, "", "", ""))
            candidates[candidate] = candidates.get(candidate, 0) + 1

        if not candidates:
            return None

        return min(
            candidates.items(),
            key=lambda item: (-item[1], len(urlparse(item[0]).path.strip("/").split("/")), item[0]),
        )[0]

    def _resolve_docs_scope(self, url):
        normalized_url = self._normalize_url(url)
        parsed = urlparse(normalized_url)

        docs_prefix = self._docs_prefix_from_parsed(parsed)
        if docs_prefix:
            scope_url = urlunparse((parsed.scheme, parsed.netloc, docs_prefix, "", "", ""))
            return scope_url, docs_prefix

        inferred_root = self._infer_docs_root_from_page(normalized_url)
        if inferred_root:
            inferred_parsed = urlparse(inferred_root)
            inferred_prefix = self._docs_prefix_from_parsed(inferred_parsed) or "/"
            return inferred_root, inferred_prefix

        segments = [segment for segment in parsed.path.split("/") if segment]
        fallback_prefix = f"/{segments[0]}" if segments else "/"
        scope_url = urlunparse((parsed.scheme, parsed.netloc, fallback_prefix, "", "", ""))
        return scope_url, fallback_prefix

    def _filter_documentation_links(self, links, docs_root, docs_prefix):
        docs_parsed = urlparse(docs_root)
        filtered_urls = []
        seen_urls = set()

        for link in links or []:
            try:
                normalized_link = self._normalize_url(link)
            except ValueError:
                continue

            parsed = urlparse(normalized_link)
            if parsed.netloc != docs_parsed.netloc:
                continue

            if self._is_static_asset(parsed.path):
                continue

            if docs_prefix != "/":
                if parsed.path != docs_prefix and not parsed.path.startswith(f"{docs_prefix}/"):
                    continue

            if normalized_link in seen_urls:
                continue

            seen_urls.add(normalized_link)
            filtered_urls.append(normalized_link)

        if docs_root not in seen_urls:
            filtered_urls.insert(0, docs_root)

        return sorted(
            filtered_urls,
            key=lambda item: (
                0 if item == docs_root else 1,
                len([segment for segment in urlparse(item).path.split("/") if segment]),
                item,
            ),
        )

    def _build_scrape_options(self):
        return V1ScrapeOptions(
            formats=["markdown"],
            onlyMainContent=True,
            waitFor=SCRAPE_WAIT_MS,
            timeout=SCRAPE_TIMEOUT_MS,
            removeBase64Images=True,
            blockAds=True,
        )

    def _discover_documentation_urls(self, docs_root, docs_prefix):
        try:
            map_result = self.app.v1.map_url(
                docs_root,
                limit=DOCS_DISCOVERY_LIMIT * 4,
                timeout=DOCS_MAP_TIMEOUT_MS,
                ignore_sitemap=False,
                include_subdomains=False,
                sitemap_only=False,
            )
        except Exception:
            return []

        links = map_result.links if map_result and map_result.success else []
        return self._filter_documentation_links(links, docs_root, docs_prefix)[:DOCS_DISCOVERY_LIMIT]

    def _chunked(self, items, chunk_size):
        for index in range(0, len(items), chunk_size):
            yield items[index : index + chunk_size]

    def _batch_scrape_documentation_urls(self, urls):
        pages = []
        for chunk in self._chunked(urls, DOCS_BATCH_SIZE):
            batch_result = self.app.v1.batch_scrape_urls(
                chunk,
                formats=["markdown"],
                only_main_content=True,
                wait_for=SCRAPE_WAIT_MS,
                timeout=SCRAPE_TIMEOUT_MS,
                remove_base64_images=True,
                block_ads=True,
                max_concurrency=5,
                poll_interval=2,
            )
            pages.extend(batch_result.data or [])
        return pages

    def _crawl_documentation_site(self, docs_root):
        include_paths = self._build_include_paths(docs_root)
        crawl_result = self.app.v1.crawl_url(
            docs_root,
            include_paths=include_paths,
            max_depth=4,
            max_discovery_depth=6,
            limit=DOCS_DISCOVERY_LIMIT,
            deduplicate_similar_urls=True,
            ignore_query_parameters=True,
            scrape_options=self._build_scrape_options(),
            poll_interval=2,
        )
        return crawl_result.data if crawl_result and crawl_result.data else []

    def _scrape_documentation_site(self, url):
        docs_root, docs_prefix = self._resolve_docs_scope(url)

        urls = self._discover_documentation_urls(docs_root, docs_prefix)
        if urls:
            try:
                return self._batch_scrape_documentation_urls(urls), docs_root
            except Exception:
                pass

        return self._crawl_documentation_site(docs_root), docs_root

    def _save_markdown_documents(self, pages, collection_name):
        collection_path = COLLECTIONS_ROOT / collection_name
        collection_path.mkdir(parents=True, exist_ok=True)
        for old_file in collection_path.glob("*.md"):
            old_file.unlink()

        count = 0
        seen_urls = set()
        for i, page in enumerate(pages, 1):
            content = None
            metadata = None

            if hasattr(page, "markdown") and page.markdown:
                content = page.markdown
                metadata = getattr(page, "metadata", None)
            elif isinstance(page, dict) and page.get("markdown"):
                content = page["markdown"]
                metadata = page.get("metadata")

            if not content:
                continue

            source_url = None
            if isinstance(metadata, dict):
                source_url = metadata.get("sourceURL") or metadata.get("url")
            source_url = source_url or getattr(page, "url", None)

            if source_url and source_url in seen_urls:
                continue

            if source_url:
                seen_urls.add(source_url)

            prefix = f"Source URL: {source_url}\n\n" if source_url else ""
            (collection_path / f"page_{i}.md").write_text(f"{prefix}{content}", encoding="utf-8")
            count += 1

        return count

    def scrape_website(self, url, collection_name):
        try:
            normalized_url = self._normalize_url(url)
            scraped_data, docs_root = self._scrape_documentation_site(normalized_url)

            strategy = "documentation"
            target_url = docs_root or normalized_url

            count = self._save_markdown_documents(scraped_data, collection_name)

            if count == 0:
                doc = self.app.v1.scrape_url(
                    target_url,
                    formats=["markdown"],
                    only_main_content=True,
                    wait_for=SCRAPE_WAIT_MS,
                    timeout=SCRAPE_TIMEOUT_MS,
                    remove_base64_images=True,
                    block_ads=True,
                )
                if not doc or not doc.markdown:
                    raise Exception("Scrape returned no content.")
                count = self._save_markdown_documents([doc], collection_name)

            return {
                "ok": True,
                "files": count,
                "message": f"{count} pages saved to '{collection_name}'.",
                "source": self.api_source,
                "strategy": strategy,
                "target_url": target_url,
            }

        except Exception as e:
            error_msg = f"Error during scraping: {str(e)}"
            print(error_msg)
            return {"ok": False, "error": error_msg, "source": self.api_source}
