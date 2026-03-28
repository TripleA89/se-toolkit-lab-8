# Observability Skill

You have access to observability tools that let you query VictoriaLogs and VictoriaTraces. Use these to answer questions about system health, errors, and failures.

## Available Tools

### Log Tools (VictoriaLogs)

- **logs_search** — Search logs using LogsQL queries
  - Use `query="*"` for all recent logs
  - Use `query="severity:ERROR"` for errors (preferred)
  - Use `query="level:error OR severity:ERROR OR status:500"` as alternative
  - Use `query="service.name=\"Learning Management Service\""` for specific service
  - Use `query="trace_id=<ID>"` to find all logs for a specific trace
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

1. Call `logs_error_count(hours=1)`
2. If errors found, call `logs_search(query="severity:ERROR", limit=5)` to get details
3. Summarize: which services had errors, how many, what kind

### User asks: "What went wrong?" or "Investigate the failure" or "Check system health"

**This is a multi-step investigation. Chain the tools in one pass:**

1. **First:** Call `logs_search(query="severity:ERROR", limit=10, start="-1h")` to find recent errors
2. **Extract trace_id** from the error log entries (field: `trace_id`)
3. **Search for related logs** using `logs_search(query="trace_id:<ID>", limit=20)` — note: use `trace_id:<ID>` without quotes
4. **Try to fetch trace** with `traces_get(trace_id=<ID>)` if traces API is available
5. **Summarize findings:**
   - What failed (which service, which operation)
   - When it happened (timestamp)
   - Error message
   - Request flow (what happened before/after)
   - Root cause hypothesis

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
- **One-pass investigation** — when asked "What went wrong?", chain all tools and provide complete analysis in one response

## Example

**User:** "Any errors in the last hour?"

**You:**
1. Call `logs_error_count(hours=1)`
2. Result: "Learning Management Service: 3 errors"
3. Call `logs_search(query="severity:ERROR", limit=5)`
4. Found: "db_query failed: connection refused" at 14:32:15
5. **Response:** "⚠️ Yes, 3 errors in the last hour from the Learning Management Service. All are database connection failures - the backend couldn't reach PostgreSQL around 14:32. Check if the database container is running."

**User:** "What went wrong?"

**You:**
1. Call `logs_search(query="severity:ERROR", limit=10)`
2. Found error: `db_query - [Errno -2] Name or service not known` at 12:13:21
3. Extract trace_id: `ffaf216e04016d4b267cda764a17d46f`
4. Call `logs_search(query="trace_id=ffaf216e04016d4b267cda764a17d46f", limit=20)`
5. Reconstruct flow: `request_started → auth_success → db_query(ERROR) → request_completed(404)`
6. **Response:** 

"⚠️ **Failure detected at 12:13:21**

**Root cause:** Database connection failure — PostgreSQL unreachable

**Request flow (trace: ffaf216e...):**
- 12:13:20.709 — request_started (GET /items/)
- 12:13:20.712 — auth_success (authentication passed)
- 12:13:20.713 — db_query (attempting SELECT from item table)
- 12:13:21.210 — **ERROR: db_query failed** — `[Errno -2] Name or service not known`
- 12:13:21.213 — request_completed (404 Not Found)

**Impact:** All database queries failing. Users cannot access items, labs, or learner data.

**Action:** Check if PostgreSQL container is running: `docker compose ps postgres`"
