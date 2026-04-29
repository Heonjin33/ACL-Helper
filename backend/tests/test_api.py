from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def sample_payload():
    return {
        "actionType": "squat",
        "mode": "upload",
        "durationSec": 8.5,
        "repetitions": 3,
        "frameCount": 120,
        "summary": {
            "kneeFlexionAvg": 68.2,
            "kneeFlexionMax": 96.4,
            "hipFlexionAvg": 52.0,
            "hipFlexionMax": 78.5,
            "trunkLeanAvg": 18.4,
            "kneeSymmetryDiffAvg": 6.2,
            "kneeValgusIndexAvg": 0.09,
            "stabilityIndex": 18.0,
        },
        "preliminaryScores": {
            "rangeOfMotion": 82,
            "symmetry": 86,
            "stability": 82,
            "form": 88,
            "overall": 85,
        },
        "privacyNote": "structured data only",
        "generatedAt": "2026-04-29T06:00:00.000Z",
    }


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["privacy"] == "structured-data-only"


def test_create_report_without_deepseek_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    response = client.post("/api/reports", json=sample_payload())
    assert response.status_code == 200
    data = response.json()
    assert data["overallScore"] == 85
    assert data["pdfUrl"].endswith("/pdf")
    assert data["riskTips"]
