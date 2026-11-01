"""Metrology Guard AI API."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from database import initialize, get_job, get_scan, list_scans, save_job, save_scan
from date_engine import normalize_dates
from extraction import extract_label, extract_product_views
from pdf_generator import create_report
from rule_engine import evaluate_compliance

app = FastAPI(title="Nyay Vision | Metrology Guard AI", version="1.0.0")
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *allowed_origins], allow_origin_regex=r"https://[a-zA-Z0-9-]+\.vercel\.app", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class UploadFileRequest(BaseModel):
    filename: str
    content_type: str

class PresignRequest(BaseModel):
    files: list[UploadFileRequest] = Field(min_length=1, max_length=10)

class UploadedObject(BaseModel):
    key: str
    filename: str
    content_type: str

class ScanObjectsRequest(BaseModel):
    files: list[UploadedObject] = Field(min_length=1, max_length=10)

@app.on_event("startup")
def startup() -> None:
    initialize()

@app.get("/health")
def health() -> dict[str, Any]:
    from settings import settings
    return {"status": "ok", "service": "nyay-vision", "openai_configured": bool(settings.openai_api_key), "persistence": "dynamodb" if settings.dynamodb_table else "sqlite", "direct_uploads": bool(os.getenv("S3_UPLOAD_BUCKET"))}

async def _scan_group(images: list[tuple[bytes, str, str]]) -> dict[str, Any]:
    if not images:
        raise HTTPException(400, "Select at least one package image.")
    if len(images) > 10:
        raise HTTPException(400, "A product audit can contain up to 10 images.")
    total_size = 0
    for payload, content_type, filename in images:
        if content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise HTTPException(415, f"{filename or 'A file'} is not an image. Upload PNG, JPG, or WEBP photos.")
        if len(payload) > 12 * 1024 * 1024:
            raise HTTPException(413, f"{filename or 'Image'} is larger than 12 MB.")
        total_size += len(payload)
        if total_size > 48 * 1024 * 1024:
            raise HTTPException(413, "The combined images must be smaller than 48 MB.")
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
    content_type = file.content_type
    if content_type not in {"image/png", "image/jpeg", "image/webp"} and content_type in {None, "", "application/octet-stream"}:
        suffix = Path(file.filename or "").suffix.lower()
        content_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(suffix)
    return await _scan_group([(await file.read(), content_type or "", file.filename or "package image")])

@app.post("/scan-multi")
async def scan_multi(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    images = []
    for item in files:
        content_type = item.content_type
        if content_type not in {"image/png", "image/jpeg", "image/webp"} and content_type in {None, "", "application/octet-stream"}:
            suffix = Path(item.filename or "").suffix.lower()
            content_type = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(suffix)
        images.append((await item.read(), content_type or "", item.filename or f"package view {len(images) + 1}"))
    return await _scan_group(images)

@app.post("/uploads/presign")
def presign_uploads(request: PresignRequest) -> dict[str, Any]:
    bucket = os.getenv("S3_UPLOAD_BUCKET")
    if not bucket:
        raise HTTPException(503, "Direct uploads are not configured on this backend.")
    import boto3
    s3 = boto3.client("s3")
    uploads = []
    for file in request.files:
        if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise HTTPException(415, f"{file.filename or 'A file'} is not a supported image.")
        suffix = Path(file.filename or "").suffix.lower()
        key = f"uploads/{uuid4()}{suffix}"
        url = s3.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": key, "ContentType": file.content_type}, ExpiresIn=600)
        uploads.append({"key": key, "url": url, "content_type": file.content_type})
    return {"uploads": uploads}

@app.post("/scan-objects")
def scan_objects(request: ScanObjectsRequest) -> dict[str, Any]:
    bucket = os.getenv("S3_UPLOAD_BUCKET")
    queue_url = os.getenv("SCAN_QUEUE_URL")
    if not bucket or not queue_url:
        raise HTTPException(503, "Serverless image processing is not configured on this backend.")
    for item in request.files:
        if not item.key.startswith("uploads/") or item.content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise HTTPException(400, "Invalid uploaded image reference.")
    job_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    job = {"job_id": job_id, "status": "queued", "created_at": now, "expires_at": int(datetime.now(timezone.utc).timestamp()) + 86400}
    save_job(job)
    try:
        import boto3
        boto3.client("sqs").send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({"job_id": job_id, "files": [item.model_dump() for item in request.files]}),
        )
    except Exception as exc:
        save_job({**job, "status": "failed", "error": "The scan could not be queued. Please retry."})
        raise HTTPException(503, "The scan could not be queued. Please retry.") from exc
    return {"job_id": job_id, "status": "queued"}

def _run_scan_group(images: list[tuple[bytes, str, str]]) -> dict[str, Any]:
    """Synchronous Lambda route counterpart for the shared async extraction flow."""
    import asyncio
    return asyncio.run(_scan_group(images))

@app.get("/history")
def history(limit: int = 100) -> dict[str, Any]:
    return {"items": list_scans(max(1, min(limit, 500)))}

@app.get("/jobs/{job_id}")
def scan_job(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Scan job not found or expired.")
    return job

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

from mangum import Mangum
lambda_handler = Mangum(app, lifespan="off")
