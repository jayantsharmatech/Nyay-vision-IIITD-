"""SQLite persistence plus an offline queue table for later synchronization."""
import json
import os
import sqlite3
from functools import lru_cache
from pathlib import Path
from settings import settings

DB_PATH = Path(__file__).parent / settings.database_path

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=1)
def _dynamodb_table():
    if not settings.dynamodb_table:
        return None
    import boto3
    region = settings.aws_region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or None
    resource = boto3.resource("dynamodb", region_name=region)
    return resource.Table(settings.dynamodb_table)

def initialize():
    if _dynamodb_table():
        return
    with _connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS scans (scan_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS offline_queue (queue_id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, synced INTEGER DEFAULT 0)")

def save_scan(record):
    table = _dynamodb_table()
    if table:
        table.put_item(Item={
            "scan_id": record["scan_id"],
            "history_partition": "SCANS",
            "history_sort": f"{record['created_at']}#{record['scan_id']}",
            "payload": json.dumps(record, ensure_ascii=False, separators=(",", ":")),
        })
        return
    with _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO scans(scan_id, created_at, payload) VALUES (?, ?, ?)", (record["scan_id"], record["created_at"], json.dumps(record)))

def get_scan(scan_id):
    table = _dynamodb_table()
    if table:
        item = table.get_item(Key={"scan_id": scan_id}, ConsistentRead=True).get("Item")
        return json.loads(item["payload"]) if item else None
    with _connect() as conn:
        row = conn.execute("SELECT payload FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
    return json.loads(row["payload"]) if row else None

def list_scans(limit=100):
    table = _dynamodb_table()
    if table:
        from boto3.dynamodb.conditions import Key
        records = []
        query = {
            "IndexName": "history-index",
            "KeyConditionExpression": Key("history_partition").eq("SCANS"),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        while len(records) < limit:
            page = table.query(**query)
            records.extend(json.loads(item["payload"]) for item in page.get("Items", []))
            key = page.get("LastEvaluatedKey")
            if not key:
                break
            query["ExclusiveStartKey"] = key
            query["Limit"] = limit - len(records)
        return records[:limit]
    with _connect() as conn:
        rows = conn.execute("SELECT payload FROM scans ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(row["payload"]) for row in rows]

def queue_offline(payload):
    with _connect() as conn:
        conn.execute("INSERT INTO offline_queue(payload) VALUES (?)", (json.dumps(payload),))

def pending_queue():
    with _connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM offline_queue WHERE synced = 0 ORDER BY queue_id").fetchall()]
