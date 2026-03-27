# Lab 8 — Report

Paste your checkpoint evidence below. Add screenshots as image files in the repo and reference them with `![description](path)`.

## Task 1A — Bare agent

### Question 1: "What is the agentic loop?"

**Answer:**
The agentic loop is the core architectural pattern that enables AI agents to act autonomously and complete multi-step tasks. It's what distinguishes an AI agent from a simple chatbot.

**The Basic Concept:**
At its simplest, the agentic loop is an iterative cycle where an AI:
1. **Perceives** - Receives input (user request, API response, error, etc.)
2. **Reasons** - The LLM processes context and decides what to do next
3. **Plans** - For complex tasks, breaks down the objective into subtasks
4. **Acts** - Executes an action (tool call, API request, database query, etc.)
5. **Observes** - Examines the result and determines if the task is complete

Then it loops back to step 1 until the task is done or a stopping condition is reached.

**In Code:**
```python
while not done:
    response = call_llm(messages)
    if response has tool_calls:
        results = execute_tools(response.tool_calls)
        messages.append(results)
    else:
        done = True
        return response
```

**Why It Matters:**
Chatbots respond in a single pass—one input, one output, no state between turns. They can't iterate on results, recover from failures, or handle dependent tasks. Agents persist across multiple steps, adapting based on intermediate results.

### Question 2: "What labs are available in our LMS?"

**Answer:**
The agent found lab tasks in the file system (lab/tasks/required/task-1.md through task-5.md, and lab/tasks/optional/task-1.md), but **not from the LMS backend API**. This is expected because the agent has no MCP tools configured yet — it can only access files and general knowledge, not the actual LMS database.

**Key observation:** Without tools, the agent cannot query the real LMS backend at `http://localhost:42002`. It will hallucinate or find alternative sources (like file paths).

## Task 1B — Agent with LMS tools

### Question 1: "What labs are available?"

**Answer:**
The agent returned real lab data from the LMS backend:

| Lab ID | Title |
|--------|-------|
| Lab 01 | Products, Architecture & Roles |
| Lab 02 | Run, Fix, and Deploy a Backend Service |
| Lab 03 | Backend API: Explore, Debug, Implement, Deploy |
| Lab 04 | Testing, Front-end, and AI Agents |
| Lab 05 | Data Pipeline and Analytics Dashboard |
| Lab 06 | Build Your Own Agent |
| Lab 07 | Build a Client with an AI Coding Agent |
| Lab 08 | lab-08 |

**Key observation:** Unlike Part A (where the agent found file paths), now it queries the actual PostgreSQL database via MCP tools.

### Question 2: "Describe the architecture of the LMS system"

**Answer:**
The agent provided a comprehensive architecture description:

**Container Architecture (7 containers):**
- **Caddy** (Port 42002) — Reverse proxy + static file server
- **FastAPI** (Port 8000) — REST API backend
- **Nanobot** (Port 8765) — AI agent with MCP tools
- **PostgreSQL** (Port 42004) — Database
- **pgAdmin** (Port 42003) — DB admin UI
- **Qwen Code API** — LLM provider
- **Observability Stack** — OpenTelemetry Collector, VictoriaLogs, VictoriaTraces

**Data Model (OBER-based):**
- `item` — Learning content hierarchy (course → lab → task → step)
- `learner` — Student profiles
- `interacts` — Interaction logs (view, attempt, complete)

**Key Design Decisions:**
- Monolith — Easier to deploy, test, and understand for students
- SQLModel — Combines ORM + validation in one class hierarchy
- Async DB — Consistent with FastAPI's async model
- Feature Flags — Control endpoint availability without code changes
- WebSocket Agent — Symmetric architecture for multiple clients

The agent correctly identified all components and their relationships by calling MCP tools (`lms_labs`, `lms_learners`, etc.) and reasoning about the system.

## Task 1C — Skill prompt

### Question: "Show me the scores" (without specifying a lab)

**Answer:**
The agent displayed a comprehensive overview of all lab scores with key insights:

**Lab 01 – Products, Architecture & Roles**
| Task | Avg Score | Attempts |
|------|-----------|----------|
| Lab setup | 84.3% | 3,029 |
| Task 0: Practice the Git workflow | 64.5% | 306 |
| Task 1: Product & architecture description | 55.1% | 161 |
| Task 2: Roles and skills mapping | 49.8% | 83 |
| Optional tasks | 20-60% | 5-13 |

**Lab 02 — Run, Fix, and Deploy a Backend Service**
| Task | Avg Score | Attempts |
|------|-----------|----------|
| Task 1: Run the web server | 67.9% | 210 |
| Task 2: Identify, report, and fix a bug | 66.7% | 216 |
| Task 4: Deploy the web server to the VM | 56.2% | 84 |

*(Similar tables for Labs 03-07)*

**Key Insights from Agent:**
- **Highest scoring task:** Lab 01 "Lab setup" (84.3%)
- **Most attempted task:** Lab 01 "Lab setup" (3,029 attempts)
- **Lowest scoring:** Lab 02 "Make your VM a proxy" (0.0%) and Lab 01 "Plan skill development" (20.0%)
- **Lab 08 has no data yet** (likely the current lab)

**Skill prompt effect:**
The skill prompt (`nanobot/workspace/skills/lms/SKILL.md`) taught the agent to:
1. Format percentages nicely (e.g., "84.3%" not "0.843")
2. Use markdown tables for structured data
3. Provide key insights and summaries
4. Handle the case when no lab is specified — show all labs instead of asking for clarification (agent chose to be proactive)

## Task 2A — Deployed agent

<!-- Paste a short nanobot startup log excerpt showing the gateway started inside Docker -->

## Task 2B — Web client

<!-- Screenshot of a conversation with the agent in the Flutter web app -->

## Task 3A — Structured logging

<!-- Paste happy-path and error-path log excerpts, VictoriaLogs query screenshot -->

## Task 3B — Traces

<!-- Screenshots: healthy trace span hierarchy, error trace -->

## Task 3C — Observability MCP tools

<!-- Paste agent responses to "any errors in the last hour?" under normal and failure conditions -->

## Task 4A — Multi-step investigation

<!-- Paste the agent's response to "What went wrong?" showing chained log + trace investigation -->

## Task 4B — Proactive health check

<!-- Screenshot or transcript of the proactive health report that appears in the Flutter chat -->

## Task 4C — Bug fix and recovery

<!-- 1. Root cause identified
     2. Code fix (diff or description)
     3. Post-fix response to "What went wrong?" showing the real underlying failure
     4. Healthy follow-up report or transcript after recovery -->
