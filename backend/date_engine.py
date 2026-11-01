"""Normalize packaging month/year and date strings for display and rule checks."""
from datetime import datetime
import re

MONTHS = {m.lower(): i for i, m in enumerate(("January February March April May June July August September October November December").split(), 1)}

def normalize_date(value):
    if not value or not isinstance(value, str):
        return {"raw": value, "normalized": None}
    raw = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%Y", "%m-%Y", "%Y/%m", "%Y-%m"):
        try:
            parsed = datetime.strptime(raw, fmt)
        except ValueError:
            parsed = None
        if parsed:
            return {"raw": raw, "normalized": parsed.isoformat() if "%d" in fmt else parsed.strftime("%Y-%m")}
    match = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b", raw, re.I)
    if match:
        return {"raw": raw, "normalized": f"{int(match.group(2)):04d}-{MONTHS[match.group(1).lower()]:02d}"}
    match = re.search(r"\b(\d{1,2})[./-](\d{4})\b", raw)
    if match and 1 <= int(match.group(1)) <= 12:
        return {"raw": raw, "normalized": f"{int(match.group(2)):04d}-{int(match.group(1)):02d}"}
    return {"raw": raw, "normalized": None}

def normalize_dates(data):
    result = dict(data)
    result["date_values"] = {"pack_date": normalize_date(data.get("pack_date")), "expiry_date": normalize_date(data.get("expiry_date"))}
    return result
