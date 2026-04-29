from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .database import fetch_report, init_db, insert_report
from .deepseek import generate_report
from .models import EvaluationPayload, ReportResponse
from .pdf import build_pdf, pdf_dir


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ACL-helper API",
    description="Structured rehabilitation assessment API. Raw video and camera frames are never accepted.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "privacy": "structured-data-only"}


@app.post("/api/reports", response_model=ReportResponse)
def create_report(payload: EvaluationPayload) -> ReportResponse:
    if payload.frameCount <= 0:
        raise HTTPException(status_code=400, detail="frameCount must be greater than 0")

    init_db()
    report = generate_report(payload)
    created_at = datetime.now(timezone.utc)
    report_id = insert_report(
        action_type=payload.actionType,
        mode=payload.mode,
        overall_score=report.overallScore,
        summary=payload.summary.model_dump(mode="json"),
        report=report.model_dump(mode="json"),
        created_at=created_at.isoformat(),
    )
    build_pdf(report_id, payload, report)

    return ReportResponse(
        id=report_id,
        pdfUrl=f"/api/reports/{report_id}/pdf",
        createdAt=created_at,
        **report.model_dump(),
    )


@app.get("/api/reports/{report_id}/pdf")
def download_pdf(report_id: int) -> FileResponse:
    row = fetch_report(report_id)
    path = pdf_dir() / f"acl-helper-report-{report_id}.pdf"
    if row is None or not path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
