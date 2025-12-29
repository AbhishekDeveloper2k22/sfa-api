from datetime import datetime
from typing import Optional, Dict, Any

import pytz


def build_audit_fields(
    prefix: str = "created",
    by: Optional[Any] = None,
    timezone: str = "Asia/Kolkata",
) -> Dict[str, Any]:
    """Build dynamic audit fields like created_at, created_time, created_by (or updated_*)."""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return {
        f"{prefix}_at": now.strftime("%Y-%m-%d"),
        f"{prefix}_time": now.strftime("%H:%M:%S"),
        f"{prefix}_by": by,
    }


def merge_audit_fields(
    doc: Dict[str, Any],
    prefix: str,
    by: Optional[Any],
    timezone: str = "Asia/Kolkata",
) -> Dict[str, Any]:
    """Merge audit fields into an existing document and return it."""
    doc.update(build_audit_fields(prefix=prefix, by=by, timezone=timezone))
    return doc
