import uuid
from pathlib import Path
from typing import Optional
import shutil

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.pipeline import run_analysis


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
REPORTS_DIR = BASE_DIR / "reports"
TMP_DIR = BASE_DIR / "tmp"
DEMO_DIR = STATIC_DIR / "demo"
DEMO_CSV = DEMO_DIR / "sample.csv"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Auto Data Analyst Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> HTMLResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="index.html not found")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.post("/demo")
def demo() -> JSONResponse:
    if not DEMO_CSV.exists():
        raise HTTPException(status_code=500, detail="Demo CSV not found.")

    run_id = uuid.uuid4().hex
    run_dir = REPORTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    tmp_path = TMP_DIR / f"{run_id}.csv"
    shutil.copyfile(DEMO_CSV, tmp_path)

    try:
        result = run_analysis(
            csv_path=str(tmp_path),
            output_dir=str(run_dir),
            api_key="",
            target=None,
            task_type=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Demo analysis failed: {exc}") from exc

    report_path = run_dir / "report.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=500, detail="Report generation failed.")

    response = {
        "run_id": run_id,
        "report_url": f"/reports/{run_id}/report.pdf",
        "summary": result.get("summary", ""),
        "overview": result.get("overview", {}),
        "modeling": result.get("modeling", {}),
        "warnings": result.get("warnings", []),
    }
    return JSONResponse(response)


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    target: Optional[str] = Form(default=None),
    task_type: Optional[str] = Form(default=None),
) -> JSONResponse:
    if not api_key.strip():
        raise HTTPException(status_code=400, detail="API key is required.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    run_id = uuid.uuid4().hex
    run_dir = REPORTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    tmp_path = TMP_DIR / f"{run_id}.csv"
    with tmp_path.open("wb") as f:
        f.write(await file.read())

    try:
        result = run_analysis(
            csv_path=str(tmp_path),
            output_dir=str(run_dir),
            api_key=api_key,
            target=target,
            task_type=task_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    report_path = run_dir / "report.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=500, detail="Report generation failed.")

    response = {
        "run_id": run_id,
        "report_url": f"/reports/{run_id}/report.pdf",
        "summary": result.get("summary", ""),
        "overview": result.get("overview", {}),
        "modeling": result.get("modeling", {}),
        "warnings": result.get("warnings", []),
    }
    return JSONResponse(response)


@app.get("/reports/{run_id}/report.pdf")
def download_report(run_id: str) -> FileResponse:
    report_path = REPORTS_DIR / run_id / "report.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(report_path, media_type="application/pdf", filename="report.pdf")
