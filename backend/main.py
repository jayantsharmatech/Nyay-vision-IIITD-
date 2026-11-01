"""Metrology Guard AI API."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from database import initialize, get_scan, list_scans, save_scan
from date_engine import normalize_dates
from extraction import extract_label, extract_product_views
from pdf_generator import create_report
from rule_engine import evaluate_compliance

app = FastAPI(title="Nyay Vision | Metrology Guard AI", version="1.0.0")
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *allowed_origins], allow_origin_regex=r"https://[a-zA-Z0-9-]+\.vercel\.app", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup() -> None:
    initialize()

@app.get("/health")
def health() -> dict[str, Any]:
    from settings import settings
    return {"status": "ok", "service": "nyay-vision", "openai_configured": bool(settings.openai_api_key), "persistence": "dynamodb" if settings.dynamodb_table else "sqlite"}

async def _scan_group(files: list[UploadFile]) -> dict[str, Any]:
    if not files:
        raise HTTPException(400, "Select at least one package image.")
    if len(files) > 10:
        raise HTTPException(400, "A product audit can contain up to 10 images.")
    images = []
    total_size = 0
    for item in files:
        content_type = item.content_type
        if content_type not in {"image/png", "image/jpeg", "image/webp"} and content_type in {None, "", "application/octet-stream"}:
            suffix = Path(item.filename or "").suffix.lower()
            content_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(suffix)
        if content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise HTTPException(415, f"{item.filename or 'A file'} is not an image. Upload PNG, JPG, or WEBP photos.")
        payload = await item.read()
        if len(payload) > 12 * 1024 * 1024:
            raise HTTPException(413, f"{item.filename or 'Image'} is larger than 12 MB.")
        total_size += len(payload)
        if total_size > 48 * 1024 * 1024:
            raise HTTPException(413, "The combined images must be smaller than 48 MB.")
        images.append((payload, content_type, item.filename or f"package view {len(images) + 1}"))
    try:
        if len(images) == 1:
            extracted = await extract_label(images[0][0], images[0][1])
        else:
            extracted = await extract_product_views(images)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if len(images) > 1 and (not extracted.get("same_product") or extracted.get("product_match_confidence", 0) < 0.65):
        raise HTTPException(422, "These photos could not be confidently matched to one product. Upload views of the same product together, or scan different products separately.")
    extracted = normalize_dates(extracted)
    extracted["image_count"] = len(images)
    extracted["source_images"] = [name for _, _, name in images]
    audit = evaluate_compliance(extracted)
    scan_id = str(uuid4())
    record = {"scan_id": scan_id, "created_at": datetime.now(timezone.utc).isoformat(), "filename": ", ".join(name for _, _, name in images), "image_count": len(images), "image_files": [name for _, _, name in images], "category": audit["category"]["id"], "category_info": audit["category"], "extraction": extracted, "audit": audit, "sync_status": "synced"}
    save_scan(record)
    return record

@app.post("/scan")
async def scan(file: UploadFile = File(...)) -> dict[str, Any]:
    return await _scan_group([file])

@app.post("/scan-multi")
async def scan_multi(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    return await _scan_group(files)

@app.get("/history")
def history(limit: int = 100) -> dict[str, Any]:
    return {"items": list_scans(max(1, min(limit, 500)))}

@app.get("/report/{scan_id}")
def report(scan_id: str) -> FileResponse:
    record = get_scan(scan_id)
    if not record:
        raise HTTPException(404, "Scan not found.")
    with tempfile.NamedTemporaryFile(prefix="nyay-vision-", suffix=".pdf", delete=False) as temp:
        path = Path(temp.name)
    try:
        create_report(record, path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return FileResponse(path, media_type="application/pdf", filename=f"Nyay-Vision-{scan_id[:8]}.pdf", background=BackgroundTask(path.unlink, missing_ok=True))

@app.get("/scan/{scan_id}")
def scan_detail(scan_id: str) -> dict[str, Any]:
    record = get_scan(scan_id)
    if not record:
        raise HTTPException(404, "Scan not found.")
    return record
