# dorxng-mcp

A Python [Model Context Protocol](https://modelcontextprotocol.io/) server for running DorXNG-style OSINT searches against private DorXNG/SearXNG instances and, when explicitly requested, storing results in DorXNG-compatible SQLite databases.

Upstream DorXNG: <https://github.com/ResearchandDestroy/DorXNG>

> DorXNG asks users **not** to run its workflow against public SearXNG instances. Use your own DorXNG/SearXNG container(s).

## Install

```bash
pip install -e .
```

## DorXNG/SearXNG quickstart

Run a private DorXNG SearXNG container:

```bash
docker run researchanddestroy/searxng:latest
```

This setup defaults to the current local Podman port mapping:

```text
https://127.0.0.1:8443/search
```

DorXNG's upstream Docker bridge convention is often `https://172.17.0.2/search`; pass `server` if your instance is exposed elsewhere.

For multiple instances, create a newline-delimited `server.lst`:

```text
https://172.17.0.2/search
https://172.17.0.3/search
```

## MCP configuration

Example MCP server entry:

```json
{
  "mcpServers": {
    "dorxng": {
      "command": "dorxng-mcp"
    }
  }
}
```

For local development without installing the script:

```json
{
  "mcpServers": {
    "dorxng": {
      "command": "python",
      "args": ["-m", "dorxng_mcp.server"],
      "env": { "PYTHONPATH": "/home/tay/projects/dorxng-mcp/src" }
    }
  }
}
```

## Tool response shape

Tools return structured payloads:

- Success: `{ "ok": true, ... }`
- Failure: `{ "ok": false, "error": { "type": "...", "message": "..." }, "metadata": { ... } }`

Search tools cap inline results with `limit`/`offset` and include metadata such as `result_count`, `returned_count`, `truncated`, `pages_requested`, `servers_used`, and `stored`.

## Tools

### `dorxng_search`

Runs a read-only SearXNG JSON search using DorXNG-compatible parameters (`q`, `format=json`, `pageno`). It does **not** write to SQLite.

Arguments:

- `query` (required): authorized search query or dork.
- `server`: single private SearXNG `/search` endpoint. Default: `https://127.0.0.1:8443/search`.
- `server_list_file`: newline-delimited list of private endpoints. Takes precedence over `server`.
- `pages`: number of result pages to request.
- `concurrency`: max concurrent page requests.
- `timeout_seconds`: per-request timeout.
- `verify_tls`: verify TLS certificates. Default `false` to match DorXNG's self-signed container workflow.
- `limit`: max results returned inline. Default `25`.
- `offset`: result offset for paging through the inline response window. Default `0`.

### `dorxng_search_and_store`

Runs the same search, explicitly stores de-duplicated results in a DorXNG-compatible SQLite database, and returns a capped inline result window.

Arguments are the same as `dorxng_search`, plus:

- `database` (required): SQLite database path to create/update.

### `dorxng_query_database`

Regex-searches a DorXNG-compatible SQLite database by query, title, or URL.

Arguments:

- `database`: SQLite database path. Default `dorxng.db`.
- `pattern`: case-insensitive regex. Default `.*`.
- `limit`: max matches returned. Default `100`.

### `dorxng_get_setup_info`

Returns upstream setup information and the private-instance safety warning.

## Development

```bash
python -m compileall src
python -m unittest discover -s tests
```
