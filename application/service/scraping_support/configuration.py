"""Environment and path helpers for scraping."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
COLLECTIONS_ROOT = PROJECT_ROOT / "data" / "collections"

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

FIRECRAWL_LOCAL_URL = os.getenv("FIRECRAWL_LOCAL_URL") or os.getenv("SCRAPING_API_URL", "http://localhost:3002")
FIRECRAWL_CLOUD_URL = "https://api.firecrawl.dev"
