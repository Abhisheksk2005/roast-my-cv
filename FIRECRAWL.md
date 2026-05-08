# Firecrawl — Setup & Usage Guide

Firecrawl powers the real-time web search in both the **Degree Roast** and **Internship Roast** pipelines. It searches for live company hiring bars, salary data, and market signals so the roast is backed by actual current data — not hallucinated numbers.

---

## 1. Get Your API Key

Create a free account at [firecrawl.dev](https://www.firecrawl.dev/signin?view=signup) and copy your API key from the dashboard.

Add it to `backend/.env`:

```dotenv
FIRECRAWL_API_KEY=fc-your-key-here
```

---

## 2. How It's Used in This Project

### Internship Roast (`internship_research_service.py`)

For each target company the student enters, Firecrawl runs **3–4 parallel search queries**:

```
"Google internship requirements skills India 2025"
"Google software intern GPA CGPA hiring bar reddit"
"Google internship what they look for linkedin"
"Google intern interview process skills required"
```

It also searches for market context about the student's major and skills. All results are fed into Groq (LLaMA 3.3-70B) which generates the per-company roast verdict.

### Degree Roast (`firecrawl_service.py` + `llm_service.py`)

Claude (Haiku) runs an **agentic search loop** — it decides its own queries, reads results, and submits structured salary/tuition/AI-risk analysis. Firecrawl handles each search call.

---

## 3. Key Settings (in `backend/.env`)

```dotenv
# Required
FIRECRAWL_API_KEY=fc-...

# Optional tuning (defaults shown)
FIRECRAWL_SEARCH_TIMEOUT_MS=15000    # per-query timeout
FIRECRAWL_RESULTS_PER_QUERY=3        # results returned per search (lower = cheaper)
RESEARCH_FIRECRAWL_SCRAPE=false      # full markdown scrape per result (richer but costs more credits)
RESEARCH_MAX_SEARCH_CALLS=6          # max searches Claude can run in agentic mode
RESEARCH_MAX_QUERIES=10              # max queries in fallback (non-agentic) mode
```

---

## 4. Endpoints Used

All calls go through the Python SDK (`firecrawl-py`):

```python
from firecrawl import FirecrawlApp

fc = FirecrawlApp(api_key="fc-...")

# Search — what the internship pipeline uses
results = fc.search(
    "Google SWE intern 2025 requirements",
    params={"limit": 3, "timeout": 15000}
)

# Each result has:
# result["data"][i]["markdown"]     ← clean extracted content
# result["data"][i]["description"]  ← short snippet
# result["data"][i]["url"]          ← source URL
# result["data"][i]["title"]        ← page title
```

---

## 5. Credit Usage Estimate

| Action | Credits |
|---|---|
| 1 search query (3 results, no scrape) | ~3 credits |
| 1 search query (3 results, with scrape) | ~6 credits |
| Full internship roast (3 companies) | ~30–50 credits |
| Full degree roast (agentic, 6 searches) | ~20–40 credits |

Free tier: **500 credits/month** — enough for ~10–15 full demo roasts.

---

## 6. What Happens If the Key Is Missing

If `FIRECRAWL_API_KEY` is not set or empty:

- The search step is **skipped silently**
- The roast still runs — Groq falls back to general knowledge
- Results are less accurate (no real company hiring bar data)
- You'll see `"No data found."` in the verdict reasons

For a demo, the roast will still work — it just won't have live web context.

---

## 7. Quick Test

With the server running, hit this to verify Firecrawl is connected:

```bash
curl -X POST http://localhost:8000/api/internship \
  -H "Content-Type: application/json" \
  -d '{
    "major": "Computer Science",
    "university": "NUS",
    "target_companies": ["Google"],
    "skills": ["Python", "React"],
    "cgpa": 3.8,
    "year_of_study": 3
  }'
```

If `search_queries` in the response is non-empty and `company_verdicts[0].reason` references real hiring info (not just generic text), Firecrawl is working.

---

## 8. Useful Links

- [Firecrawl Dashboard](https://www.firecrawl.dev/app) — monitor usage, credits, API keys
- [API Docs](https://docs.firecrawl.dev) — full endpoint reference
- [firecrawl-py SDK](https://github.com/mendableai/firecrawl/tree/main/apps/python-sdk) — Python SDK source
