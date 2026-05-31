"""
src/server.py — Incident Memory Agent Backend
Run: uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import subprocess
import json
import os
import re
from pathlib import Path
print("LOADED SERVER FROM:", __file__)
@app.get("/where")
async def where():
    return {"file": __file__, "portal_path": str(PORTAL_PATH), "exists": PORTAL_PATH.exists()}
app = FastAPI(title="Incident Memory Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Portal HTML path — resolves relative to server.py (goes up one level to project root)
PORTAL_PATH = Path(__file__).resolve().parent.parent / "incident-memory-portal.html"


# ─── SERVE PORTAL ───────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_portal():
    if PORTAL_PATH.exists():
        return FileResponse(str(PORTAL_PATH), media_type="text/html")
    # Return a helpful error page if not found
    return HTMLResponse(
        content=f"""<html><body style="font-family:monospace;padding:2rem;background:#111;color:#f87171">
        <h2>Portal HTML not found</h2>
        <p>Expected at: <code>{PORTAL_PATH}</code></p>
        <p>Make sure <b>incident-memory-portal.html</b> is in your project root:<br>
        <code>C:\\Users\\rajaramd\\projects\\coral-incident-memory\\incident-memory-portal.html</code></p>
        <p>The API is running fine — try <a href="/health" style="color:#7c6bff">/health</a> or 
        <a href="/docs" style="color:#7c6bff">/docs</a></p>
        </body></html>""",
        status_code=404
    )


# ─── MODELS ─────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    sql: str
    params: dict = {}

class AnalyzeRequest(BaseModel):
    rows: list
    query: str


# ─── HEALTH ─────────────────────────────────────────────────────
@app.get("/health")
async def health():
    coral_ok = check_coral()
    provider = detect_ai_provider()
    portal_ok = PORTAL_PATH.exists()
    return {
        "status": "ok",
        "coral": "connected" if coral_ok else "unavailable",
        "ai": provider,
        "portal": "found" if portal_ok else f"not found at {PORTAL_PATH}",
    }

def check_coral() -> bool:
    try:
        r = subprocess.run(["coral", "--version"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False

def detect_ai_provider() -> str:
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "local-fallback"


# ─── QUERY ──────────────────────────────────────────────────────
@app.post("/query")
async def run_query(req: QueryRequest):
    """Execute SQL via Coral and return rows as JSON."""
    sql = req.sql.strip()
    if not re.match(r"^\s*SELECT", sql, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")

    try:
        # Try JSON format
        result = subprocess.run(
            ["coral", "sql", "--format", "json", sql],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            # Fallback: plain output → parse table
            result = subprocess.run(
                ["coral", "sql", sql],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return {"rows": [], "count": 0, "error": result.stderr.strip(), "source": "coral"}
            rows = parse_table_output(result.stdout)
        else:
            raw = result.stdout.strip()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    rows = parsed
                elif isinstance(parsed, dict):
                    rows = parsed.get("rows", parsed.get("data", []))
                else:
                    rows = []
            except json.JSONDecodeError:
                rows = parse_table_output(raw)

        return {"rows": rows, "count": len(rows), "source": "coral"}

    except subprocess.TimeoutExpired:
        return {"rows": [], "count": 0, "error": "Coral query timed out", "source": "coral"}
    except FileNotFoundError:
        return {"rows": [], "count": 0, "error": "coral CLI not found on PATH", "source": "coral"}
    except Exception as e:
        return {"rows": [], "count": 0, "error": str(e), "source": "coral"}


def parse_table_output(output: str) -> list:
    """Parse coral ASCII table → list of dicts."""
    lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
    data_lines = [l for l in lines if not re.match(r"^[+\-]+$", l)]
    if len(data_lines) < 2:
        return []
    def split_row(line):
        return [p.strip() for p in line.strip("|").split("|") if p.strip() is not None]
    headers = split_row(data_lines[0])
    rows = []
    for line in data_lines[1:]:
        vals = split_row(line)
        if len(vals) == len(headers):
            rows.append(dict(zip(headers, vals)))
    return rows


# ─── ANALYZE ────────────────────────────────────────────────────
@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """AI-powered RCA summary from Coral rows."""
    provider = detect_ai_provider()

    if provider == "openai":
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert SRE assistant. Analyze past incident data "
                            "and give concise, actionable summaries in 2-3 sentences. "
                            "Bold key terms like service names, RCAs, and ticket IDs using **markdown**."
                        )
                    },
                    {"role": "user", "content": build_prompt(req.rows, req.query)}
                ],
                max_tokens=220,
                temperature=0.3,
            )
            return {"analysis": resp.choices[0].message.content, "provider": "openai"}
        except Exception:
            pass

    if provider == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=220,
                system=(
                    "You are an expert SRE assistant. Analyze past incident data and give concise, "
                    "actionable summaries in 2-3 sentences. Bold key terms using **markdown**."
                ),
                messages=[{"role": "user", "content": build_prompt(req.rows, req.query)}],
            )
            return {"analysis": msg.content[0].text, "provider": "anthropic"}
        except Exception:
            pass

    return {"analysis": build_local_summary(req.rows, req.query), "provider": "local"}


def build_prompt(rows: list, query: str) -> str:
    return (
        f"SRE engineer asked: '{query}'\n\n"
        f"Coral returned {len(rows)} past incident(s):\n{json.dumps(rows, indent=2)}\n\n"
        "Provide a 2-3 sentence SRE summary: Has this happened before? "
        "What was the root cause? What should the engineer check first? "
        "Bold service names, RCA phrases, and ticket IDs using **markdown**."
    )


def build_local_summary(rows: list, query: str) -> str:
    if not rows:
        return "No incidents found matching your query. This service may have a clean history — or try a broader search term."
    service = rows[0].get("service_name", "unknown")
    critical = sum(1 for r in rows if r.get("severity") == "critical")
    latest = rows[0]
    rcas = list(dict.fromkeys(r.get("rca", "") for r in rows if r.get("rca")))
    summary = f"Found **{len(rows)}** past incident(s) for **{service}**. "
    if critical:
        summary += f"**{critical} critical** — this service has a recurring severity pattern. "
    summary += (
        f"Most recent: **{latest.get('summary')}** ({latest.get('started_at','')[:10]}) "
        f"— ticket **{latest.get('ticket_key')}**. "
    )
    if rcas:
        summary += f"Root cause(s): **{'; '.join(rcas[:2])}**."
    return summary


# ─── SOURCES ────────────────────────────────────────────────────
@app.get("/sources")
async def list_sources():
    try:
        r = subprocess.run(["coral", "source", "list"], capture_output=True, text=True, timeout=10)
        return {"output": r.stdout, "error": r.stderr}
    except Exception as e:
        return {"output": "", "error": str(e)}
