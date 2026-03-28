# Observability Skill

You have access to observability tools that let you query VictoriaLogs and VictoriaTraces. Use these to answer questions about system health, errors, and failures.

## Available Tools

### Log Tools (VictoriaLogs)

- **logs_search** — Search logs using LogsQL queries
  - Use `query="*"` for all recent logs
  - Use `query="level:error OR severity:ERROR OR status:500"` for errors
  - Use `query="service.name=\"Learning Management Service\""` for specific service
  - Default time range: last hour (`start="-1h"`)
  - Returns: Formatted log entries with timestamp, severity, service, event, and error details

- **logs_error_count** — Count errors per service over a time window
  - Use this first when user asks "any errors?" or "system health?"
  - Returns count grouped by service
  - Default: last 1 hour

### Trace Tools (VictoriaTraces)

- **traces_list** — List recent traces for a service
  - Use to see request patterns and latencies
  - Shows trace count, span count, duration
  - Note: May return "Jaeger API not available" — use logs_search with trace_id instead

- **traces_get** — Fetch a specific trace by ID
  - Use when you find a trace ID in logs and want full details
  - Shows span hierarchy and identifies error spans
  - Note: May return "Jaeger API not available" — use logs_search with trace_id instead

## When to Use

### User asks: "Any errors in the last hour?"

1. Call `logs_error_count` with `hours=1`
2. If errors found, call `logs_search` with `query="severity:ERROR"` to get details
3. Summarize: which services had errors, how many, what kind

### User asks: "What went wrong?" or "Investigate the failure"

1. Call `logs_search` with `query="severity:ERROR"` to find recent errors
2. Look for trace IDs in error logs (field: `trace_id`)
3. If traces API is available, call `traces_get` with the trace ID
4. If traces API is unavailable, search logs with `query="trace_id=<ID>"` to find all related events
5. Identify: which service failed, what operation, what error

### User asks: "Show me logs for [service]"

1. Call `logs_search` with `query="service.name=\"[service]\""`
2. Summarize key events: requests, errors, slow operations

### User provides a trace ID

1. Call `logs_search` with `query="trace_id=<ID>"` to find all log entries for that trace
2. Reconstruct the request flow from the events
3. Identify where errors occurred

## Response Style

- **Be concise** — summarize findings, don't dump raw JSON
- **Highlight errors** — use ⚠️ or "ERROR" to draw attention
- **Include timestamps** — when did the error occur?
- **Connect logs and traces** — if you find a trace ID, search for related logs
- **Actionable** — what should the user do next? (restart service, check config, etc.)
- **Handle API limitations** — if traces API is unavailable, use logs to analyze trace data

## Example

**User:** "Any errors in the last hour?"

**You:**
1. Call `logs_error_count(hours=1)`
2. Result: "Learning Management Service: 3 errors"
3. Call `logs_search(query="severity:ERROR", limit=5)`
4. Found: "db_query failed: connection refused" at 14:32:15
5. **Response:** "⚠️ Yes, 3 errors in the last hour from the Learning Management Service. All are database connection failures - the backend couldn't reach PostgreSQL around 14:32. Check if the database container is running."

**User:** "What happened in trace ffaf216e04016d4b?"

**You:**
1. Call `logs_search(query="trace_id=ffaf216e04016d4b")`
2. Found: request_started → auth_success → db_query (ERROR: connection refused) → request_completed (404)
3. **Response:** "Trace ffaf216e04016d4b shows a failed request at 12:13:21. The backend authenticated successfully but the database query failed with 'connection refused' — PostgreSQL was unreachable at that moment."
