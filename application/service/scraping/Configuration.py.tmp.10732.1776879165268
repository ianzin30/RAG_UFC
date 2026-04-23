"""Environment and path helpers for scraping."""
# Simple: Settings for website scraping service

from __future__ import annotations

import os
from pathlib import Path

from ..RuntimeConfig import PROJECT_ROOT, load_project_environment


COLLECTIONS_ROOT = PROJECT_ROOT / "data" / "collections"

load_project_environment()

FIRECRAWL_LOCAL_URL = os.getenv("FIRECRAWL_LOCAL_URL") or os.getenv("SCRAPING_API_URL", "http://localhost:3002")
FIRECRAWL_CLOUD_URL = "https://api.firecrawl.dev"
