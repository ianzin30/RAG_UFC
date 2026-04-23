# Simple: Download and process website content
"""Public facade for website scraping."""

import os

from .Client import build_firecrawl_client, is_local_firecrawl_available
from .Html import extract_page_links
from .Pipeline import (
    batch_scrape_documentation_urls,
    build_scrape_options,
    chunked,
    crawl_documentation_site,
    discover_documentation_urls,
    save_markdown_documents,
    scrape_documentation_site,
    scrape_website,
)
from .Urls import (
    build_include_paths,
    docs_prefix_from_parsed,
    filter_documentation_links,
    infer_docs_root_from_page,
    is_static_asset,
    normalize_url,
    resolve_docs_scope,
    same_site,
)


class ScrapingService:
    def __init__(self):
        self.api_key = os.getenv("SCRAPING_API_KEY") or os.getenv("FIRECRAWL_API_KEY")
        self.app, self.api_source = build_firecrawl_client(self.api_key)

    def _is_local_firecrawl_available(self):
        return is_local_firecrawl_available()

    def _build_firecrawl_client(self):
        app, api_source = build_firecrawl_client(self.api_key)
        self.api_source = api_source
        return app

    def _normalize_url(self, url):
        return normalize_url(url)

    def _same_site(self, host_a: str, host_b: str) -> bool:
        return same_site(host_a, host_b)

    def _docs_prefix_from_parsed(self, parsed):
        return docs_prefix_from_parsed(parsed)

    def _is_static_asset(self, path: str) -> bool:
        return is_static_asset(path)

    def _build_include_paths(self, url):
        return build_include_paths(url)

    def _extract_page_links(self, url):
        return extract_page_links(url)

    def _infer_docs_root_from_page(self, url):
        return infer_docs_root_from_page(url)

    def _resolve_docs_scope(self, url):
        return resolve_docs_scope(url)

    def _filter_documentation_links(self, links, docs_root, docs_prefix):
        return filter_documentation_links(links, docs_root, docs_prefix)

    def _build_scrape_options(self):
        return build_scrape_options()

    def _discover_documentation_urls(self, docs_root, docs_prefix):
        return discover_documentation_urls(self.app, docs_root, docs_prefix)

    def _chunked(self, items, chunk_size):
        return chunked(items, chunk_size)

    def _batch_scrape_documentation_urls(self, urls):
        return batch_scrape_documentation_urls(self.app, urls)

    def _crawl_documentation_site(self, docs_root):
        return crawl_documentation_site(self.app, docs_root)

    def _scrape_documentation_site(self, url):
        return scrape_documentation_site(self.app, url)

    def _save_markdown_documents(self, pages, collection_name):
        return save_markdown_documents(pages, collection_name)

    def scrape_website(self, url, collection_name):
        return scrape_website(self.app, self.api_source, url, collection_name).to_dict()
