"""Scraping pipeline helpers."""
# Simple: Download multiple website pages efficiently

from __future__ import annotations

from firecrawl.v1.client import V1ScrapeOptions

from .Configuration import COLLECTIONS_ROOT
from .Constants import DOCS_BATCH_SIZE, DOCS_DISCOVERY_LIMIT, DOCS_MAP_TIMEOUT_MS, SCRAPE_TIMEOUT_MS, SCRAPE_WAIT_MS
from .Models import ScrapeOutcome
from .Urls import build_include_paths, filter_documentation_links, normalize_url, resolve_docs_scope


# Estas opcoes padronizam o scraping de paginas isoladas e de crawls.
def build_scrape_options():
    return V1ScrapeOptions(
        formats=["markdown"],
        onlyMainContent=True,
        waitFor=SCRAPE_WAIT_MS,
        timeout=SCRAPE_TIMEOUT_MS,
        removeBase64Images=True,
        blockAds=True,
    )


# Esta descoberta tenta usar o mapa do Firecrawl antes de partir para um crawl mais caro.
def discover_documentation_urls(app, docs_root: str, docs_prefix: str) -> list[str]:
    try:
        map_result = app.v1.map_url(
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
    return filter_documentation_links(links, docs_root, docs_prefix)[:DOCS_DISCOVERY_LIMIT]


# Este helper quebra listas grandes em lotes menores para batch scraping.
def chunked(items, chunk_size: int):
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


# Este caminho prefere batch scraping quando ja conhecemos as URLs relevantes.
def batch_scrape_documentation_urls(app, urls) -> list:
    pages = []
    for chunk in chunked(urls, DOCS_BATCH_SIZE):
        batch_result = app.v1.batch_scrape_urls(
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


# Este caminho recorre ao crawl quando nao foi possivel descobrir URLs suficientes antes.
def crawl_documentation_site(app, docs_root: str) -> list:
    include_paths = build_include_paths(docs_root)
    crawl_result = app.v1.crawl_url(
        docs_root,
        include_paths=include_paths,
        max_depth=4,
        max_discovery_depth=6,
        limit=DOCS_DISCOVERY_LIMIT,
        deduplicate_similar_urls=True,
        ignore_query_parameters=True,
        scrape_options=build_scrape_options(),
        poll_interval=2,
    )
    return crawl_result.data if crawl_result and crawl_result.data else []


# Esta etapa escolhe entre batch scraping e crawl conforme a descoberta inicial.
def scrape_documentation_site(app, url: str) -> tuple[list, str]:
    docs_root, docs_prefix = resolve_docs_scope(url)
    urls = discover_documentation_urls(app, docs_root, docs_prefix)
    if urls:
        try:
            return batch_scrape_documentation_urls(app, urls), docs_root
        except Exception:
            pass
    return crawl_documentation_site(app, docs_root), docs_root


# Esta persistencia grava cada pagina como markdown e remove duplicatas por URL.
def save_markdown_documents(pages, collection_name: str) -> int:
    collection_path = COLLECTIONS_ROOT / collection_name
    collection_path.mkdir(parents=True, exist_ok=True)
    for old_file in collection_path.glob("*.md"):
        old_file.unlink()

    count = 0
    seen_urls = set()
    for index, page in enumerate(pages, start=1):
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
        (collection_path / f"page_{index}.md").write_text(f"{prefix}{content}", encoding="utf-8")
        count += 1

    return count


# Esta e a porta principal do scraper, com fallback final para pagina unica.
def scrape_website(app, api_source: str | None, url: str, collection_name: str) -> ScrapeOutcome:
    try:
        normalized_url = normalize_url(url)
        scraped_data, docs_root = scrape_documentation_site(app, normalized_url)
        target_url = docs_root or normalized_url
        count = save_markdown_documents(scraped_data, collection_name)

        if count == 0:
            doc = app.v1.scrape_url(
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
            count = save_markdown_documents([doc], collection_name)

        return ScrapeOutcome(
            ok=True,
            files=count,
            message=f"{count} pages saved to '{collection_name}'.",
            source=api_source,
            strategy="documentation",
            target_url=target_url,
        )
    except Exception as exc:
        error_msg = f"Error during scraping: {exc}"
        print(error_msg)
        return ScrapeOutcome(ok=False, error=error_msg, source=api_source)
