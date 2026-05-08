"""CV parsing (PDF / DOCX -> text) and Claude-powered concise coaching."""

from __future__ import annotations

import asyncio
import io
import os
from datetime import datetime

import structlog

from backend.models import CVAnalysis, CVEducation, CVExperienceEntry, CVHighlight, CVSectionFeedback

logger = structlog.get_logger(__name__)

MAX_CV_BYTES = int((os.getenv("CV_MAX_BYTES") or str(5 * 1024 * 1024)).strip())
MAX_CV_TEXT_CHARS = 30_000

CV_ANALYSIS_TOOL = {
    "name": "submit_cv_analysis",
    "description": "Submit concise CV coaching results with exact CV anchors and extracted profile data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "candidate_name": {
                "type": "string",
                "description": "Candidate's name as written on the CV (best guess). Empty if truly missing.",
            },
            "candidate_email": {
                "type": "string",
                "description": "Email address from the CV. Empty if not found.",
            },
            "candidate_phone": {
                "type": "string",
                "description": "Phone number from the CV. Empty if not found.",
            },
            "candidate_location": {
                "type": "string",
                "description": "City/region/country from the CV. Empty if not found.",
            },
            "current_role": {
                "type": "string",
                "description": "Most recent or current job title from the CV. Empty if not found.",
            },
            "current_company": {
                "type": "string",
                "description": "Most recent or current employer from the CV. Empty if not found.",
            },
            "experience_years": {
                "type": "integer",
                "description": "Estimated total years of professional experience based on work history dates. 0 if can't determine.",
            },
            "education": {
                "type": "array",
                "description": "Education entries extracted from the CV, most recent first.",
                "items": {
                    "type": "object",
                    "properties": {
                        "degree": {"type": "string", "description": "Degree name (e.g. 'BSc Computer Science')."},
                        "institution": {"type": "string", "description": "University or school name."},
                        "year": {"type": "string", "description": "Graduation year or date range. Empty if not stated."},
                    },
                    "required": ["degree", "institution"],
                },
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key skills/tools/technologies extracted from the CV (top 10-15, most relevant first).",
            },
            "experience_entries": {
                "type": "array",
                "description": "Work experience entries extracted from the CV, most recent first. Max 5.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "company": {"type": "string"},
                        "dates": {"type": "string", "description": "Date range as written on CV."},
                        "summary": {"type": "string", "description": "1-sentence summary of what they did in this role (max 20 words)."},
                    },
                    "required": ["title", "company"],
                },
            },
            "overall_score_0_100": {
                "type": "integer",
                "description": "Overall CV quality 0-100.",
            },
            "verdict": {
                "type": "string",
                "description": "One punchy sentence verdict (like a recruiter's gut reaction).",
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 strengths, each max 12 words.",
            },
            "fixes": {
                "type": "array",
                "description": "3-6 specific fixes, ranked by impact. Each is a concrete action anchored to exact CV text.",
                "items": {
                    "type": "object",
                    "properties": {
                        "match_text": {
                            "type": "string",
                            "description": "Exact substring copied from the CV text that should be changed (must appear verbatim).",
                        },
                        "issue": {
                            "type": "string",
                            "description": "What's wrong (max 15 words).",
                        },
                        "fix": {
                            "type": "string",
                            "description": "Exact action to take (max 20 words).",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "important", "suggestion"],
                        },
                        "section": {
                            "type": "string",
                            "description": "CV section this applies to.",
                        },
                    },
                    "required": ["match_text", "issue", "fix", "severity", "section"],
                },
            },
            "missing_sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sections the CV should have but doesn't (e.g. 'Skills', 'Summary'). Empty if none.",
            },
            "donald_take": {
                "type": "string",
                "description": "2-3 sentence coaching summary in Donald's voice: direct, honest, slightly roasty but helpful. This is what Donald reads aloud.",
            },
        },
        "required": [
            "candidate_name",
            "overall_score_0_100",
            "verdict",
            "strengths",
            "fixes",
            "missing_sections",
            "donald_take",
            "education",
            "skills",
        ],
    },
}

_CV_SYSTEM_PROMPT = """\
You are a ruthlessly efficient CV coach. Return ONLY the structured tool call.
No filler, no hedging. Short. Punchy. Done.

## Profile extraction (IMPORTANT)
- Extract ALL available profile data: name, email, phone, location, current role, company, education, skills, experience.
- For education: extract every degree/cert with institution and year.
- For skills: pull the top 10-15 most relevant skills/tools/technologies.
- For experience_entries: extract up to 5 most recent roles with title, company, dates, and a 1-sentence summary.
- Estimate experience_years from the date range of work history.
- This data powers the voice agent — extract it accurately so the AI doesn't need to ask the user.

## Annotation requirement (IMPORTANT)
- You MUST set candidate_name (best guess from the header / contact block).
- For each fix, set match_text to an EXACT substring copied from the CV text.
  - It must appear verbatim in the CV. Copy/paste.
  - Keep match_text short (ideally <= 120 chars) but specific enough to find.
  - Do not paraphrase match_text.

## Scoring rubric
S (85-100) Interview-ready: quantified bullets, strong summary, tailored keywords, clean format.
A (70-84) Solid, minor polish: good structure, most bullets quantified, small gaps.
B (55-69) Decent bones, needs work: right sections but duty-based bullets, generic skills.
C (40-54) Weak, major rewrites: missing sections, no metrics, passive language, filler.
D (25-39) Barely a CV: job-description copy-paste, no outcomes, placeholder objective.
F (0-24) Start over: incomplete, no structure, missing contact info.

## Scoring dimensions (weight)
- Impact language (25%): action verbs + outcomes vs "Responsible for"
- Structure & sections (20%): Summary/Exp/Edu/Skills/Projects present and ordered
- ATS & keywords (20%): role-specific tools named vs generic "Microsoft Office"
- Quantification (20%): numbers in 70%+ of bullets vs zero metrics
- Conciseness & formatting (15%): 1-2 pages, consistent, no fluff

## Example: score 28 (D)
Verdict: "Recruiter would skip this in 3 seconds flat."
Strengths: ["Contact info present", "Chronological layout"]
Fixes: [critical/Objective: generic objective → 2-line summary with niche + top win], [critical/Experience: "Helped with" framing → own outcomes with numbers], [important/Skills: filler words → real tools]
Donald: "Your CV reads like a job description. Duties instead of wins. One evening adding numbers takes this from 28 to 65."

## Example: score 62 (B)
Verdict: "Got the bones, missing the muscle."
Strengths: ["Solid structure", "Some bullets quantified", "Real tools named"]
Fixes: [important/Experience: only 2/12 bullets have numbers → add metrics to 8+], [suggestion/Projects: no projects section → add 2-3 with tech + impact]
Donald: "Structure is solid, you know your tools. But bullets read like task lists. Add numbers and a projects section to jump a tier."

## Example: score 88 (S)
Verdict: "This person gets interviews. Minor polish only."
Strengths: ["Every bullet has a metric", "Summary nails positioning", "Projects with live links"]
Fixes: [suggestion/Experience: oldest role has 4 bullets → trim to 2], [suggestion/Skills: missing trending keyword → add AI/ML]
Donald: "Not much to roast. Your CV looks like someone who gets callbacks. Trim old role, add trending keywords, go get paid."

## Output rules
- Verdict: one sentence, recruiter gut reaction. Brutal.
- Strengths: max 3, each under 12 words.
- Fixes: 3-6, ranked by impact. Concrete actions, not paragraphs. Be specific.
- Severity: critical = will get rejected. important = significantly weakens. suggestion = polish.
- missing_sections: only actually expected and missing sections.
- donald_take: 2-3 sentences. Blunt, roasty, wants you to win. Reference something specific.
- Do NOT dump CV text. Do NOT write paragraphs.
"""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    import pdfplumber

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_cv_text(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    if lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {filename}. Upload a PDF, DOCX, or TXT file.")


def _get_client():
    import anthropic

    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return None
    try:
        timeout_sec = float((os.getenv("ANTHROPIC_TIMEOUT_SEC") or "180").strip() or "180")
    except ValueError:
        timeout_sec = 180.0
    return anthropic.Anthropic(api_key=key, timeout=max(30.0, timeout_sec))


def _parse_cv_tool_response(message) -> dict | None:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_cv_analysis":
            return block.input
    return None


async def analyze_cv(cv_text: str, filename: str) -> CVAnalysis:
    """Send CV text to Claude for concise coaching analysis."""
    client = _get_client()
    if client is None:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    truncated = cv_text[:MAX_CV_TEXT_CHARS]
    model = (os.getenv("ANTHROPIC_CV_MODEL") or os.getenv("ANTHROPIC_ANALYSIS_MODEL") or "claude-haiku-4-5").strip()

    user_msg = f"CV file: {filename}\n\n```\n{truncated}\n```\n\nAnalyse. Call submit_cv_analysis."

    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model=model,
            system=_CV_SYSTEM_PROMPT,
            max_tokens=1500,
            tools=[CV_ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "submit_cv_analysis"},
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception:
        logger.exception("Claude CV analysis call failed")
        raise RuntimeError("CV analysis failed — please try again.")

    result = _parse_cv_tool_response(response)
    if result is None:
        raise RuntimeError("Claude did not return a structured CV analysis.")

    fixes = result.get("fixes", [])
    highlights = [
        CVHighlight(
            original_text=f.get("match_text", "") or f.get("issue", ""),
            suggested_text=f.get("fix", ""),
            reason="",
            severity=f.get("severity", "suggestion"),
            section=f.get("section", ""),
        )
        for f in fixes
        if f.get("match_text") or f.get("issue")
    ]

    missing = result.get("missing_sections", [])
    sections = [
        CVSectionFeedback(name=m, score_0_10=0, summary="Missing from your CV.")
        for m in missing
    ]

    education_raw = result.get("education", [])
    education = [
        CVEducation(
            degree=e.get("degree", ""),
            institution=e.get("institution", ""),
            year=e.get("year", ""),
        )
        for e in education_raw
        if e.get("degree") or e.get("institution")
    ]

    experience_raw = result.get("experience_entries", [])
    experience_entries = [
        CVExperienceEntry(
            title=x.get("title", ""),
            company=x.get("company", ""),
            dates=x.get("dates", ""),
            summary=x.get("summary", ""),
        )
        for x in experience_raw
        if x.get("title") or x.get("company")
    ]

    return CVAnalysis(
        candidate_name=(result.get("candidate_name", "") or "").strip(),
        candidate_email=(result.get("candidate_email", "") or "").strip(),
        candidate_phone=(result.get("candidate_phone", "") or "").strip(),
        candidate_location=(result.get("candidate_location", "") or "").strip(),
        current_role=(result.get("current_role", "") or "").strip(),
        current_company=(result.get("current_company", "") or "").strip(),
        experience_years=int(result.get("experience_years", 0) or 0),
        education=education,
        skills=result.get("skills", []),
        experience_entries=experience_entries,
        cv_text=truncated,
        overall_score_0_100=int(result.get("overall_score_0_100", 50)),
        overall_summary=result.get("verdict", ""),
        strengths=result.get("strengths", []),
        top_actions=[f"{f.get('issue', '')} → {f.get('fix', '')}" for f in fixes if f.get("issue")],
        sections=sections,
        highlights=highlights,
        coaching_notes=result.get("donald_take", ""),
        file_name=filename,
        analyzed_at=datetime.now(),
    )
