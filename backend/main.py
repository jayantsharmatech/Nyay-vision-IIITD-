"""Metrology Guard AI API."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from database import initialize, get_scan, list_scans, save_scan
from date_engine import normalize_dates
from extraction import extract_label
from pdf_generator import create_report
from rule_engine import evaluate_compliance

ROOT = Path(__file__).parent
REPORTS = ROOT / "data" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Nyay Vision | Metrology Guard AI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup() -> None:
    initialize()

@app.get("/health")
def health() -> dict[str, Any]:
    from settings import settings
    return {"status": "ok", "service": "nyay-vision", "openai_configured": bool(settings.openai_api_key)}

async def _scan(file: UploadFile) -> dict[str, Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "Upload a packaging photo in PNG, JPG, or WEBP format.")
    payload = await file.read()
    if len(payload) > 12 * 1024 * 1024:
        raise HTTPException(413, "Image must be smaller than 12 MB.")
    try:
        extracted = await extract_label(payload, file.content_type)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    extracted = normalize_dates(extracted)
    audit = evaluate_compliance(extracted)
    scan_id = str(uuid4())
    record = {"scan_id": scan_id, "created_at": datetime.now(timezone.utc).isoformat(), "filename": file.filename or "package image", "category": audit["category"]["id"], "category_info": audit["category"], "extraction": extracted, "audit": audit, "sync_status": "synced"}
    save_scan(record)
    pdf_path = REPORTS / f"{scan_id}.pdf"
    create_report(record, pdf_path)
    return record

@app.post("/scan")
async def scan(file: UploadFile = File(...)) -> dict[str, Any]:
    return await _scan(file)

@app.post("/scan-multi")
async def scan_multi(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(400, "Select at least one package image.")
    if len(files) > 10:
        raise HTTPException(400, "A batch can contain up to 10 images.")
    results = []
    for item in files:
        try:
            results.append(await _scan(item))
        except HTTPException as exc:
            results.append({"filename": item.filename, "error": exc.detail})
    return {"results": results, "total": len(files), "completed": sum("scan_id" in row for row in results)}

@app.get("/history")
def history(limit: int = 100) -> dict[str, Any]:
    return {"items": list_scans(max(1, min(limit, 500)))}

@app.get("/report/{scan_id}")
def report(scan_id: str) -> FileResponse:
    if not get_scan(scan_id):
        raise HTTPException(404, "Scan not found.")
    path = REPORTS / f"{scan_id}.pdf"
    if not path.exists():
        record = get_scan(scan_id)
        create_report(record, path)
    return FileResponse(path, media_type="application/pdf", filename=f"Nyay-Vision-{scan_id[:8]}.pdf")

@app.get("/scan/{scan_id}")
def scan_detail(scan_id: str) -> dict[str, Any]:
    record = get_scan(scan_id)
    if not record:
        raise HTTPException(404, "Scan not found.")
    return record
