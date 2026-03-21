from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_ok() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_analyze_requires_api_key() -> None:
    resp = client.post(
        "/analyze",
        data={"api_key": "   "},
        files={"file": ("sample.csv", "a,b\n1,2\n", "text/csv")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "API key is required."


def test_analyze_rejects_non_csv() -> None:
    resp = client.post(
        "/analyze",
        data={"api_key": "dummy-key"},
        files={"file": ("sample.txt", "hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only CSV files are supported."


def test_analyze_success(monkeypatch) -> None:
    def fake_run_analysis(
        csv_path: str,
        output_dir: str,
        api_key: str,
        target: str | None = None,
        task_type: str | None = None,
    ) -> dict:
        report_path = Path(output_dir) / "report.pdf"
        report_path.write_bytes(b"%PDF-1.4\n% test")
        return {
            "summary": "ok",
            "overview": {"rows": 1},
            "modeling": {"status": "completed"},
            "warnings": [],
        }

    monkeypatch.setattr(main_module, "run_analysis", fake_run_analysis)

    resp = client.post(
        "/analyze",
        data={"api_key": "dummy-key"},
        files={"file": ("sample.csv", "a,b\n1,2\n", "text/csv")},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["summary"] == "ok"
    assert payload["overview"] == {"rows": 1}
    assert payload["modeling"]["status"] == "completed"
    assert payload["report_url"].endswith("/report.pdf")

