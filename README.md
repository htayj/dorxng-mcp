# dorxng-mcp

A Python [Model Context Protocol](https://modelcontextprotocol.io/) server for running DorXNG-style OSINT searches against private DorXNG/SearXNG instances and storing results in DorXNG-compatible SQLite databases.

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

By convention DorXNG's first local Docker container is available at:

```text
https://172.17.0.2/search
```

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

## Tools

### `dorxng_search`

Runs a SearXNG JSON search using DorXNG-compatible parameters (`q`, `format=json`, `pageno`) and optionally stores results in SQLite.

Arguments:

- `query` (required): search query or dork.
- `server`: single SearXNG `/search` endpoint. Default: `https://172.17.0.2/search`.
- `server_list_file`: newline-delimited list of endpoints. Takes precedence over `server`.
- `pages`: number of result pages to request.
- `concurrency`: max concurrent page requests.
- `timeout_seconds`: per-request timeout.
- `database`: SQLite database path, default `dorxng.db`; pass null/empty to skip storing.
- `verify_tls`: verify TLS certificates. Default `false` to match DorXNG's self-signed container workflow.

### `dorxng_query_database`

Regex-searches a DorXNG-compatible SQLite database by query, title, or URL.

### `dorxng_server_help`

Returns upstream setup hints and safety warning.

## Development

```bash
python -m compileall src
python -m unittest discover -s tests
```
