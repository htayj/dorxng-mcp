"""MCP tool server for DorXNG-compatible SearXNG instances."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import DEFAULT_DATABASE, DEFAULT_SERVER, query_database, read_server_list, search, store_results

mcp = FastMCP("dorxng-mcp")


@mcp.tool()
def dorxng_search(
    query: str,
    server: str = DEFAULT_SERVER,
    server_list_file: str | None = None,
    pages: int = 1,
    concurrency: int = 4,
    timeout_seconds: float = 120.0,
    database: str | None = DEFAULT_DATABASE,
    verify_tls: bool = False,
) -> dict[str, Any]:
    """Search through DorXNG/SearXNG and optionally store results in SQLite.

    Use only DorXNG-controlled or private SearXNG instances; the DorXNG upstream
    explicitly asks users not to run this workflow against public SearXNG
    instances. ``server_list_file`` accepts DorXNG's newline-delimited server.lst
    format and takes precedence over ``server`` when provided.
    """
    servers = read_server_list(server_list_file) if server_list_file else None
    results = search(
        query,
        server=server,
        servers=servers,
        pages=pages,
        concurrency=concurrency,
        timeout=timeout_seconds,
        verify_tls=verify_tls,
    )
    total_database_rows = None
    if database:
        total_database_rows = store_results(database, results)
    return {
        "query": query,
        "result_count": len(results),
        "database": database,
        "total_database_rows": total_database_rows,
        "results": [result.as_dict() for result in results],
    }


@mcp.tool()
def dorxng_query_database(database: str = DEFAULT_DATABASE, pattern: str = ".*", limit: int = 100) -> dict[str, Any]:
    """Regex-search a DorXNG SQLite database by query, title, or URL."""
    matches = query_database(database, pattern, limit=limit)
    return {"database": database, "pattern": pattern, "count": len(matches), "results": matches}


@mcp.tool()
def dorxng_server_help() -> dict[str, Any]:
    """Return setup hints for the upstream DorXNG SearXNG container."""
    return {
        "default_server": DEFAULT_SERVER,
        "upstream": "https://github.com/ResearchandDestroy/DorXNG",
        "docker_quickstart": "docker run researchanddestroy/searxng:latest",
        "server_list_format": "Newline-delimited SearXNG /search URLs, e.g. https://172.17.0.2/search",
        "warning": "Use private DorXNG/SearXNG instances, not public SearXNG instances.",
    }


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
