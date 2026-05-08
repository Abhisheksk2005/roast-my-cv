"""
Claude-powered research: agentic search loop + one-shot extraction fallback.

Primary mode (agentic):
  Claude decides what to search via a web_search tool, runs searches through
  Firecrawl, reads the results, and submits structured analysis when satisfied.
  Searches within a single turn run in parallel; total searches are capped.

Fallback mode (one-shot):
  Pre-searched snippets are passed to Claude in a single call for extraction.
  Used when the agentic loop is unavailable or fails.
"""

from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass, field

import structlog
from datetime import datetime
from typing import Awaitable, Callable

import anthropic

from backend.services.money_locale import format_money_int, grad_timeline

logger = structlog.get_logger(__name__)
PROMPT_CACHING_BETA_HEADER = "prompt-caching-2024-07-31"

SearchFn = Callable[[str], Awaitable[dict]]

# ── Tool definitions ──────────────────────────────────────────────────────────

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for career, salary, tuition, job-market, or AI-automation data. "
        "Returns titles, URLs, and content snippets from top results. "
        "Be specific: include role/degree name, country, year, and source names "
        "(BLS, ONS, Glassdoor, Payscale, etc.)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Targeted search query.",
            },
        },
        "required": ["query"],
    },
}

ANALYSIS_TOOL = {
    "name": "submit_analysis",
    "description": "Submit the structured degree + career + financial + AI-risk analysis extracted from search results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "avg_salary_for_degree": {
                "type": ["integer", "null"],
                "description": "Average annual salary in the USER'S PRIMARY CURRENCY (see profile ISO code), major units only. Nationwide/regional per snippets. null if not found.",
            },
            "avg_salary_for_role": {
                "type": ["integer", "null"],
                "description": "Average annual salary in the user's primary currency for the current job title. null if not found.",
            },
            "median_salary_for_role": {
                "type": ["integer", "null"],
                "description": "Median annual salary in the user's primary currency for the current job title. null if not found.",
            },
            "salary_range_low": {
                "type": ["integer", "null"],
                "description": "Low end of salary range in the user's primary currency (e.g. entry level). null if not found.",
            },
            "salary_range_high": {
                "type": ["integer", "null"],
                "description": "High end of salary range in the user's primary currency (e.g. senior). null if not found.",
            },
            "estimated_tuition": {
                "type": ["integer", "null"],
                "description": "Estimated total degree tuition in the user's primary currency (e.g. 3–4 year total; include fees/room if bundled in snippets). UK: use course fees total if that's what sources give. null if not found.",
            },
            "sp500_annual_return_pct": {
                "type": ["number", "null"],
                "description": "Annualized total return (%) of the LOCAL broad equity benchmark from graduation year to present (e.g. S&P 500 US, FTSE 100 UK, STOXX/Europe for EU). Dividends reinvested if data says so. Snippets name the index — use that. null if not found.",
            },
            "degree_roi_rank": {
                "type": ["string", "null"],
                "description": "Degree ROI ranking as 'X/Y' if found, or null.",
            },
            "job_market_trend": {
                "type": "string",
                "enum": ["growing", "flat", "shrinking"],
                "description": "Overall job market trend for this role from snippet data (ONS, BLS, Eurostat, etc.).",
            },
            "unemployment_rate_pct": {
                "type": ["number", "null"],
                "description": "Unemployment rate (%) for this field or role if found in snippets. null otherwise.",
            },
            "job_openings_estimate": {
                "type": ["integer", "null"],
                "description": "Estimated annual job openings or projected growth (count) for this role from BLS or search data. null if not found.",
            },
            "lifetime_earnings_estimate": {
                "type": ["integer", "null"],
                "description": "Estimated lifetime earnings in the user's primary currency for this degree/role. null if not found in snippets.",
            },
            "degree_premium_over_hs": {
                "type": ["integer", "null"],
                "description": "Annual earnings premium in the user's primary currency vs secondary school leaver baseline in that country. null if not found.",
            },
            "ai_replacement_risk_0_100": {
                "type": "integer",
                "description": (
                    "AI/automation exposure for this role (0=safe, 100=fully automatable). "
                    "Be **harsh and pessimistic**: junior/assistant/associate layers, rules-heavy compliance, "
                    "templated writing, scheduling, data prep, first-pass review, and routine triage should score **high** (often 65–95). "
                    "Reserve low scores only for strong liability, physical presence, regulated sign-off, or rare expert judgment. "
                    "Factor seniority, task mix, and snippets."
                ),
            },
            "ai_risk_reasoning": {
                "type": "string",
                "description": "2–3 tight sentences on the AI risk score. Cite snippet evidence; say which tasks are exposed vs safer; optional timeline.",
            },
            "safeguard_tips": {
                "type": "array",
                "items": {"type": "string"},
                "description": "4–6 actionable, specific tips for THIS person to survive the AI wave. Order matters: put the highest-impact move FIRST, then next most important. Reference their exact job title, degree, experience level, and situation. No generic platitudes like 'learn to code'. Each tip is one concrete action they can take.",
            },
            "honest_take": {
                "type": "string",
                "description": "2–4 sentences. Use SPECIFIC market numbers in the correct local currency symbol (£ $ € …). Mention index opportunity cost using the benchmark from snippets (S&P, FTSE, etc.). NEVER mention self-reported salary. Be quotable.",
            },
            "source_orgs_mentioned": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Up to 5 org names in snippets (BLS, ONS, Glassdoor, Payscale, McKinsey, etc.). Empty array if none.",
            },
            "tasks": {
                "type": "array",
                "description": (
                    "REQUIRED: 5–8 weekly tasks. time_pct sums ~100. Per-task automation_score_0_100: **score harshly** — "
                    "routine desk work, playbooks, checklists, junior execution, and rules-based steps are usually **70–95**; "
                    "only score low (under ~45) for real hands-on, trust, liability, or messy human judgment. "
                    "timeline_horizon: when exposure hits. Server time-weights tasks + applies a pessimism bump — still set ai_replacement_risk_0_100 consistently."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Short label, e.g. 'Draft client emails'."},
                        "time_pct": {
                            "type": "integer",
                            "description": "Approximate % of workweek on this task (0–100) — all tasks should sum to ~100.",
                        },
                        "automation_score_0_100": {
                            "type": "integer",
                            "description": (
                                "0–100 for this task only. Err high for repetitive, rules-driven, or junior execution work; "
                                "low only for irreplaceable judgment, physical, or regulated accountability."
                            ),
                        },
                        "reasoning": {"type": "string", "description": "One sentence: why this score for this task."},
                        "timeline_horizon": {
                            "type": "string",
                            "enum": ["now", "1_2_years", "3_5_years", "longer"],
                            "description": "When AI could realistically take most of this task.",
                        },
                    },
                    "required": [
                        "task",
                        "time_pct",
                        "automation_score_0_100",
                        "reasoning",
                        "timeline_horizon",
                    ],
                },
            },
        },
        "required": [
            "avg_salary_for_degree",
            "avg_salary_for_role",
            "median_salary_for_role",
            "salary_range_low",
            "salary_range_high",
            "estimated_tuition",
            "sp500_annual_return_pct",
            "degree_roi_rank",
            "job_market_trend",
            "unemployment_rate_pct",
            "job_openings_estimate",
            "lifetime_earnings_estimate",
            "degree_premium_over_hs",
            "ai_replacement_risk_0_100",
            "ai_risk_reasoning",
            "safeguard_tips",
            "honest_take",
            "source_orgs_mentioned",
        ],
    },
}

# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class LLMAnalysis:
    avg_salary_for_degree: int | None
    avg_salary_for_role: int | None
    median_salary_for_role: int | None
    salary_range_low: int | None
    salary_range_high: int | None
    estimated_tuition: int | None
    sp500_annual_return_pct: float | None
    degree_roi_rank: str | None
    job_market_trend: str | None
    unemployment_rate_pct: float | None
    job_openings_estimate: int | None
    lifetime_earnings_estimate: int | None
    degree_premium_over_hs: int | None
    ai_replacement_risk_0_100: int
    ai_risk_reasoning: str
    safeguard_tips: list[str] = field(default_factory=list)
    honest_take: str = ""
    source_orgs_mentioned: list[str] = field(default_factory=list)
    job_tasks: list[dict] | None = None  # raw task rows from submit_analysis.tasks


@dataclass
class AgenticResult:
    """Output of the agentic research loop — analysis plus search metadata."""
    analysis: LLMAnalysis
    queries_used: list[str] = field(default_factory=list)
    hit_counts: list[int] = field(default_factory=list)
    raw_snippets: list[str] = field(default_factory=list)
    sources: list[tuple[str, str, str]] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_client() -> anthropic.Anthropic | None:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return None
    try:
        timeout_sec = float((os.getenv("ANTHROPIC_TIMEOUT_SEC") or "180").strip() or "180")
    except ValueError:
        timeout_sec = 180.0
    return anthropic.Anthropic(api_key=key, timeout=max(30.0, timeout_sec))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _max_search_calls() -> int:
    try:
        return max(2, min(10, int((os.getenv("RESEARCH_MAX_SEARCH_CALLS") or "6").strip())))
    except ValueError:
        return 6


def _parse_analysis_dict(d: dict) -> LLMAnalysis:
    raw_tasks = d.get("tasks")
    job_tasks: list[dict] | None = None
    if isinstance(raw_tasks, list) and raw_tasks:
        job_tasks = [t for t in raw_tasks if isinstance(t, dict)]
    return LLMAnalysis(
        avg_salary_for_degree=d.get("avg_salary_for_degree"),
        avg_salary_for_role=d.get("avg_salary_for_role"),
        median_salary_for_role=d.get("median_salary_for_role"),
        salary_range_low=d.get("salary_range_low"),
        salary_range_high=d.get("salary_range_high"),
        estimated_tuition=d.get("estimated_tuition"),
        sp500_annual_return_pct=d.get("sp500_annual_return_pct"),
        degree_roi_rank=d.get("degree_roi_rank"),
        job_market_trend=d.get("job_market_trend"),
        unemployment_rate_pct=d.get("unemployment_rate_pct"),
        job_openings_estimate=d.get("job_openings_estimate"),
        lifetime_earnings_estimate=d.get("lifetime_earnings_estimate"),
        degree_premium_over_hs=d.get("degree_premium_over_hs"),
        ai_replacement_risk_0_100=int(d.get("ai_replacement_risk_0_100", 50)),
        ai_risk_reasoning=d.get("ai_risk_reasoning", ""),
        safeguard_tips=d.get("safeguard_tips", []),
        honest_take=d.get("honest_take", ""),
        source_orgs_mentioned=list(d.get("source_orgs_mentioned") or []),
        job_tasks=job_tasks,
    )


# ── Agentic research ─────────────────────────────────────────────────────────

_AGENTIC_SYSTEM = """\
You are an expert career + financial analyst building a **maximally harsh** "degree roast" report card — sharp, quotable, uncomfortable truth. Punch up: weak ROI, automation exposure, and tuition pain. No sugarcoating.

You have two tools:
- **web_search** — search the web for real data. Be targeted and efficient.
- **submit_analysis** — submit your structured findings when you have enough data.

## What to find (priority order)
1. Average / median salary for the person's current role, in their local currency.
2. Average salary for their degree field.
3. Total tuition cost at their university.
4. Broad equity index returns (S&P 500, FTSE 100, STOXX 600, etc.) from their graduation year to present — record the annualized % in `sp500_annual_return_pct` regardless of which index.
5. Job market trend for their role (growing / flat / shrinking), unemployment rate, openings.
6. **Task decomposition for AI risk (required):** In `tasks`, list **5–8 concrete tasks** they actually do (not the job title). For each: `time_pct` (shares of week, sum ≈ 100), `automation_score_0_100` for **that task** (0=safe, 100=fully automatable today/near future), `timeline_horizon` (now / 1_2_years / 3_5_years / longer), and one-line `reasoning` citing judgment vs routine, tools already in market, regulation, physical presence, etc.
7. Degree ROI ranking, lifetime earnings, degree premium vs non-degree.

### AI risk rubric (per task) — **harsh / pessimistic**
- **Default skeptical of desk jobs:** junior, coordinator, assistant, analyst (early-career), and any role that mostly applies rules, templates, or playbooks → task scores are usually **high** (often 70–95 for the bulk of time).
- First drafts, email/slide prep, scheduling, data cleaning, ticket triage, simple coding glue, first-pass QA → **high**; these are already in-market for LLMs and agents.
- Physical world, personal liability, surgery-level accountability, regulated sign-off you cannot delegate, or genuinely novel negotiation with no playbook → **lower** scores — but do not give “safe” scores just because the title sounds senior; look at what they *do* hour by hour.
- If **years of experience** is low or unknown, assume more execution and less strategy → **higher** average automation.
- `timeline_horizon`: **now** / **1_2_years** when tools already exist; **longer** only when deployment friction is real (law, unions, trust, physical reality).

The backend **time-weights** `tasks` and applies a small pessimism calibration — still set `ai_replacement_risk_0_100` to match your task mix (same harsh mindset).

## Search guidelines
- Target 4–6 focused searches. Do not repeat overlapping queries.
- Include country/region, year, and data-source names (BLS, ONS, Glassdoor, Payscale, etc.).
- If a single search covers multiple topics, skip redundant queries.
- You may issue multiple web_search calls in one turn — they run in parallel.
- After gathering enough data, call submit_analysis immediately.

## Extraction rules
- ALL money integers must be in the user's PRIMARY CURRENCY, major units only (dollars not cents, pounds not pence).
- Extract from search results only — do not invent numbers. Use null when data is missing.
- If the profile lists a **user-reported total tuition** integer, `estimated_tuition` in submit_analysis **must equal that exact integer** (canonical). Still run web_search for published fees/tuition to inform honest_take and contrast.
- Self-reported salary is internal context only — NEVER put it in honest_take.
- For sp500_annual_return_pct: use the annualized total return for the benchmark named in the profile or found in search results. If you cannot find it, use a reasonable long-run nominal average for that market (~10–11% US, ~7–9% UK/EU).
- honest_take: 2–4 quotable sentences with correct currency symbols — **meaner and funnier** than a neutral analyst, but still factual. Mention tuition vs index opportunity cost when tuition data exists. If the user reported a tuition total, treat that as the real tuition story (still cite market context from search when useful). If user hasn't graduated yet, use forward-looking language.
- safeguard_tips: 4–6 specific, actionable tips for THIS person ordered by impact (highest first). Reference their exact role, degree, experience. No generic advice.
"""


def _build_agentic_user_message(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None,
    salary: int | None,
    *,
    country_or_region: str,
    currency_code: str,
    money_locale: str,
    equity_benchmark: str,
    max_searches: int,
    user_tuition_total: int | None = None,
) -> str:
    current_year = datetime.now().year
    _, years_since_grad = grad_timeline(graduation_year, current_year)
    if graduation_year <= 0 or graduation_year < 1950:
        grad_line = (
            "Graduation year: unknown — treat as current or prospective student; "
            "prioritize typical graduate salaries, tuition, and field outlook."
        )
    elif graduation_year > current_year:
        grad_line = (
            f"Expected graduation: {graduation_year} — NOT graduated yet. "
            "Frame honest_take for a student: typical outcomes, starting salary bands, "
            "whether the degree pays off on average."
        )
    else:
        grad_line = f"Graduated: {graduation_year} ({years_since_grad} years ago)"

    region_line = (country_or_region or "").strip() or "not specified"
    salary_line = format_money_int(salary, currency_code) if salary else "not disclosed"
    if user_tuition_total and user_tuition_total > 0:
        tuition_line = (
            f"{user_tuition_total} {currency_code} (user-reported total degree cost — **canonical** for submit_analysis `estimated_tuition`; "
            "still search the web for published fees/tuition as context and for honest_take contrast if it differs)"
        )
    else:
        tuition_line = "not provided — extract estimated total tuition/fees from search only"

    return (
        f"## Profile\n"
        f"Degree: {degree}\n"
        f"University: {university}\n"
        f"{grad_line}\n"
        f"Current job: {current_job}\n"
        f"Years of experience: {years_experience if years_experience is not None else 'unknown'}\n"
        f"Country / region: {region_line}\n"
        f"Primary currency (ISO 4217): {currency_code}\n"
        f"Self-reported salary: {salary_line}\n"
        f"User-reported tuition (total): {tuition_line}\n"
        f"Search locale: {money_locale}\n"
        f"Equity benchmark: {equity_benchmark}\n\n"
        f"Search strategically — you have at most {max_searches} web_search calls. Go."
    )


def _format_search_results(raw: dict, query: str) -> str:
    items = raw.get("data", [])
    if not items:
        return f"No results found for: {query}"
    parts: list[str] = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "")
        url = item.get("url", "")
        md = (item.get("markdown") or "")[:600]
        header = f"[{i}]"
        if title:
            header += f" {title}"
        if url:
            header += f"\n    {url}"
        if md.strip():
            parts.append(f"{header}\n{md}")
        else:
            parts.append(header)
    return "\n\n".join(parts)


async def agentic_research(
    search_fn: SearchFn,
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None = None,
    salary: int | None = None,
    *,
    country_or_region: str = "",
    currency_code: str = "USD",
    money_locale: str = "US",
    equity_benchmark: str = "S&P 500",
    user_tuition_total: int | None = None,
) -> AgenticResult | None:
    """
    Claude-driven research loop.  Claude picks search queries, reads results,
    and submits structured analysis.  Multiple searches in one turn run in parallel.
    Returns None if Anthropic is unavailable or the loop fails.
    """
    client = _get_client()
    if client is None:
        return None

    max_searches = _max_search_calls()
    model = (os.getenv("ANTHROPIC_ANALYSIS_MODEL") or "claude-haiku-4-5").strip()
    use_cache = _env_bool("ANTHROPIC_PROMPT_CACHING", True)

    system_text = _AGENTIC_SYSTEM.strip()
    if use_cache:
        system_payload: str | list = [
            {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}},
        ]
    else:
        system_payload = system_text

    user_msg = _build_agentic_user_message(
        degree, university, graduation_year, current_job,
        years_experience, salary,
        country_or_region=country_or_region,
        currency_code=currency_code,
        money_locale=money_locale,
        equity_benchmark=equity_benchmark,
        max_searches=max_searches,
        user_tuition_total=user_tuition_total,
    )

    messages: list[dict] = [{"role": "user", "content": user_msg}]
    tools = [WEB_SEARCH_TOOL, ANALYSIS_TOOL]

    queries_used: list[str] = []
    hit_counts: list[int] = []
    raw_snippets: list[str] = []
    all_sources: list[tuple[str, str, str]] = []
    search_count = 0

    extra_headers = {"anthropic-beta": PROMPT_CACHING_BETA_HEADER} if use_cache else {}

    for _round in range(max_searches + 3):
        tool_choice: dict
        if search_count >= max_searches:
            tool_choice = {"type": "tool", "name": "submit_analysis"}
        else:
            tool_choice = {"type": "any"}

        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model=model,
                system=system_payload,
                max_tokens=3000,
                tools=tools,
                tool_choice=tool_choice,
                messages=messages,
                **({"extra_headers": extra_headers} if extra_headers else {}),
            )
        except Exception:
            logger.exception("Agentic research: Claude call failed on round %d", _round)
            return None

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # Scan for tool_use blocks
        search_blocks: list[anthropic.types.ToolUseBlock] = []
        analysis_input: dict | None = None
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            if block.name == "submit_analysis":
                analysis_input = block.input
            elif block.name == "web_search":
                search_blocks.append(block)

        if analysis_input is not None:
            return AgenticResult(
                analysis=_parse_analysis_dict(analysis_input),
                queries_used=queries_used,
                hit_counts=hit_counts,
                raw_snippets=raw_snippets,
                sources=all_sources,
            )

        if not search_blocks:
            logger.warning("Agentic round %d: no tool calls and no submit — breaking", _round)
            break

        # Run all search calls in this turn in parallel
        async def _run_one(block: anthropic.types.ToolUseBlock) -> tuple[str, str, dict]:
            q = (block.input or {}).get("query", "")
            result = await search_fn(q)
            return block.id, q, result

        completed = await asyncio.gather(*[_run_one(sb) for sb in search_blocks])

        tool_results: list[dict] = []
        for tool_id, query, raw in completed:
            queries_used.append(query)
            search_count += 1

            hits = sum(1 for item in raw.get("data", []) if item.get("markdown"))
            hit_counts.append(hits)

            for item in raw.get("data", []):
                url = (item.get("url") or "").strip()
                title = (item.get("title") or "").strip()
                if url or title:
                    all_sources.append((url, title, query))
                md = (item.get("markdown") or "").strip()
                if md:
                    raw_snippets.append(md[:600])

            formatted = _format_search_results(raw, query)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": formatted,
            })

        messages.append({"role": "user", "content": tool_results})

    logger.warning("Agentic research loop exhausted without submit_analysis")
    return None


# ── Legacy one-shot extraction (fallback) ─────────────────────────────────────


def _build_anthropic_messages(prompt: str, use_prompt_cache: bool) -> list[dict]:
    if not use_prompt_cache:
        return [{"role": "user", "content": prompt}]
    return [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}],
        }
    ]


def _build_prompt(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None,
    salary: int | None,
    snippets_by_query: list[tuple[str, str]],
    *,
    country_or_region: str,
    currency_code: str,
    money_locale: str,
    equity_benchmark: str,
    user_tuition_total: int | None = None,
) -> str:
    current_year = datetime.now().year
    _, years_since_grad = grad_timeline(graduation_year, current_year)
    if graduation_year <= 0 or graduation_year < 1950:
        grad_line = (
            "Graduation year: unknown — treat as current or prospective student; "
            "prioritize typical graduate salaries, tuition, and field outlook."
        )
    elif graduation_year > current_year:
        grad_line = (
            f"Expected graduation: {graduation_year} — NOT graduated yet. "
            "Frame honest_take for someone still in school or applying: typical outcomes, "
            "starting salary bands, whether the degree pays off on average — not 'your last decade in the workforce'."
        )
    else:
        grad_line = f"Graduated: {graduation_year} ({years_since_grad} years ago)"

    region_line = (country_or_region or "").strip() or "not specified"
    salary_line = f"Self-reported salary ({currency_code}): {format_money_int(salary, currency_code)}"
    if user_tuition_total and user_tuition_total > 0:
        tuition_profile = (
            f"User-reported total tuition ({currency_code}): {user_tuition_total} — use this EXACT integer as "
            f"`estimated_tuition` in submit_analysis (canonical). Still extract/compare published fees from snippets for honest_take.\n"
        )
    else:
        tuition_profile = "User-reported tuition: not provided — estimate total tuition from snippets only.\n"

    profile_block = (
        f"Degree: {degree}\n"
        f"University: {university}\n"
        f"{grad_line}\n"
        f"Current job / situation: {current_job}\n"
        f"Years of experience: {years_experience if years_experience is not None else 'unknown'}\n"
        f"Country / region (user or agent): {region_line}\n"
        f"PRIMARY CURRENCY (ISO 4217): {currency_code} — ALL extracted money integers MUST be in this currency, major units only (pounds not pence, dollars not cents).\n"
        f"{salary_line}\n"
        f"{tuition_profile}"
        f"Search locale bucket: {money_locale} — prefer local sources (e.g. ONS/Reed for UK, BLS for US).\n"
        f"Equity benchmark for opportunity-cost narrative: {equity_benchmark} (use snippets; field name in tool is still sp500_annual_return_pct).\n"
    )

    snippet_block = ""
    for query, text in snippets_by_query:
        if text.strip():
            snippet_block += f"\n--- Search: \"{query}\" ---\n{text[:1200]}\n"

    index_rule = (
        f"- For sp500_annual_return_pct: use annualized total return for {equity_benchmark} (or the index named in snippets). "
        "If missing, use a reasonable long-run nominal average for that market (~10–11% for US large-cap; ~7–9% for FTSE-style UK unless snippets disagree).\n"
    )

    return (
        "You are an expert career + financial analyst building a brutally honest 'degree roast' report card.\n"
        "You have a user's profile and search snippets from the web. Your job is to extract every useful number\n"
        "and produce sharp analysis a comedian can riff on.\n\n"
        f"## User profile\n{profile_block}\n"
        f"## Search snippets\n{snippet_block}\n\n"
        "## Instructions\n\n"
        "### Financial extraction\n"
        "1. Extract salaries in the PRIMARY CURRENCY: average for the degree field, average for the role, median, "
        "and range (low/high). Prefer region-appropriate sources (ONS, Reed, Glassdoor UK for UK; BLS, Glassdoor US for US).\n"
        "2. Extract total degree tuition/fees in the PRIMARY CURRENCY (e.g. 3–4 year total UK; US COA if given). "
        "If only annual fees exist, estimate total typical degree length.\n"
        f"3. Extract annualized return for {equity_benchmark} (tool field sp500_annual_return_pct) from snippets when possible.\n"
        "4. Lifetime earnings and degree premium: same currency as profile.\n"
        "5. Unemployment / job openings from local statistics if present.\n\n"
        "### AI & career analysis\n"
        "6. **tasks** (required): 5–8 weekly tasks; time_pct ~100; per-task automation_score_0_100 — **score harshly**: "
        "rules-heavy, junior execution, templates, triage, and routine desk work → high scores (often 70–95); "
        "only low scores for real liability, physical, or irreplaceable judgment. timeline_horizon as in the tool. "
        "Server time-weights tasks + pessimism calibration.\n"
        "7. Safeguard tips: 4–6 specific actions for this person.\n\n"
        "### Honest take\n"
        "8. 2–4 sentences with correct currency symbols (£ $ € …) matching PRIMARY CURRENCY. "
        "Tone: **harsher roast energy** — punchy and quotable, not dry. "
        "Reference market averages only — NEVER self-reported salary. "
        f"Mention tuition vs \"if that went into {equity_benchmark}\" style opportunity cost when tuition exists. "
        "If they are NOT graduated yet, use forward-looking language (typical starting pay, whether the field is heating up, "
        "tuition vs alternatives) — do not imply they already finished the degree unless grad year is in the past.\n\n"
        "### Sources\n"
        "9. source_orgs_mentioned: up to 5 names from snippets.\n\n"
        "### Rules\n"
        "- Extract FROM SNIPPETS; null if unclear — do not invent salary/tuition.\n"
        f"{index_rule}"
        "- Self-reported salary is context for your internal comparison only — not in honest_take.\n\n"
        "Call the submit_analysis tool with your results."
    )


def _parse_tool_response(message: anthropic.types.Message) -> LLMAnalysis | None:
    for block in message.content:
        if block.type == "tool_use" and block.name == "submit_analysis":
            return _parse_analysis_dict(block.input)
    return None


async def analyze_with_llm(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None,
    salary: int | None,
    queries: list[str],
    snippets_per_query: list[str],
    *,
    country_or_region: str = "",
    currency_code: str = "USD",
    money_locale: str = "US",
    equity_benchmark: str = "S&P 500",
    user_tuition_total: int | None = None,
) -> LLMAnalysis | None:
    client = _get_client()
    if client is None:
        return None

    pairs = list(zip(queries, snippets_per_query))
    prompt = _build_prompt(
        degree,
        university,
        graduation_year,
        current_job,
        years_experience,
        salary,
        pairs,
        country_or_region=country_or_region,
        currency_code=currency_code,
        money_locale=money_locale,
        equity_benchmark=equity_benchmark,
        user_tuition_total=user_tuition_total,
    )

    model = (os.getenv("ANTHROPIC_ANALYSIS_MODEL") or "claude-haiku-4-5").strip()
    use_prompt_cache = _env_bool("ANTHROPIC_PROMPT_CACHING", True)
    message_payload = _build_anthropic_messages(prompt, use_prompt_cache)
    try:
        request_kwargs = dict(
            model=model,
            max_tokens=2600,
            tools=[ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "submit_analysis"},
            messages=message_payload,
        )
        if use_prompt_cache:
            request_kwargs["extra_headers"] = {"anthropic-beta": PROMPT_CACHING_BETA_HEADER}
        try:
            response = await asyncio.to_thread(client.messages.create, **request_kwargs)
        except Exception:
            if not use_prompt_cache:
                raise
            logger.warning("Anthropic prompt caching request failed; retrying without cache headers.")
            response = await asyncio.to_thread(
                client.messages.create,
                model=model,
                max_tokens=2600,
                tools=[ANALYSIS_TOOL],
                tool_choice={"type": "tool", "name": "submit_analysis"},
                messages=[{"role": "user", "content": prompt}],
            )
        return _parse_tool_response(response)
    except Exception:
        logger.exception("Claude one-shot analysis failed")
        return None
