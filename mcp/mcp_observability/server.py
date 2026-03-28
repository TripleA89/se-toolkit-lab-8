"""Stdio MCP server exposing observability tools for VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

server = Server("observability")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_VICTORIALOGS_URL: str = ""
_VICTORIATRACES_URL: str = ""


def _resolve_victorialogs_url() -> str:
    return _VICTORIALOGS_URL or os.environ.get("VICTORIALOGS_URL", "http://localhost:9428")


def _resolve_victoriatraces_url() -> str:
    return _VICTORIATRACES_URL or os.environ.get("VICTORIATRACES_URL", "http://localhost:10428")


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class _LogsSearchArgs(BaseModel):
    query: str = Field(
        default="*",
        description="LogsQL query string. Use _stream:{service=\"backend\"} AND level:error for errors.",
    )
    limit: int = Field(default=10, ge=1, le=100, description="Max log entries to return (default 10).")
    start: str = Field(
        default="-1h",
        description="Start time for the query (e.g., '-1h', '-24h', '2024-01-01Z'). Default: last hour.",
    )


class _LogsErrorCountArgs(BaseModel):
    service: str = Field(default="*", description="Service name to filter (use '*' for all services).")
    hours: int = Field(default=1, ge=1, le=168, description="Time window in hours (default 1, max 168).")


class _TracesListArgs(BaseModel):
    service: str = Field(description="Service name to filter traces (e.g., 'Learning Management Service').")
    limit: int = Field(default=10, ge=1, le=100, description="Max traces to return (default 10).")


class _TracesGetArgs(BaseModel):
    trace_id: str = Field(description="Trace ID to fetch (hex string, e.g., '2a9b55532c5147def04ae2d4ff35340c').")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text(data: Any) -> list[TextContent]:
    """Serialize data to JSON text."""
    if isinstance(data, str):
        return [TextContent(type="text", text=data)]
    return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]


async def _http_get(url: str, params: dict[str, Any] | None = None, parse_ndjson: bool = False) -> Any:
    """Make HTTP GET request.
    
    Args:
        url: The URL to request
        params: Query parameters
        parse_ndjson: If True, parse response as newline-delimited JSON (VictoriaLogs format)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        if parse_ndjson:
            # VictoriaLogs returns NDJSON (newline-delimited JSON)
            lines = response.text.strip().split('\n')
            return [json.loads(line) for line in lines if line.strip()]
        return response.json()


# ---------------------------------------------------------------------------
# VictoriaLogs tool handlers
# ---------------------------------------------------------------------------


async def _logs_search(args: _LogsSearchArgs) -> list[TextContent]:
    """Search logs using VictoriaLogs LogsQL query."""
    url = f"{_resolve_victorialogs_url()}/select/logsql/query"
    params = {
        "query": args.query,
        "limit": args.limit,
    }
    if args.start:
        params["start"] = args.start

    try:
        result = await _http_get(url, params, parse_ndjson=True)
        # VictoriaLogs returns NDJSON - list of log entries
        if isinstance(result, list):
            summary = f"Found {len(result)} log entries:\n\n"
            entries = []
            for entry in result[:5]:  # Show first 5 entries in detail
                if isinstance(entry, dict):
                    ts = entry.get("_time", "unknown")
                    event = entry.get("event", entry.get("_msg", "unknown"))
                    service = entry.get("service.name", entry.get("service", "unknown"))
                    severity = entry.get("severity", entry.get("level", "INFO"))
                    error = entry.get("error")
                    error_text = f" - {error[:80]}" if error else ""
                    entries.append(f"[{ts}] {severity} - {service}: {event}{error_text}")
            if len(result) > 5:
                entries.append(f"... and {len(result) - 5} more entries")
            return _text(summary + "\n".join(entries))
        return _text(f"Query result: {json.dumps(result, indent=2)[:1000]}")
    except httpx.HTTPError as e:
        return _text(f"Error querying VictoriaLogs: {e}")
    except Exception as e:
        return _text(f"Error: {type(e).__name__}: {e}")


async def _logs_error_count(args: _LogsErrorCountArgs) -> list[TextContent]:
    """Count errors per service over a time window."""
    # Build LogsQL query for errors
    if args.service == "*":
        query = "level:error OR severity:ERROR OR status:500"
    else:
        query = f"_stream:{{service=\"{args.service}\"}} AND (level:error OR severity:ERROR OR status:500)"

    url = f"{_resolve_victorialogs_url()}/select/logsql/query"
    params = {
        "query": query,
        "start": f"-{args.hours}h",
        "limit": 1000,  # Get more to count accurately
    }

    try:
        result = await _http_get(url, params, parse_ndjson=True)
        if isinstance(result, list):
            # Count by service
            error_counts: dict[str, int] = {}
            for entry in result:
                if isinstance(entry, dict):
                    service = entry.get("service.name", entry.get("service", "unknown"))
                    error_counts[service] = error_counts.get(service, 0) + 1

            if not error_counts:
                return _text(f"No errors found in the last {args.hours} hour(s).")

            summary = f"Error count in the last {args.hours} hour(s):\n\n"
            for service, count in sorted(error_counts.items(), key=lambda x: -x[1]):
                summary += f"  - {service}: {count} errors\n"
            return _text(summary)
        return _text(f"No errors found. Query result: {result}")
    except httpx.HTTPError as e:
        return _text(f"Error querying VictoriaLogs: {e}")
    except Exception as e:
        return _text(f"Error: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# VictoriaTraces tool handlers
# ---------------------------------------------------------------------------


async def _traces_list(args: _TracesListArgs) -> list[TextContent]:
    """List recent traces for a service."""
    # Try Jaeger API first (standard VictoriaTraces API)
    url = f"{_resolve_victoriatraces_url()}/jaeger/api/traces"
    params = {
        "service": args.service,
        "limit": args.limit,
    }

    try:
        result = await _http_get(url, params)
        if isinstance(result, dict) and "data" in result:
            traces = result["data"]
            if not traces:
                return _text(f"No traces found for service '{args.service}'.")

            summary = f"Found {len(traces)} traces for '{args.service}':\n\n"
            for trace in traces[:5]:
                trace_id = trace.get("traceID", "unknown")
                spans = len(trace.get("spans", []))
                start_time = trace.get("startTime", 0)
                duration = trace.get("duration", 0)
                summary += f"  - Trace {trace_id[:16]}... | {spans} spans | {duration/1000:.1f}ms\n"

            if len(traces) > 5:
                summary += f"  ... and {len(traces) - 5} more traces"

            return _text(summary)
        
        # Handle "unsupported path" error message
        if isinstance(result, str) and "unsupported path" in result:
            return _text(f"VictoriaTraces Jaeger API not available. Use VictoriaLogs (logs_search) to query trace data via trace_id from logs.")
        
        return _text(f"No traces found. Response: {json.dumps(result)[:500]}")
    except httpx.HTTPError as e:
        return _text(f"Error querying VictoriaTraces: {e}")
    except Exception as e:
        return _text(f"Error: {type(e).__name__}: {e}")


async def _traces_get(args: _TracesGetArgs) -> list[TextContent]:
    """Fetch a specific trace by ID."""
    url = f"{_resolve_victoriatraces_url()}/jaeger/api/traces/{args.trace_id}"

    try:
        result = await _http_get(url)
        if isinstance(result, dict) and "data" in result:
            traces = result["data"]
            if not traces:
                return _text(f"Trace {args.trace_id} not found.")

            trace = traces[0]
            summary = f"Trace {args.trace_id}:\n\n"
            summary += f"  Services: {len(trace.get('processes', {}))}\n"
            summary += f"  Spans: {len(trace.get('spans', []))}\n"

            # Show span hierarchy
            spans = trace.get("spans", [])
            summary += "\n  Span hierarchy:\n"
            for span in spans[:10]:  # Show first 10 spans
                indent = "    " * (span.get("depth", 0))
                operation = span.get("operationName", "unknown")
                duration = span.get("duration", 0) / 1000
                summary += f"  {indent}- {operation} ({duration:.1f}ms)\n"

            if len(spans) > 10:
                summary += f"  ... and {len(spans) - 10} more spans"

            # Check for errors
            errors = []
            for span in spans:
                for log in span.get("logs", []):
                    if any(f.get("key") == "error" for f in log.get("fields", [])):
                        errors.append(span.get("operationName", "unknown"))

            if errors:
                summary += f"\n  ⚠️ Errors in spans: {', '.join(errors)}"

            return _text(summary)
        
        # Handle "unsupported path" error message
        if isinstance(result, str) and "unsupported path" in result:
            return _text(f"VictoriaTraces Jaeger API not available. Use logs_search with trace_id={args.trace_id[:16]} to find related log entries.")
        
        return _text(f"Trace not found. Response: {json.dumps(result)[:500]}")
    except httpx.HTTPError as e:
        return _text(f"Error querying VictoriaTraces: {e}")
    except Exception as e:
        return _text(f"Error: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_Registry = tuple[type[BaseModel], Callable[..., Awaitable[list[TextContent]]], Tool]

_TOOLS: dict[str, _Registry] = {}


def _register(
    name: str,
    description: str,
    model: type[BaseModel],
    handler: Callable[..., Awaitable[list[TextContent]]],
) -> None:
    schema = model.model_json_schema()
    schema.pop("$defs", None)
    schema.pop("title", None)
    _TOOLS[name] = (model, handler, Tool(name=name, description=description, inputSchema=schema))


_register(
    "logs_search",
    "Search logs in VictoriaLogs using LogsQL query. Use for finding specific events, errors, or patterns.",
    _LogsSearchArgs,
    _logs_search,
)
_register(
    "logs_error_count",
    "Count errors per service over a time window. Use to answer 'any errors in the last hour?'.",
    _LogsErrorCountArgs,
    _logs_error_count,
)
_register(
    "traces_list",
    "List recent traces for a service. Shows trace count, span count, and duration.",
    _TracesListArgs,
    _traces_list,
)
_register(
    "traces_get",
    "Fetch a specific trace by ID. Shows span hierarchy and identifies errors.",
    _TracesGetArgs,
    _traces_get,
)


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [entry[2] for entry in _TOOLS.values()]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    entry = _TOOLS.get(name)
    if entry is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    model_cls, handler, _ = entry
    try:
        args = model_cls.model_validate(arguments or {})
        return await handler(args)
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main(
    victorialogs_url: str | None = None,
    victoriatraces_url: str | None = None,
) -> None:
    global _VICTORIALOGS_URL, _VICTORIATRACES_URL
    _VICTORIALOGS_URL = victorialogs_url or os.environ.get("VICTORIALOGS_URL", "http://localhost:9428")
    _VICTORIATRACES_URL = victoriatraces_url or os.environ.get("VICTORIATRACES_URL", "http://localhost:10428")

    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
