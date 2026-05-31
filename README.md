# Incident-Memory-Agent

A Coral-powered incident memory layer for SRE workflows. Engineers can query past incidents, RCA history, and ticket context using a single SQL query instead of manually searching across raw tools or logs.

## Problem

During production incidents, engineers often waste time asking:
- Have we seen this issue before?
- What was the root cause last time?
- Which ticket tracked the fix?
- Who owned the incident and what follow-up was done?

Without a memory layer, agents or engineers end up reading raw APIs, dashboards, or logs, which is slower and more expensive.

## Solution

This project builds an **incident memory agent** backed by Coral.

Coral exposes incident history as a SQL table, and the agent runs one SQL query to retrieve compact, structured incident context. For the demo, the data source is a local JSONL file, but the same flow can later be extended to real enterprise systems like Jira, Datadog, ServiceNow, or Site24x7.

## How Coral is used

- A Coral source spec (`local-incidents.yaml`) maps local JSONL incident data into a SQL table.
- Coral exposes the data as `local_incidents.incidents`.
- The agent and web portal query this table using SQL.
- Coral returns structured rows that the AI summary layer can use directly.

## Architecture

```text
Engineer Query / Portal UI
        ↓
FastAPI Backend
        ↓
Coral SQL Query
        ↓
local_incidents.incidents
(JSONL-backed Coral source)
        ↓
Structured Incident Rows
        ↓
AI / Rule-based Summary
```

## Project structure

```text
coral-incident-memory/
  demo-data/
    incidents.jsonl
    local-incidents.yaml
  sql/
    incident_history.sql
  src/
    agent.py
    server.py
  incident-memory-portal.html
  README.md
```

## Demo features

- Query past incidents by service name
- View generated SQL sent to Coral
- Retrieve structured incident rows from Coral
- Display RCA and ticket context
- Show an AI-powered or local summary
- View a lightweight architecture screen inside the portal

## Sample query

```sql
SELECT
  service_name,
  alert_id,
  severity,
  started_at,
  summary,
  rca,
  ticket_key
FROM local_incidents.incidents
WHERE service_name = 'auth-service'
ORDER BY started_at DESC
LIMIT 5;
```

## Setup

### 1. Clone the project

```bash
git clone <your-repo-url>
cd coral-incident-memory
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn openai anthropic
```

### 3. Register Coral source

```bash
coral source add --file .\demo-data\local-incidents.yaml
coral source test local_incidents
coral sql "SELECT * FROM local_incidents.incidents LIMIT 5"
```

### 4. Run the backend

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open the portal

Open:

```text
http://localhost:8000
```

## Why this matters

This project shows how Coral can act as the memory and retrieval layer for enterprise agents. Instead of spending tokens and time reading raw tool output, the agent gets a compact SQL result and answers faster.

## Future improvements

- Connect real Jira or Datadog sources through Coral
- Add richer ticket fields like owner, status, and resolution
- Support natural language querying across multiple services
- Join incident history with deployments or runbooks
- Add filters for severity, time window, and incident class

## Built for

**Pirates of the Coral-bean Hackathon** by WeMakeDevs.

## Demo video


## Rajaram D

Add your name and GitHub profile here.

