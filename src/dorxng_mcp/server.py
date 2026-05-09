"""MCP tool server for DorXNG-compatible SearXNG instances."""

from __future__ import annotations

from typing import Any, Iterable

from mcp.server.fastmcp import FastMCP

from .core import DEFAULT_DATABASE, DEFAULT_SERVER, SearchResult, query_database, read_server_list, search, store_results
from .dorking import suggest_dorks
from .safety import assert_no_illegal_sexual_material

mcp = FastMCP("dorxng-mcp")


def _failure(error_type: str, message: str, **metadata: Any) -> dict[str, Any]:
    """Return a structured, MCP-friendly failure payload."""
    payload: dict[str, Any] = {"ok": False, "error": {"type": error_type, "message": message}}
    if metadata:
        payload["metadata"] = metadata
    return payload


def _success(**payload: Any) -> dict[str, Any]:
    """Return a structured success payload."""
    return {"ok": True, **payload}


def _resolve_servers(server: str, server_list_file: str | None) -> list[str]:
    return read_server_list(server_list_file) if server_list_file else [server]


def _page_results(results: Iterable[SearchResult], *, limit: int, offset: int = 0) -> tuple[list[dict[str, Any]], bool]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if offset < 0:
        raise ValueError("offset must be >= 0")
    result_list = list(results)
    window = result_list[offset : offset + limit]
    return [result.as_dict() for result in window], offset + limit < len(result_list)


def _search_response(
    *,
    query: str,
    results: list[SearchResult],
    pages: int,
    concurrency: int,
    servers_used: list[str],
    limit: int,
    offset: int,
    stored: bool,
    database: str | None = None,
    total_database_rows: int | None = None,
) -> dict[str, Any]:
    returned_results, truncated = _page_results(results, limit=limit, offset=offset)
    return _success(
        query=query,
        result_count=len(results),
        returned_count=len(returned_results),
        offset=offset,
        limit=limit,
        truncated=truncated,
        pages_requested=pages,
        concurrency=concurrency,
        servers_used=servers_used,
        stored=stored,
        database=database,
        total_database_rows=total_database_rows,
        results=returned_results,
    )


@mcp.tool()
def dorxng_search(
    query: str,
    server: str = DEFAULT_SERVER,
    server_list_file: str | None = None,
    pages: int = 1,
    concurrency: int = 4,
    timeout_seconds: float = 120.0,
    verify_tls: bool = False,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Search DorXNG/SearXNG and return a capped inline result window.

    This tool is read-only from the MCP server's perspective: it does not write
    to SQLite. Use only authorized/private DorXNG or SearXNG instances; DorXNG
    upstream explicitly asks users not to run this workflow against public
    SearXNG instances. ``server_list_file`` accepts DorXNG's newline-delimited
    server.lst format and takes precedence over ``server`` when provided.
    """
    try:
        assert_no_illegal_sexual_material(query)
        servers = _resolve_servers(server, server_list_file)
        results = search(
            query,
            server=server,
            servers=servers,
            pages=pages,
            concurrency=concurrency,
            timeout=timeout_seconds,
            verify_tls=verify_tls,
        )
        return _search_response(
            query=query,
            results=results,
            pages=pages,
            concurrency=concurrency,
            servers_used=servers,
            limit=limit,
            offset=offset,
            stored=False,
        )
    except Exception as exc:
        return _failure(type(exc).__name__, str(exc), query=query, server=server, server_list_file=server_list_file)


@mcp.tool()
def dorxng_search_and_store(
    query: str,
    database: str,
    server: str = DEFAULT_SERVER,
    server_list_file: str | None = None,
    pages: int = 1,
    concurrency: int = 4,
    timeout_seconds: float = 120.0,
    verify_tls: bool = False,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    """Search DorXNG/SearXNG, explicitly store results, and return a capped window.

    ``database`` is required so persistence is an intentional side effect. The
    SQLite schema is compatible with DorXNG's ``search_results`` table.
    """
    try:
        assert_no_illegal_sexual_material(query)
        servers = _resolve_servers(server, server_list_file)
        results = search(
            query,
            server=server,
            servers=servers,
            pages=pages,
            concurrency=concurrency,
            timeout=timeout_seconds,
            verify_tls=verify_tls,
        )
        total_database_rows = store_results(database, results)
        return _search_response(
            query=query,
            results=results,
            pages=pages,
            concurrency=concurrency,
            servers_used=servers,
            limit=limit,
            offset=offset,
            stored=True,
            database=database,
            total_database_rows=total_database_rows,
        )
    except Exception as exc:
        return _failure(
            type(exc).__name__,
            str(exc),
            query=query,
            database=database,
            server=server,
            server_list_file=server_list_file,
        )


@mcp.tool()
def dorxng_query_database(database: str = DEFAULT_DATABASE, pattern: str = ".*", limit: int = 100) -> dict[str, Any]:
    """Regex-search a DorXNG SQLite database by query, title, or URL."""
    try:
        assert_no_illegal_sexual_material(pattern)
        matches = query_database(database, pattern, limit=limit)
        return _success(
            database=database,
            pattern=pattern,
            count=len(matches),
            returned_count=len(matches),
            limit=limit,
            truncated=False,
            results=matches,
        )
    except Exception as exc:
        return _failure(type(exc).__name__, str(exc), database=database, pattern=pattern, limit=limit)


@mcp.tool()
def dorxng_get_dorking_guidance(
    target: str | None = None,
    objective: str = "broad",
    file_types: list[str] | None = None,
) -> dict[str, Any]:
    """Return search-operator guidance and DorXNG query templates for file discovery.

    ``target`` may be a domain or URL prefix to scope templates with ``site:``.
    ``objective`` can be ``broad``, ``files``, ``archives``, ``directories``, or
    ``code``. ``file_types`` customizes file-extension templates.
    """
    try:
        assert_no_illegal_sexual_material(target, objective, file_types)
        return _success(**suggest_dorks(target=target, objective=objective, file_types=file_types))
    except Exception as exc:
        return _failure(type(exc).__name__, str(exc), target=target, objective=objective, file_types=file_types)


@mcp.tool()
def dorxng_get_setup_info() -> dict[str, Any]:
    """Return setup information for private upstream DorXNG/SearXNG containers."""
    return _success(
        default_server=DEFAULT_SERVER,
        upstream="https://github.com/ResearchandDestroy/DorXNG",
        docker_quickstart="docker run researchanddestroy/searxng:latest",
        server_list_format="Newline-delimited SearXNG /search URLs, e.g. https://172.17.0.2/search",
        warning="Use private DorXNG/SearXNG instances, not public SearXNG instances.",
    )


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
