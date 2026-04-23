"""URL normalization and documentation-scope helpers."""
# Simple: Clean website URLs and find documentation pages

from __future__ import annotations

from urllib.error import URLError
from urllib.parse import urljoin, urlparse, urlunparse

from .Constants import DOCS_PATH_MARKERS, STATIC_FILE_EXTENSIONS
from .Html import extract_page_links


# Esta normalizacao garante uma URL canônica antes do scraping.
def normalize_url(url: str) -> str:
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


# Esta comparacao permite tratar subdominios como o mesmo site documental.
def same_site(host_a: str, host_b: str) -> bool:
    return host_a == host_b or host_a.endswith(f".{host_b}") or host_b.endswith(f".{host_a}")


# Esta funcao tenta descobrir o prefixo de documentacao no host ou no path.
def docs_prefix_from_parsed(parsed) -> str | None:
    host_prefix = parsed.netloc.split(".", 1)[0].lower()
    if host_prefix == "docs":
        return "/"

    segments = [segment for segment in parsed.path.split("/") if segment]
    for index, segment in enumerate(segments):
        if segment.lower() in DOCS_PATH_MARKERS:
            return "/" + "/".join(segments[: index + 1])
    return None


# Esta checagem evita incluir assets estaticos no conjunto de paginas candidatas.
def is_static_asset(path: str) -> bool:
    normalized_path = (path or "").lower()
    return any(normalized_path.endswith(extension) for extension in STATIC_FILE_EXTENSIONS)


# Esta montagem restringe o crawl para a subarvore mais provavel de documentacao.
def build_include_paths(url: str) -> list[str] | None:
    parsed = urlparse(url)
    docs_prefix = docs_prefix_from_parsed(parsed)
    if docs_prefix:
        return [f"^{docs_prefix}$", f"^{docs_prefix}/.*$"]

    base_path = parsed.path.rstrip("/")
    if not base_path:
        return None
    return [f"^{base_path}$", f"^{base_path}/.*$"]


# Esta heuristica observa links da pagina para inferir a raiz de docs quando ela nao veio explicita.
def infer_docs_root_from_page(url: str) -> str | None:
    parsed = urlparse(url)
    candidates = {}

    try:
        links = extract_page_links(url)
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, ValueError):
        return None

    for href in links:
        try:
            normalized_link = normalize_url(urljoin(url, href))
        except ValueError:
            continue

        link_parsed = urlparse(normalized_link)
        if not same_site(parsed.netloc, link_parsed.netloc):
            continue

        docs_prefix = docs_prefix_from_parsed(link_parsed)
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


# Esta etapa resolve a melhor URL-base e o prefixo que limitarao o scraping.
def resolve_docs_scope(url: str) -> tuple[str, str]:
    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)

    docs_prefix = docs_prefix_from_parsed(parsed)
    if docs_prefix:
        scope_url = urlunparse((parsed.scheme, parsed.netloc, docs_prefix, "", "", ""))
        return scope_url, docs_prefix

    inferred_root = infer_docs_root_from_page(normalized_url)
    if inferred_root:
        inferred_parsed = urlparse(inferred_root)
        inferred_prefix = docs_prefix_from_parsed(inferred_parsed) or "/"
        return inferred_root, inferred_prefix

    segments = [segment for segment in parsed.path.split("/") if segment]
    fallback_prefix = f"/{segments[0]}" if segments else "/"
    scope_url = urlunparse((parsed.scheme, parsed.netloc, fallback_prefix, "", "", ""))
    return scope_url, fallback_prefix


# Este filtro remove ruido e preserva apenas links que continuam dentro da documentacao.
def filter_documentation_links(links, docs_root: str, docs_prefix: str) -> list[str]:
    docs_parsed = urlparse(docs_root)
    filtered_urls = []
    seen_urls = set()

    for link in links or []:
        try:
            normalized_link = normalize_url(link)
        except ValueError:
            continue

        parsed = urlparse(normalized_link)
        if parsed.netloc != docs_parsed.netloc:
            continue
        if is_static_asset(parsed.path):
            continue
        if docs_prefix != "/" and parsed.path != docs_prefix and not parsed.path.startswith(f"{docs_prefix}/"):
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
