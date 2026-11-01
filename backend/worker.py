"""SQS worker for serverless package-image analysis jobs."""
import json
import logging
import os
from datetime import datetime, timezone

import boto3

from database import get_job, save_job
from main import _run_scan_group

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    s3 = boto3.client("s3")
    bucket = os.environ["S3_UPLOAD_BUCKET"]
    for message in event.get("Records", []):
        payload = json.loads(message["body"])
        job_id = payload["job_id"]
        job = get_job(job_id)
        if not job or job.get("status") in {"completed", "failed"}:
            continue

        files = payload.get("files", [])
        save_job({**job, "status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()})
        images = []
        try:
            total_size = 0
            for file in files:
                head = s3.head_object(Bucket=bucket, Key=file["key"])
                size = int(head.get("ContentLength", 0))
                if size == 0:
                    raise ValueError(f"{file['filename']} is empty")
                if head.get("ContentType") != file["content_type"]:
                    raise ValueError(f"{file['filename']} has an unexpected content type")
                if size > 12 * 1024 * 1024:
                    raise ValueError(f"{file['filename']} exceeds the 12 MB limit")
                total_size += size
                if total_size > 48 * 1024 * 1024:
                    raise ValueError("Combined images exceed the 48 MB limit")
                uploaded = s3.get_object(Bucket=bucket, Key=file["key"])
                images.append((uploaded["Body"].read(), file["content_type"], file["filename"]))

            scan = _run_scan_group(images)
            save_job({**job, "status": "completed", "scan_id": scan["scan_id"], "updated_at": datetime.now(timezone.utc).isoformat()})
        except Exception:
            logger.exception("Scan job %s failed", job_id)
            save_job({**job, "status": "failed", "error": "Image analysis failed. Check the photos and retry.", "updated_at": datetime.now(timezone.utc).isoformat()})
        finally:
            for file in files:
                try:
                    s3.delete_object(Bucket=bucket, Key=file["key"])
                except Exception:
                    logger.exception("Could not delete temporary image for job %s", job_id)

    return {"batchItemFailures": []}
