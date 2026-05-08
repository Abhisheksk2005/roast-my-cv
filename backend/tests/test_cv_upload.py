"""Integration tests for the CV upload endpoint (mocked Claude)."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import CVAnalysis, CVHighlight, CVSectionFeedback


def _mock_analysis() -> CVAnalysis:
    return CVAnalysis(
        cv_text="Test CV text",
        overall_score_0_100=55,
        overall_summary="Decent but needs work.",
        strengths=["Good layout"],
        top_actions=["Add numbers"],
        sections=[
            CVSectionFeedback(
                name="Experience",
                score_0_10=5,
                summary="Lacks quantified achievements.",
            )
        ],
        highlights=[
            CVHighlight(
                original_text="Managed projects",
                suggested_text="Managed 8 cross-functional projects, delivering $1.2M in savings",
                reason="Quantify impact",
                severity="important",
                section="Experience",
            )
        ],
        coaching_notes="Overall decent but needs metrics.",
        file_name="test.txt",
    )


@pytest.fixture()
def client():
    return TestClient(app)


def test_upload_txt_cv(client: TestClient):
    with patch("backend.routers.cv.analyze_cv", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = _mock_analysis()

        cv_content = "Jane Doe\nExperience\nManaged projects\nEducation\nB.Sc. CS - MIT".encode("utf-8")
        response = client.post(
            "/api/cv/upload",
            files={"file": ("resume.txt", io.BytesIO(cv_content), "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert data["analysis"]["overall_score_0_100"] == 55
        assert len(data["analysis"]["highlights"]) == 1
        mock_analyze.assert_called_once()


def test_upload_empty_file(client: TestClient):
    response = client.post(
        "/api/cv/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_unsupported_format(client: TestClient):
    response = client.post(
        "/api/cv/upload",
        files={"file": ("resume.pptx", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_upload_too_large(client: TestClient):
    huge = b"x" * (6 * 1024 * 1024)
    response = client.post(
        "/api/cv/upload",
        files={"file": ("big.txt", io.BytesIO(huge), "text/plain")},
    )
    assert response.status_code == 413
