"""Tests for CV text extraction and analysis model construction."""

from __future__ import annotations

import pytest
from backend.services.cv_service import extract_cv_text
from backend.models import CVAnalysis, CVHighlight, CVSectionFeedback


def test_extract_text_from_txt():
    raw = "Jane Doe\njane@example.com\n\nExperience\nMarketing Manager".encode("utf-8")
    result = extract_cv_text(raw, "resume.txt")
    assert "Jane Doe" in result
    assert "Marketing Manager" in result


def test_extract_text_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported"):
        extract_cv_text(b"data", "resume.pptx")


def test_cv_analysis_model_roundtrip():
    highlight = CVHighlight(
        original_text="No metrics in bullets",
        suggested_text="Add revenue numbers to each role",
        reason="",
        severity="important",
        section="Experience",
    )
    analysis = CVAnalysis(
        cv_text="",
        overall_score_0_100=42,
        overall_summary="Needs work.",
        strengths=["Clean layout"],
        top_actions=["Add metrics"],
        sections=[],
        highlights=[highlight],
        coaching_notes="You need numbers.",
        file_name="test.pdf",
    )
    d = analysis.model_dump(mode="json")
    restored = CVAnalysis.model_validate(d)
    assert restored.overall_score_0_100 == 42
    assert len(restored.highlights) == 1
    assert restored.highlights[0].original_text == "No metrics in bullets"


def test_highlight_severity_values():
    for sev in ("critical", "important", "suggestion"):
        h = CVHighlight(
            original_text="x",
            suggested_text="y",
            reason="",
            severity=sev,
            section="s",
        )
        assert h.severity == sev
