"""
Internship Research Pipeline:
  1. Build search queries for each target company
  2. Search via Firecrawl for real hiring requirements
  3. Feed results + student profile to Claude
  4. Get back structured verdicts per company
"""

from __future__ import annotations

import asyncio
import json
import os

import structlog
from firecrawl import FirecrawlApp

from backend.models import CompanyVerdict, InternshipProfile, InternshipResearchResult, RecommendedCompany

logger = structlog.get_logger(__name__)

FIRECRAWL_SEARCH_TIMEOUT_MS = int(os.getenv("FIRECRAWL_SEARCH_TIMEOUT_MS", "15000"))


# ── Search ─────────────────────────────────────────────────────────────────────

def _build_company_queries(company: str, country: str = "") -> list[str]:
    """Build targeted search queries for one company's internship bar."""
    region = country or "global"
    return [
        f"{company} internship requirements skills {region} 2024 2025",
        f"{company} software intern GPA CGPA hiring bar reddit",
        f"{company} internship what they look for linkedin",
        f"{company} intern interview process skills required",
    ]


def _build_profile_queries(profile: InternshipProfile) -> list[str]:
    """Build queries to understand the market demand for the student's skills."""
    skills_str = ", ".join(profile.skills[:3]) if profile.skills else "programming"
    return [
        f"{profile.major} internship skills required {profile.country_or_region or 'global'} 2024",
        f"{skills_str} internship demand entry level 2024 2025",
    ]


async def _search_one(fc: FirecrawlApp, query: str) -> str:
    """Run one Firecrawl search and return joined snippets."""
    try:
        results = await asyncio.to_thread(
            fc.search,
            query,
            params={"limit": 3, "timeout": FIRECRAWL_SEARCH_TIMEOUT_MS},
        )
        snippets = []
        for r in (results.get("data") or []):
            text = (r.get("markdown") or r.get("description") or "").strip()
            if text:
                snippets.append(text[:600])
        return "\n---\n".join(snippets) if snippets else ""
    except Exception as e:
        logger.warning("firecrawl_search_failed", query=query[:60], error=str(e))
        return ""


# ── LLM Analysis ───────────────────────────────────────────────────────────────

def _build_analysis_prompt(
    profile: InternshipProfile,
    company_snippets: dict[str, str],
    profile_snippets: str,
) -> str:
    """Build the roast prompt — savage, funny, culturally aware, data-backed, appreciates wins."""
    skills_str = ", ".join(profile.skills) if profile.skills else "none listed"
    courses_str = ", ".join(profile.courses) if profile.courses else "none listed"
    companies_str = ", ".join(profile.target_companies)
    cgpa_line = f"{profile.cgpa}" if profile.cgpa else "not provided (sus)"
    exp_line = profile.experience or "nothing — the blank slate arc"
    year_line = f"Year {profile.year_of_study}" if profile.year_of_study else "year unknown"

    snippet_sections = ""
    for company, snippets in company_snippets.items():
        snippet_sections += f"\n\n### {company} — real hiring signals:\n{snippets or 'No data found — assume bar is high.'}"

    return f"""You are Donald — the internet's most culturally-aware, savagely funny, but genuinely helpful internship roast host.

You are part Gordon Ramsay, part LinkedIn Top Voice who went viral for all the wrong reasons, part that one senior engineer who actually tells you the truth. You roast hard, but you ALSO spot and celebrate real strengths — because every CV has something good, and ignoring it would make you just another hater.

## TONE RULES (non-negotiable)
1. **Reference actual CV details** — if they listed React, call it out. If their experience says "built a to-do app", roast the to-do app specifically. Generic roasts are lazy. Lazy is bad.
2. **Spot and hype the genuine wins** — did they have a decent CGPA? Hype it. Good tech stack? Credit it. Relevant experience? Respect it — then pivot to the gap. Format: "okay [good thing] understood the assignment... but [gap]."
3. **Use current cultural references** — pick from: "delulu", "it's giving [X] energy", "understood the assignment", "no cap", "NPC behavior", "main character arc", "vibe coding", "GPT-pilled their way through", "skill-issue speedrun", "the audacity", "not the [X] we needed", "ate and left no crumbs", "lowkey/highkey", "this ain't it chief", "the bar was on the floor and they...", "core memory unlocked", "chronically online", referencing LeetCode grind culture, hustle culture, AI tools, current tech trends. Use 2-3 per roast — don't overdo it.
4. **Be informative** — every joke must leave the student knowing exactly what to fix. Specificity > savagery.
5. **The voice_script is a performance** — write it like a 3-minute stand-up set being read by a confident AI voice. Short punchy sentences. Strategic pauses with "...". Build to a punchline for each company. End on something actionable but delivered with attitude.

## Student in the Hot Seat
- Major: {profile.major}
- University: {profile.university}
- CGPA: {cgpa_line}
- Year of Study: {year_line}
- Skills: {skills_str}
- Courses: {courses_str}
- Experience: {exp_line}
- Languages Known: {", ".join(profile.languages_known) if profile.languages_known else "not listed"}
- Country / Region: {profile.country_or_region or "not provided"}

## Their Target Companies
{companies_str}

## Real Market Data (back your burns with this)
{profile_snippets or "No market data — roast from general knowledge."}
{snippet_sections}

## Scoring Guide
- 0-25: "They applied to Google from Minecraft." Full delulu arc.
- 26-45: Reach energy. High hopes, thin resume. The audacity is real.
- 46-65: Mid but fixable. Main character potential, side character execution.
- 66-80: Legitimate candidate. Don't tell them too early — they'll get complacent.
- 81-100: Actually ate. Roast them for being here instead of already interning.

## Required Output Structure
For EACH target company:
- verdict: exactly one of "Realistic", "Reach", or "Be honest with yourself"
- reason: 1-2 sentences. Reference REAL hiring bar data. Reference something SPECIFIC from their CV. Be funny, be accurate. Mention both a strength and the gap if possible.
- bright_spot: ONE thing from their CV that genuinely helps for this company. Format: "[specific skill/experience from CV] actually slaps for [company] because [real reason]." Keep it real — no participation trophies.
- skill_gaps: 2-3 specific gaps for THIS company
- one_fix: 1 urgent action. Phrase it like advice from a mentor who loves them but has no time for excuses.

Overall:
- overall_readiness_score: honest integer 0-100
- top_skill_gaps: 3-5 real recurring gaps
- bright_spots: 2-3 genuine strengths from their ACTUAL profile that are worth celebrating (reference specific skills/experience/CGPA from the CV)
- tips: exactly 3 tips. Start with a verb. Specific to THIS profile. Ordered by impact. Make them sting a little.
- honest_take: THE line. One sentence (two max). References their score + dream company + specific CV detail. The kind of thing you'd screenshot. Culturally aware. Lands like a punchline.
- voice_script: the full roast as a spoken performance. Under 400 words. Build it like:
  1. Cold open — score + honest_take delivered as a punchline
  2. Per company — verdict + one punchy line (reference CV detail + gap)
  3. One genuine hype moment from bright_spots (because good hosts give credit)
  4. Close — one actionable tip delivered with energy
  Write for a confident AI voice reading it aloud. Punchy sentences. Strategic "..." pauses. No markdown. No bullet points. Pure spoken text.
- recommended_companies: 6 companies the student should ACTUALLY apply to based on their real CV profile. NOT the ones they listed — these are YOUR honest recommendations. Mix: 2 reach, 3 target, 1 safety. Reference specific skills/CGPA/experience from their CV in the reason. Each reason max 12 words.

Respond ONLY with valid JSON:
{{
  "overall_readiness_score": <int 0-100>,
  "company_verdicts": [
    {{
      "company": "<name>",
      "verdict": "<Realistic|Reach|Be honest with yourself>",
      "reason": "<punchy, specific, references CV details and company bar>",
      "bright_spot": "<genuine win from their CV for this company>",
      "skill_gaps": ["<specific gap1>", "<specific gap2>"],
      "one_fix": "<urgent, specific, no-nonsense action>"
    }}
  ],
  "top_skill_gaps": ["<gap1>", "<gap2>", "<gap3>"],
  "bright_spots": ["<genuine win 1 from CV>", "<genuine win 2>"],
  "tips": ["<verb-led specific tip1>", "<tip2>", "<tip3>"],
  "honest_take": "<THE quotable roast line — references CV specifics>",
  "voice_script": "<spoken performance — under 400 words, punchy, for ElevenLabs TTS>",
  "recommended_companies": [
    {{"name": "<company>", "tier": "<reach|target|safety>", "reason": "<why based on their actual CV, max 12 words>"}},
    ...
  ]
}}"""


async def _analyze_with_grok(prompt: str) -> dict | None:
    """Send the prompt to Groq and parse the JSON response."""
    model = (os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b").strip()
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )

        kwargs = {
            "model": model,
            # This prompt asks for verdicts + a ~400 word voice_script + 6 company
            # recommendations. That is well over 2000 tokens of JSON on its own, and on
            # reasoning models the thinking tokens come out of the same budget.
            "max_tokens": int(os.getenv("GROQ_MAX_TOKENS", "8000")),
            "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        # gpt-oss reasons before answering; keep the budget on the answer.
        if "gpt-oss" in model:
            kwargs["reasoning_effort"] = "low"

        response = await asyncio.to_thread(client.chat.completions.create, **kwargs)
        choice = response.choices[0]
        raw = (choice.message.content or "").strip()
        if not raw:
            logger.error(
                "grok_empty_content",
                model=model,
                finish_reason=getattr(choice, "finish_reason", None),
            )
            return None

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()
        # Reasoning models can prepend prose before the JSON object.
        if not raw.startswith("{"):
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end > start:
                raw = raw[start:end + 1]
        return json.loads(raw)
    except Exception as e:
        logger.error(
            "grok_analysis_failed",
            model=model,
            error_type=type(e).__name__,
            error=str(e)[:500],
        )
        return None


# ── Main Entry Point ────────────────────────────────────────────────────────────

async def run_internship_research(profile: InternshipProfile) -> dict:
    """
    Full internship research pipeline.
    1. Build queries for each company + profile
    2. Search via Firecrawl in parallel
    3. Analyse with Groq
    4. Return structured result dict
    """
    fc_key = os.getenv("FIRECRAWL_API_KEY", "")
    fc = FirecrawlApp(api_key=fc_key) if fc_key else None

    all_queries: list[str] = []

    # Build and run company searches
    company_snippets: dict[str, str] = {}
    for company in profile.target_companies:
        queries = _build_company_queries(company, profile.country_or_region)
        all_queries.extend(queries)
        if fc:
            results = await asyncio.gather(*[_search_one(fc, q) for q in queries])
            company_snippets[company] = "\n---\n".join(r for r in results if r)
        else:
            company_snippets[company] = ""

    # Build and run profile searches
    profile_queries = _build_profile_queries(profile)
    all_queries.extend(profile_queries)
    if fc:
        profile_results = await asyncio.gather(*[_search_one(fc, q) for q in profile_queries])
        profile_snippets = "\n---\n".join(r for r in profile_results if r)
    else:
        profile_snippets = ""

    # Analyse with Groq
    prompt = _build_analysis_prompt(profile, company_snippets, profile_snippets)
    analysis = await _analyze_with_grok(prompt)

    if not analysis:
        return InternshipResearchResult(
            overall_readiness_score=0,
            company_verdicts=[
                CompanyVerdict(
                    company=c,
                    verdict="Reach",
                    reason="Research unavailable — please try again.",
                    skill_gaps=[],
                    one_fix="Retry the research.",
                )
                for c in profile.target_companies
            ],
            top_skill_gaps=[],
            tips=["Try again with a better connection."],
            honest_take="Research failed — Donald can't roast without data.",
            search_queries=all_queries,
        ).model_dump()

    verdicts = [
        CompanyVerdict(
            company=v.get("company", ""),
            verdict=v.get("verdict", "Reach"),
            reason=v.get("reason", ""),
            bright_spot=v.get("bright_spot", ""),
            skill_gaps=v.get("skill_gaps", []),
            one_fix=v.get("one_fix", ""),
        )
        for v in analysis.get("company_verdicts", [])
    ]

    recommended = [
        RecommendedCompany(
            name=r.get("name", ""),
            tier=r.get("tier", "target"),
            reason=r.get("reason", ""),
        )
        for r in analysis.get("recommended_companies", [])
    ]

    return InternshipResearchResult(
        overall_readiness_score=int(analysis.get("overall_readiness_score", 0)),
        company_verdicts=verdicts,
        top_skill_gaps=analysis.get("top_skill_gaps", []),
        bright_spots=analysis.get("bright_spots", []),
        tips=analysis.get("tips", []),
        honest_take=analysis.get("honest_take", ""),
        voice_script=analysis.get("voice_script", ""),
        search_queries=all_queries,
        recommended_companies=recommended,
    ).model_dump()
