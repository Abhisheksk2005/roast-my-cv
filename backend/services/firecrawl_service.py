"""
Research pipeline (Claude-first):
  1. Agentic loop: Claude decides what to search and submits structured analysis.
  2. Fallback: parallel Firecrawl search + one-shot Claude extraction.
  3. No heuristic scoring/extraction fallback.
"""

from __future__ import annotations

import os
import re
import asyncio
from datetime import datetime

import structlog
from urllib.parse import urlparse

from firecrawl import FirecrawlApp

from backend.models import ResearchData, ResearchSource
from backend.services.llm_service import (
    AgenticResult,
    LLMAnalysis,
    agentic_research,
    analyze_with_llm,
)
from backend.services.money_locale import (
    coerced_currency_from_region,
    equity_benchmark_label,
    grad_timeline,
    index_anchor_year,
    money_locale,
)
from backend.services.ai_job_model import (
    compute_career_market_stress_0_100,
    compute_financial_roi_stress_0_100,
    compute_overall_cooked_from_components,
    financial_opportunity_gap,
    resolve_ai_replacement_from_llm,
)

logger = structlog.get_logger(__name__)

# Historical S&P 500 annualized total returns (nominal, dividends reinvested) by start-year decade.
# Used as fallback when snippets/LLM don't provide a number.
_SP500_FALLBACK_RETURNS: dict[int, float] = {
    2024: 11.0,
    2023: 12.5,
    2022: 10.0,
    2021: 9.5,
    2020: 14.0,
    2019: 13.5,
    2018: 12.0,
    2017: 12.5,
    2016: 13.0,
    2015: 12.0,
    2014: 11.5,
    2013: 12.0,
    2012: 13.0,
    2011: 12.5,
    2010: 13.0,
    2009: 14.5,
    2008: 11.0,
    2007: 10.0,
    2006: 10.5,
    2005: 10.5,
}
_SP500_DEFAULT_RETURN = 10.5


def _sp500_fallback(graduation_year: int) -> float:
    return _SP500_FALLBACK_RETURNS.get(graduation_year, _SP500_DEFAULT_RETURN)


def _compound_growth(principal: int, annual_return_pct: float, years: int) -> int:
    return int(principal * ((1 + annual_return_pct / 100) ** years))


def _get_firecrawl() -> FirecrawlApp | None:
    key = (os.getenv("FIRECRAWL_API_KEY") or "").strip()
    if not key:
        return None
    http_timeout = float((os.getenv("FIRECRAWL_HTTP_TIMEOUT_SEC") or "75").strip() or "75")
    return FirecrawlApp(api_key=key, timeout=http_timeout)


def _search_result_text(item: object) -> str:
    md = getattr(item, "markdown", None)
    if md:
        return str(md)
    parts: list[str] = []
    for attr in ("title", "description", "snippet"):
        v = getattr(item, attr, None)
        if v:
            parts.append(str(v))
    return " ".join(parts)


def _search_item_url_title(item: object) -> tuple[str, str]:
    url = ""
    title = ""
    u = getattr(item, "url", None)
    if u:
        url = str(u).strip()
    t = getattr(item, "title", None)
    if t:
        title = str(t).strip()
    md = getattr(item, "metadata", None)
    if md is not None:
        mu = getattr(md, "url", None) or getattr(md, "source_url", None)
        if mu and not url:
            url = str(mu).strip()
        mt = getattr(md, "title", None) or getattr(md, "og_title", None)
        if mt and not title:
            title = str(mt).strip()
    return url, title


def _topic_label(query: str, max_len: int = 52) -> str:
    q = query.strip()
    if len(q) <= max_len:
        return q
    return q[: max_len - 1] + "…"


def _normalize_url_key(url: str) -> str:
    p = urlparse(url.strip())
    host = (p.netloc or "").lower()
    path = (p.path or "").rstrip("/")
    return f"{host}{path}"


def _extract_sources_from_raw_results(
    raw_results: list[dict],
    queries: list[str],
    max_n: int = 12,
) -> list[ResearchSource]:
    seen: set[str] = set()
    out: list[ResearchSource] = []
    for r, query in zip(raw_results, queries):
        topic = _topic_label(query)
        for item in r.get("data", []):
            if not isinstance(item, dict):
                continue
            url = (item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url and not title:
                continue
            key = _normalize_url_key(url) if url else f"title:{title[:120]}"
            if key in seen:
                continue
            seen.add(key)
            label = title or (urlparse(url).netloc if url else "") or "Source"
            out.append(ResearchSource(title=label, url=url, topic=topic))
            if len(out) >= max_n:
                return out
    return out


def _dedupe_agentic_sources(raw: list[tuple[str, str, str]], max_n: int = 12) -> list[ResearchSource]:
    seen: set[str] = set()
    out: list[ResearchSource] = []
    for url, title, topic in raw:
        if not url and not title:
            continue
        key = _normalize_url_key(url) if url else f"title:{title[:120]}"
        if key in seen:
            continue
        seen.add(key)
        label = title or (urlparse(url).netloc if url else "") or "Source"
        out.append(ResearchSource(title=label, url=url, topic=_topic_label(topic)))
        if len(out) >= max_n:
            break
    return out


def _methodology_note(
    *,
    used_firecrawl: bool,
    used_llm: bool,
    sp500_used_fallback: bool,
    equity_benchmark: str = "S&P 500",
    student_illustrative_horizon: bool = False,
    used_user_reported_tuition: bool = False,
) -> str:
    parts: list[str] = []
    if used_firecrawl:
        parts.append("Numbers come from the pages linked below.")
    else:
        parts.append("Web search was off — figures are thin.")
    if used_llm:
        parts.append("AI condensed the snippets into this card.")
    if used_user_reported_tuition:
        parts.append(
            "Tuition on the card uses the amount the user reported (annual fees were scaled to a total when needed). "
            "Published fees from search may differ."
        )
    if sp500_used_fallback:
        parts.append(
            f"{equity_benchmark}-style growth uses a long-run average when snippets had no clear rate."
        )
    if student_illustrative_horizon:
        parts.append(
            "Not graduated yet (or grad year missing): index comparison uses a short illustrative horizon."
        )
    return " ".join(parts)


def _firecrawl_search_timeout_ms() -> int:
    try:
        return max(15000, int((os.getenv("FIRECRAWL_SEARCH_TIMEOUT_MS") or "55000").strip()))
    except ValueError:
        return 55000


def _firecrawl_max_concurrent() -> int:
    try:
        return max(1, min(10, int((os.getenv("FIRECRAWL_MAX_CONCURRENT") or "5").strip())))
    except ValueError:
        return 5


def _firecrawl_results_per_query() -> int:
    try:
        return max(1, min(8, int((os.getenv("FIRECRAWL_RESULTS_PER_QUERY") or "3").strip())))
    except ValueError:
        return 3


def _firecrawl_scrape_markdown() -> bool:
    v = (os.getenv("RESEARCH_FIRECRAWL_SCRAPE") or "false").strip().lower()
    return v not in ("0", "false", "no", "off")


def _research_max_queries() -> int:
    try:
        return max(4, min(14, int((os.getenv("RESEARCH_MAX_QUERIES") or "10").strip())))
    except ValueError:
        return 10


def _sync_search(client: FirecrawlApp, query: str, limit: int | None = None) -> dict:
    per_q = limit if limit is not None else _firecrawl_results_per_query()
    try:
        if _firecrawl_scrape_markdown():
            data = client.search(
                query,
                limit=per_q,
                timeout=_firecrawl_search_timeout_ms(),
                scrape_options={"formats": ["markdown"]},
            )
        else:
            data = client.search(
                query,
                limit=per_q,
                timeout=_firecrawl_search_timeout_ms(),
            )
        rows: list[dict] = []
        for item in data.web or []:
            text = _search_result_text(item)
            if not text.strip():
                continue
            url, title = _search_item_url_title(item)
            rows.append({"markdown": text[:4000], "url": url, "title": title})
        return {"data": rows}
    except Exception:
        logger.exception("Firecrawl search failed for query=%r", query[:80])
        return {"data": []}


async def _bounded_search(
    sem: asyncio.Semaphore,
    client: FirecrawlApp,
    query: str,
    limit: int | None = None,
) -> dict:
    ms = _firecrawl_search_timeout_ms()
    deadline = ms / 1000.0 + 25.0
    async with sem:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync_search, client, query, limit),
                timeout=deadline,
            )
        except asyncio.TimeoutError:
            logger.warning("Firecrawl search asyncio deadline exceeded query=%r", query[:80])
            return {"data": []}


def _build_queries(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    current_year: int,
    *,
    locale: str = "US",
) -> list[str]:
    # Used only for fallback one-shot path and activity previews.
    if locale == "UK":
        return [
            f"{current_job} average salary UK {current_year} ONS",
            f"{current_job} salary UK glassdoor reed indeed {current_year}",
            f"{degree} degree graduate salary UK {current_year}",
            f"{university} tuition fees UK total cost {graduation_year}",
            f"{university} UK tuition fees per year {graduation_year}",
            f"FTSE 100 average annual return {graduation_year} to {current_year} total return UK",
            f"FTSE 100 historical performance since {graduation_year} compound growth",
            f"{current_job} job market UK outlook {current_year} ONS",
            f"{current_job} UK job vacancies demand {current_year}",
            f"{degree} degree ROI UK ranking {current_year} worth it",
            f"{degree} degree lifetime earnings UK vs A levels",
            f"{current_job} AI automation UK replacement risk {current_year}",
            f"will AI replace {current_job} UK jobs PwC McKinsey",
            f"{degree} {university} worth it reddit UK {current_year - 1}",
        ]
    if locale == "EU":
        return [
            f"{current_job} average salary Europe {current_year} euros glassdoor indeed",
            f"{current_job} salary range Europe {current_year} entry senior",
            f"{degree} degree average salary Europe {current_year}",
            f"{university} tuition fees total cost {graduation_year} Europe",
            f"{university} annual tuition {graduation_year} euros",
            f"STOXX Europe 600 annual return {graduation_year} to {current_year}",
            f"European stock market average return since {graduation_year} MSCI Europe",
            f"{current_job} job market Europe outlook {current_year}",
            f"{current_job} job openings demand Europe {current_year}",
            f"{degree} degree ROI ranking Europe {current_year}",
            f"{degree} degree lifetime earnings premium Europe vs high school",
            f"{current_job} AI automation replacement risk Europe {current_year}",
            f"will AI replace {current_job} jobs Europe McKinsey",
            f"{degree} {university} worth it reddit {current_year - 1}",
        ]
    return [
        f"{current_job} average salary median salary {current_year} BLS",
        f"{current_job} salary range entry level senior {current_year}",
        f"{degree} degree average salary {current_year} payscale glassdoor",
        f"{university} total cost of attendance tuition room board {graduation_year}",
        f"{university} tuition {graduation_year} annual cost",
        f"S&P 500 average annual return {graduation_year} to {current_year} total return",
        f"S&P 500 historical performance since {graduation_year} compound growth",
        f"{current_job} job market outlook {current_year} BLS growth rate unemployment",
        f"{current_job} job openings demand {current_year}",
        f"{degree} degree ROI ranking {current_year} worth it",
        f"{degree} degree lifetime earnings premium vs high school",
        f"{current_job} AI automation replacement risk {current_year}",
        f"will AI replace {current_job} jobs McKinsey Goldman Sachs",
        f"{degree} {university} worth it reddit {current_year - 1}",
    ]


def resolve_research_query_plan(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    *,
    country_or_region: str = "",
    currency_code: str = "USD",
) -> tuple[list[str], str, str, str]:
    current_year = datetime.now().year
    norm_currency = coerced_currency_from_region(currency_code, country_or_region)
    loc = money_locale(norm_currency, country_or_region)
    equity_bench = equity_benchmark_label(loc)
    queries = _build_queries(degree, university, graduation_year, current_job, current_year, locale=loc)
    max_q = _research_max_queries()
    if len(queries) > max_q:
        queries = queries[:max_q]
    return queries, norm_currency, loc, equity_bench


def _effective_user_tuition_total(
    tuition_paid: int | None,
    tuition_is_total: bool,
    country_or_region: str,
) -> int | None:
    """Convert user-stated tuition to an approximate total degree cost (major units)."""
    if tuition_paid is None or tuition_paid <= 0:
        return None
    if tuition_is_total:
        return tuition_paid
    region = (country_or_region or "").strip().lower()
    ukish = bool(re.search(r"\b(uk|u\.k\.|united kingdom|england|scotland|wales|northern ireland|britain)\b", region))
    years = 3 if ukish else 4
    return tuition_paid * years


def _sp500_model(
    tuition: int | None,
    sp500_pct: float | None,
    index_fallback_year: int,
    compound_years: int,
) -> tuple[int | None, float | None, float | None]:
    if not tuition or tuition <= 0:
        return None, sp500_pct, None
    annual = sp500_pct if sp500_pct else _sp500_fallback(index_fallback_year)
    total = ((1 + annual / 100) ** compound_years - 1) * 100
    invested = _compound_growth(tuition, annual, compound_years)
    return invested, total, annual


def _build_from_llm(
    llm: LLMAnalysis,
    raw_snippets: list[str],
    compound_years: int,
    years_since_graduation: int | None,
    index_anchor_year: int,
    *,
    sources_list: list[ResearchSource],
    used_firecrawl: bool,
    currency_code: str,
    equity_benchmark: str,
    student_mode: bool,
    search_queries: list[str],
    search_hit_counts: list[int],
    user_tuition_total: int | None = None,
) -> ResearchData:
    web_tuition = llm.estimated_tuition
    used_user_reported = bool(user_tuition_total and user_tuition_total > 0)
    tuition_web_estimate: int | None = web_tuition if used_user_reported else None
    tuition = user_tuition_total if used_user_reported else web_tuition
    sp500_used_fallback = bool(tuition and tuition > 0 and llm.sp500_annual_return_pct is None)
    sp500_invested, sp500_total, sp500_annual = _sp500_model(
        tuition, llm.sp500_annual_return_pct, index_anchor_year, compound_years
    )
    tuition_if_invested = sp500_invested
    opp_gap = financial_opportunity_gap(tuition, tuition_if_invested)
    trend = llm.job_market_trend
    ai_risk, ai_reasoning, task_exposure, near_term = resolve_ai_replacement_from_llm(
        llm.ai_replacement_risk_0_100,
        (llm.ai_risk_reasoning or "").strip(),
        llm.job_tasks,
    )
    career_market = compute_career_market_stress_0_100(trend, llm.unemployment_rate_pct)
    financial_roi = compute_financial_roi_stress_0_100(tuition, tuition_if_invested)
    cooked = compute_overall_cooked_from_components(ai_risk, career_market, financial_roi)
    named = [s.strip() for s in (llm.source_orgs_mentioned or []) if s and str(s).strip()][:5]

    return ResearchData(
        currency_code=currency_code,
        avg_salary_for_degree=llm.avg_salary_for_degree,
        avg_salary_for_role=llm.avg_salary_for_role,
        median_salary_for_role=llm.median_salary_for_role,
        salary_range_low=llm.salary_range_low,
        salary_range_high=llm.salary_range_high,
        estimated_tuition=tuition,
        tuition_web_estimate=tuition_web_estimate,
        tuition_if_invested=tuition_if_invested,
        tuition_opportunity_gap=opp_gap,
        degree_roi_rank=llm.degree_roi_rank,
        job_market_trend=trend,
        unemployment_rate_pct=llm.unemployment_rate_pct,
        job_openings_estimate=llm.job_openings_estimate,
        raw_search_results=raw_snippets,
        search_queries=search_queries,
        search_hit_counts=search_hit_counts,
        sources=sources_list,
        named_sources=named,
        methodology_note=_methodology_note(
            used_firecrawl=used_firecrawl,
            used_llm=True,
            sp500_used_fallback=sp500_used_fallback,
            equity_benchmark=equity_benchmark,
            student_illustrative_horizon=student_mode,
            used_user_reported_tuition=used_user_reported,
        ),
        sp500_annual_return_pct=sp500_annual,
        sp500_total_return_pct=sp500_total,
        tuition_as_sp500_today=sp500_invested,
        years_since_graduation=years_since_graduation,
        lifetime_earnings_estimate=llm.lifetime_earnings_estimate,
        degree_premium_over_hs=llm.degree_premium_over_hs,
        ai_replacement_risk_0_100=ai_risk,
        ai_risk_reasoning=ai_reasoning,
        job_task_exposure=task_exposure,
        near_term_ai_risk_0_100=near_term,
        career_market_stress_0_100=career_market,
        financial_roi_stress_0_100=financial_roi,
        overall_cooked_0_100=cooked,
        safeguard_tips=llm.safeguard_tips[:6],
        honest_take=llm.honest_take,
    )


async def _try_agentic(
    fc: FirecrawlApp,
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None,
    salary: int | None,
    *,
    country_or_region: str,
    currency_code: str,
    money_locale_key: str,
    equity_benchmark: str,
    user_tuition_total: int | None = None,
) -> AgenticResult | None:
    sem = asyncio.Semaphore(_firecrawl_max_concurrent())
    search_fn = lambda q: _bounded_search(sem, fc, q)  # noqa: E731
    try:
        return await agentic_research(
            search_fn,
            degree,
            university,
            graduation_year,
            current_job,
            years_experience,
            salary,
            country_or_region=country_or_region,
            currency_code=currency_code,
            money_locale=money_locale_key,
            equity_benchmark=equity_benchmark,
            user_tuition_total=user_tuition_total,
        )
    except Exception:
        logger.exception("Agentic research failed")
        return None


async def run_research(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None = None,
    salary: int | None = None,
    country_or_region: str = "",
    currency_code: str = "USD",
    tuition_paid: int | None = None,
    tuition_is_total: bool = True,
) -> ResearchData:
    try:
        from opentelemetry import trace

        span_cm = trace.get_tracer(__name__).start_as_current_span("run_research")
    except Exception:
        from contextlib import nullcontext

        span_cm = nullcontext()
    with span_cm:
        return await _run_research_impl(
            degree,
            university,
            graduation_year,
            current_job,
            years_experience,
            salary,
            country_or_region,
            currency_code,
            tuition_paid,
            tuition_is_total,
        )


async def _run_research_impl(
    degree: str,
    university: str,
    graduation_year: int,
    current_job: str,
    years_experience: int | None,
    salary: int | None,
    country_or_region: str,
    currency_code: str,
    tuition_paid: int | None = None,
    tuition_is_total: bool = True,
) -> ResearchData:
    current_year = datetime.now().year
    fc = _get_firecrawl()
    user_tuition_total = _effective_user_tuition_total(
        tuition_paid, tuition_is_total, country_or_region
    )
    queries, norm_currency, loc, equity_bench = resolve_research_query_plan(
        degree,
        university,
        graduation_year,
        current_job,
        country_or_region=country_or_region,
        currency_code=currency_code,
    )
    compound_years, years_since_grad = grad_timeline(graduation_year, current_year)
    index_anchor = index_anchor_year(graduation_year, current_year)

    if fc is None:
        raise RuntimeError("FIRECRAWL_API_KEY is required for research.")

    # Primary path: Claude agentic search
    agentic = await _try_agentic(
        fc,
        degree,
        university,
        graduation_year,
        current_job,
        years_experience,
        salary,
        country_or_region=country_or_region,
        currency_code=norm_currency,
        money_locale_key=loc,
        equity_benchmark=equity_bench,
        user_tuition_total=user_tuition_total,
    )
    if agentic is not None:
        logger.info(
            "Agentic research succeeded — %d searches, %d snippets",
            len(agentic.queries_used),
            len(agentic.raw_snippets),
        )
        source_objects = _dedupe_agentic_sources(agentic.sources)
        return _build_from_llm(
            agentic.analysis,
            agentic.raw_snippets,
            compound_years,
            years_since_grad,
            index_anchor,
            sources_list=source_objects,
            used_firecrawl=True,
            currency_code=norm_currency,
            equity_benchmark=equity_bench,
            student_mode=years_since_grad is None,
            search_queries=agentic.queries_used,
            search_hit_counts=agentic.hit_counts,
            user_tuition_total=user_tuition_total,
        )

    # Fallback path: parallel search + one-shot Claude extraction (still no heuristics)
    logger.info("Agentic unavailable — falling back to parallel Firecrawl + one-shot Claude")
    sem = asyncio.Semaphore(_firecrawl_max_concurrent())
    tasks = [_bounded_search(sem, fc, q) for q in queries]
    raw_results = await asyncio.gather(*tasks)
    hit_counts = [
        sum(1 for item in r.get("data", []) if item.get("markdown"))
        for r in raw_results
    ]
    snippets_per_query = [
        " ".join(item.get("markdown", "")[:600] for item in r.get("data", []) if item.get("markdown"))
        for r in raw_results
    ]
    raw_snippets = [s for s in snippets_per_query if s]
    sources_list = _extract_sources_from_raw_results(raw_results, queries)

    llm = await analyze_with_llm(
        degree=degree,
        university=university,
        graduation_year=graduation_year,
        current_job=current_job,
        years_experience=years_experience,
        salary=salary,
        queries=queries,
        snippets_per_query=snippets_per_query,
        country_or_region=country_or_region,
        currency_code=norm_currency,
        money_locale=loc,
        equity_benchmark=equity_bench,
        user_tuition_total=user_tuition_total,
    )
    if llm is None:
        raise RuntimeError("Claude analysis failed. Research requires Anthropic and Firecrawl.")

    return _build_from_llm(
        llm,
        raw_snippets,
        compound_years,
        years_since_grad,
        index_anchor,
        sources_list=sources_list,
        used_firecrawl=True,
        currency_code=norm_currency,
        equity_benchmark=equity_bench,
        student_mode=years_since_grad is None,
        search_queries=queries,
        search_hit_counts=hit_counts,
        user_tuition_total=user_tuition_total,
    )


async def scrape_linkedin(url: str) -> dict | None:
    fc = _get_firecrawl()
    if fc is None:
        return None
    try:
        doc = await asyncio.to_thread(fc.scrape, url, formats=["markdown"])
        md = getattr(doc, "markdown", None) or ""
        return {"markdown": md}
    except Exception:
        logger.exception("LinkedIn scrape failed")
        return None
