# HireMe or Fire Me 🎙

> The AI that tells you what recruiters won't.  
> Real data. Brutal honesty. Voice verdict.

**Live demo → [hireme.cybersartoria.it](https://hireme.cybersartoria.it)**

Built for [#ElevenHacks](https://elevenlabs.io/hackathon) — Hack #1: Firecrawl + ElevenAgents

---

Most candidates send applications blind. They research the company for 10 minutes on LinkedIn, write a cover letter full of what they think the recruiter wants to hear, and wait. They find out they were wrong three weeks later with a rejection email that says "we decided to move forward with other candidates."

**HireMe or Fire Me** is a voice-native AI judge that evaluates your fit for a role using live company data — before you apply. You describe yourself and the role you want. It searches the actual web right now for employee reviews, Glassdoor data, recent company news, and layoff history — then delivers a HIRED or FIRED verdict out loud, with the reasoning you weren't going to hear anywhere else.

Not a career coach. Not a resume optimizer. A verdict.

---

## Demo

Go to **[hireme.cybersartoria.it](https://hireme.cybersartoria.it)**

1. Paste your LinkedIn summary or describe your background
2. Enter the company and role you're targeting
3. Click **Load Context** — Firecrawl searches the live web in real time
4. Click **Start a Call** — hear your verdict out loud

The stamp updates in real time: **HIRED** or **FIRED**.

---

## How the search works

Firecrawl Search is wired directly into ElevenAgents as a webhook, called live on every session.

Three parallel queries run on every evaluation:

```
1. {company} company culture values employee reviews
2. {company} Glassdoor reviews pros cons 2024 2025
3. {company} layoffs news funding problems (last 30 days)
```

The results become the dossier the agent argues from. The judge doesn't speculate — it cites what it found, right now, from the actual web.

This is the specific use case where live search changes the outcome. A generic AI can say "Stripe has a tough culture." The moment it pulls a real Glassdoor review from last month and reads it back to you out loud, there's no dismissing it.

---

## Architecture

```
User fills profile + company + role
        │
        ▼
Frontend → POST /api/evaluate (FastAPI)
        │
        ▼
3 × Firecrawl /v2/search in parallel (asyncio.gather)
  ├── culture & values
  ├── employee reviews
  └── recent news
        │
        ▼
Dossier injected into ElevenAgents session via firstMessage override
        │
        ▼
ElevenAgents delivers HIRED / FIRED verdict by voice
        │
        ▼
JS parses transcript → visual stamp updates in real time
```

No database. No auth. No bloat. The backend is 110 lines of Python.

---

## Why ElevenAgents + Firecrawl

**ElevenAgents** handles STT → LLM → TTS + turn-taking in one platform. The verdict lands differently when it's spoken. Text on a screen is easy to dismiss. A voice saying "FIRED — your AWS cert doesn't compensate for zero distributed systems experience at this scale" is not.

**Firecrawl Search** returns full page content, not snippets. The agent gets real markdown from Glassdoor, Reddit threads, and news articles. That's the difference between "reviews are mixed" and reading you a specific complaint from three months ago.

Together: a voice agent that argues from evidence, not opinion.

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| Voice Agent | [ElevenAgents](https://elevenlabs.io/docs/eleven-agents/overview) |
| Live Web Search | [Firecrawl /v2/search](https://docs.firecrawl.dev/api-reference/endpoint/search) |
| Backend | Python 3.10 / FastAPI / httpx async |
| Frontend | Single HTML file — brutalist tabloid aesthetic |
| Deploy | nginx + systemd + Let's Encrypt |

---

## Setup

```bash
git clone https://gitlab.com/myfoxx/hireme-or-fire-me
cd hireme-or-fire-me

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add FIRECRAWL_API_KEY

uvicorn main:app --reload --port 8000
```

Test:

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_profile": "5 years Python backend, AWS certified, ex-startup CTO",
    "target_company": "Stripe",
    "target_role": "Senior Software Engineer"
  }'
```

Real Stripe data back in ~3 seconds.

### ElevenLabs agent config

System prompt:

```
You are The Judge — brutally honest career evaluator.
Gordon Ramsay + senior recruiter. No sugarcoating.

ALWAYS call evaluate_candidate before any verdict.

After the dossier:
1. One key fact from live data (no invention)
2. Top strength and weakness for this role
3. Say HIRED or FIRED clearly
4. One actionable fix

Under 60 seconds. Direct. Memorable.
```

Server tool `evaluate_candidate`:
- URL: `https://your-domain/api/evaluate`
- Method: POST
- Params: `candidate_profile`, `target_company`, `target_role`

Enable System prompt + First message overrides in Security settings.

Set your Agent ID in `index.html`:
```javascript
const AGENT_ID = 'your-agent-id-here';
```

---

## Files

```
hireme-or-fire-me/
├── main.py          # FastAPI backend
├── index.html       # Entire frontend — single file
├── requirements.txt
├── hireme.service   # systemd unit
├── .env.example
└── README.md
```

---

Built in one night for #ElevenHacks.

*[@firecrawl](https://x.com/firecrawl) · [@elevenlabs](https://x.com/elevenlabs) · #ElevenHacks*
