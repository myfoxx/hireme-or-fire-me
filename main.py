import os
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HireMe or Fire Me — Webhook Middleware")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
FIRECRAWL_URL = "https://api.firecrawl.dev/v2/search"


async def fc_search(query: str, limit: int = 3, tbs: str = "qdr:y") -> list[dict]:
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "limit": limit,
        "tbs": tbs,
        "scrapeOptions": {
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            r = await client.post(FIRECRAWL_URL, json=payload, headers=headers)
            if r.status_code != 200:
                logger.error(f"Firecrawl {r.status_code}: {r.text[:200]}")
                return []
            raw = r.json()
            logger.info(f"Firecrawl raw keys: {list(raw.keys())}")
            data_raw = raw.get("data", {})
            data = data_raw.get("web", []) if isinstance(data_raw, dict) else data_raw
            results = [item for item in data if isinstance(item, dict)]
            logger.info(f"Parsed {len(results)} results for: {query[:60]}")
            return results
    except Exception as e:
        logger.error(f"Firecrawl error: {e}")
        return []

def extract_text(results: list[dict], max_chars: int = 500) -> str:
    parts = []
    seen = set()
    for r in results:
        url = r.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        title = r.get("title", "")
        md = r.get("markdown", "") or r.get("description", "")
        lines = [l.strip() for l in md.split("\n") if l.strip() and not l.startswith("#")]
        snippet = " ".join(lines)[:max_chars]
        if snippet:
            parts.append(f"{title}: {snippet}")
    return "\n\n".join(parts) if parts else "No data found."


@app.post("/evaluate")
async def evaluate(request: Request):
    """
    ElevenAgents server tool endpoint.
    Body (agent sends these after extracting from conversation context):
      {
        "candidate_profile": "...",   # what the user pasted / described
        "target_company": "...",      # company name
        "target_role": "..."          # job role
      }
    Returns a dossier for the agent to use in its HIRED/FIRED verdict.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    candidate = body.get("candidate_profile", "").strip()
    company   = body.get("target_company", "").strip()
    role      = body.get("target_role", "").strip()

    if not company:
        return JSONResponse({"error": "target_company is required"}, status_code=400)

    logger.info(f"Evaluating: role='{role}' at company='{company}'")

    # Run 3 Firecrawl searches in parallel
    queries = [
        (f"{company} company culture values employee reviews", 3, "qdr:y"),
        (f"{company} Glassdoor reviews pros cons 2024 2025", 3, "qdr:y"),
        (f"{company} layoffs news funding problems 2024 2025", 3, "qdr:m"),
    ]
    tasks = [fc_search(q, limit=lim, tbs=tbs) for q, lim, tbs in queries]
    results = await asyncio.gather(*tasks)

    culture_text = extract_text(results[0], 400)
    glassdoor_text = extract_text(results[1], 400)
    news_text = extract_text(results[2], 300)

    # Build dossier for agent
    dossier = f"""
COMPANY DOSSIER: {company}
ROLE APPLIED FOR: {role or 'unspecified'}

--- CULTURE & VALUES (live web data) ---
{culture_text}

--- EMPLOYEE REVIEWS (Glassdoor & similar) ---
{glassdoor_text}

--- RECENT NEWS (last 6 months) ---
{news_text}

--- CANDIDATE PROFILE ---
{candidate or 'Not provided — assess based on company data only and ask for profile verbally.'}
""".strip()

    logger.info(f"Dossier built — {len(dossier)} chars")

    return JSONResponse({
        "dossier": dossier,
        "company": company,
        "role": role,
        "data_sources": 3,
    })


@app.get("/health")
async def health():
    return {"status": "ok", "firecrawl_configured": bool(FIRECRAWL_API_KEY)}
