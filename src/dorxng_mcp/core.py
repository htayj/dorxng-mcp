"""Core DorXNG/SearXNG search and database helpers.

DorXNG itself is a Python CLI that posts SearXNG-compatible search requests with
``q``, ``format=json``, and ``pageno`` parameters, then stores ``title``/``url``
results in SQLite.  This module implements the same integration surface in a
small library so the MCP layer can expose it as tools.
"""

from __future__ import annotations

import concurrent.futures
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_SERVER = "https://127.0.0.1:8443/search"
DEFAULT_DATABASE = "dorxng.db"
USER_AGENT = "DorXNG-MCP"


@dataclass(frozen=True)
class SearchResult:
    query: str
    title: str
    url: str
    engine: str | None = None
    content: str | None = None
    page: int | None = None
    server: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "query": self.query,
            "title": self.title,
            "url": self.url,
        }
        if self.engine:
            data["engine"] = self.engine
        if self.content:
            data["content"] = self.content
        if self.page is not None:
            data["page"] = self.page
        if self.server:
            data["server"] = self.server
        return data


def normalize_servers(server: str | None = None, servers: Iterable[str] | None = None) -> list[str]:
    """Return a non-empty list of search endpoint URLs."""
    if servers:
        normalized = [item.strip() for item in servers if item and item.strip()]
        if normalized:
            return normalized
    if server and server.strip():
        return [server.strip()]
    return [DEFAULT_SERVER]


def read_server_list(path: str | Path) -> list[str]:
    """Read newline-delimited DorXNG/SearXNG server URLs."""
    file_path = Path(path).expanduser()
    return [line.strip() for line in file_path.read_text().splitlines() if line.strip() and not line.startswith("#")]


def _request_page(query: str, page: int, server: str, timeout: float, verify_tls: bool) -> list[SearchResult]:
    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.post(
        server,
        data={"q": query, "format": "json", "pageno": page},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        verify=verify_tls,
    )
    response.raise_for_status()
    payload = response.json()
    raw_results = payload.get("results") or []
    results: list[SearchResult] = []
    for item in raw_results:
        title = item.get("title")
        url = item.get("url")
        if not title or not url:
            continue
        results.append(
            SearchResult(
                query=query,
                title=str(title),
                url=str(url),
                engine=item.get("engine"),
                content=item.get("content"),
                page=page,
                server=server,
            )
        )
    return results


def search(
    query: str,
    *,
    server: str | None = None,
    servers: Iterable[str] | None = None,
    pages: int = 1,
    concurrency: int = 4,
    timeout: float = 120.0,
    verify_tls: bool = False,
) -> list[SearchResult]:
    """Run a DorXNG-style SearXNG JSON search.

    Pages are distributed round-robin across the supplied servers.  Results are
    de-duplicated by ``(query, title, url)`` while preserving first-seen order.
    """
    if not query or not query.strip():
        raise ValueError("query is required")
    if pages < 1:
        raise ValueError("pages must be >= 1")
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")

    endpoint_list = normalize_servers(server, servers)
    page_numbers = list(range(1, pages + 1))
    results: list[SearchResult] = []

    max_workers = min(concurrency, len(page_numbers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_page = {
            executor.submit(
                _request_page,
                query.strip(),
                page,
                endpoint_list[(page - 1) % len(endpoint_list)],
                timeout,
                verify_tls,
            ): page
            for page in page_numbers
        }
        for future in concurrent.futures.as_completed(future_to_page):
            results.extend(future.result())

    seen: set[tuple[str, str, str]] = set()
    deduped: list[SearchResult] = []
    for result in sorted(results, key=lambda item: (item.page or 0, item.title, item.url)):
        key = (result.query, result.title, result.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def init_database(database: str | Path) -> Path:
    """Create the DorXNG-compatible search_results table if needed."""
    db_path = Path(database).expanduser()
    if db_path.parent != Path(""):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS search_results "
            "(query TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL)"
        )
    return db_path


def store_results(database: str | Path, results: Iterable[SearchResult]) -> int:
    """Insert results into a DorXNG-compatible SQLite database.

    Returns the number of rows currently in ``search_results``.
    """
    db_path = init_database(database)
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            "INSERT INTO search_results(query, title, url) VALUES (?, ?, ?)",
            [(result.query, result.title, result.url) for result in results],
        )
        connection.execute(
            "DELETE FROM search_results WHERE rowid NOT IN ("
            "SELECT MIN(rowid) FROM search_results GROUP BY query, title, url"
            ")"
        )
        row = connection.execute("SELECT COUNT(*) FROM search_results").fetchone()
    return int(row[0]) if row else 0


def query_database(database: str | Path, pattern: str, *, limit: int = 100) -> list[dict[str, str]]:
    """Regex-search a DorXNG SQLite database by query, title, or URL."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    db_path = Path(database).expanduser()
    if not db_path.exists():
        raise FileNotFoundError(f"database not found: {db_path}")
    compiled = re.compile(pattern, re.IGNORECASE)
    matches: list[dict[str, str]] = []
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT query, title, url FROM search_results ORDER BY query, title, url").fetchall()
    for query, title, url in rows:
        if compiled.search(query) or compiled.search(title) or compiled.search(url):
            matches.append({"query": query, "title": title, "url": url})
            if len(matches) >= limit:
                break
    return matches
