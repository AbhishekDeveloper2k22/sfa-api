import re
from typing import Any, Dict, List, Optional

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class AttendanceConfigError(Exception):
    """Domain error for attendance configuration operations."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "VALIDATION_FAILED",
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class AttendanceConfigService:
    """Service layer for attendance configuration per tenant."""

    _TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    _ALLOWED_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    _SHIFT_NAME_LIMIT = 100
    _LOCATION_NAME_LIMIT = 100

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------
    def get_config(self, tenant_id: str) -> Dict[str, Any]:
        collection = self._get_collection(tenant_id)
        doc = collection.find_one({"tenant_id": tenant_id})
        if not doc:
            raise AttendanceConfigError(
                "Attendance configuration not found",
                status_code=404,
                code="NOT_FOUND",
            )
        return self._sanitize(doc)

    def save_config(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise AttendanceConfigError(
                "Payload must be an object",
                errors=[{"field": "payload", "message": "Payload must be an object"}],
            )

        collection = self._get_collection(tenant_id)
        existing = collection.find_one({"tenant_id": tenant_id})
        validated = self._validate_payload(payload, existing or {})

        doc = {
            "tenant_id": tenant_id,
            **validated,
        }

        if existing:
            updated_audit = build_audit_fields(prefix="updated", by=actor)
            doc.update(updated_audit)
            history_entry = self._history_from_audit("updated", updated_audit)
            collection.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": doc,
                    "$push": {"history": history_entry},
                },
            )
            existing.update(doc)
            existing.setdefault("history", []).append(history_entry)
            saved = existing
        else:
            created_audit = build_audit_fields(prefix="created", by=actor)
            updated_audit = build_audit_fields(prefix="updated", by=actor)
            doc.update(created_audit)
            doc.update(updated_audit)
            doc["history"] = [self._history_from_audit("created", created_audit)]
            insert_result = collection.insert_one(doc)
            doc["_id"] = insert_result.inserted_id
            saved = doc

        return self._sanitize(saved)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def _validate_payload(self, data: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
        validated: Dict[str, Any] = {}
        validated["work_week"] = self._validate_work_week(data.get("work_week"))
        validated["default_shift"] = self._validate_default_shift(data.get("default_shift"))
        validated["shifts"] = self._validate_shifts(
            data.get("shifts", []), existing.get("shifts", [])
        )
        validated["late_mark"] = self._validate_late_mark(data.get("late_mark"))
        validated["early_out"] = self._validate_early_out(data.get("early_out"))
        validated["overtime"] = self._validate_overtime(data.get("overtime"))
        validated["geo_fence"] = self._validate_geo_fence(data.get("geo_fence"))
        validated["locations"] = self._validate_locations(
            data.get("locations", []),
            existing.get("locations", []),
            validated["geo_fence"],
        )
        validated["selfie_attendance"] = self._validate_selfie(data.get("selfie_attendance"))
        validated["manual_attendance"] = self._validate_manual(data.get("manual_attendance"))
        return validated

    def _validate_work_week(self, value: Any) -> List[str]:
        if not isinstance(value, list) or not value:
            raise AttendanceConfigError(
                "At least one working day must be selected",
                errors=[{"field": "work_week", "message": "At least one working day must be selected"}],
            )
        normalized = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                raise AttendanceConfigError(
                    "Invalid day provided",
                    errors=[{"field": "work_week", "message": "All entries must be strings"}],
                )
            day = item.lower().strip()
            if day not in self._ALLOWED_DAYS:
                raise AttendanceConfigError(
                    "Invalid day provided",
                    errors=[{"field": "work_week", "message": f"Invalid day '{item}'"}],
                )
            if day in seen:
                raise AttendanceConfigError(
                    "Duplicate day provided",
                    errors=[{"field": "work_week", "message": f"Duplicate day '{day}'"}],
                )
            seen.add(day)
            normalized.append(day)
        return normalized

    def _validate_default_shift(self, value: Any) -> Dict[str, Any]:
        shift = self._require_dict(value, "default_shift")
        name = self._require_str(shift.get("name"), "default_shift.name", self._SHIFT_NAME_LIMIT)
        start = self._require_time(shift.get("start"), "default_shift.start")
        end = self._require_time(shift.get("end"), "default_shift.end")
        break_minutes = self._require_int_range(shift.get("break_minutes"), "default_shift.break_minutes", 0, 480)
        self._validate_shift_timings(start, end, "default_shift")
        return {
            "name": name,
            "start": start,
            "end": end,
            "break_minutes": break_minutes,
        }

    def _validate_shifts(self, shifts: Any, existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if shifts is None:
            return []
        if not isinstance(shifts, list):
            raise AttendanceConfigError(
                "Shifts must be an array",
                errors=[{"field": "shifts", "message": "Shifts must be an array"}],
            )
        existing_ids = [item.get("id") for item in existing if isinstance(item.get("id"), int)]
        next_id = (max(existing_ids) if existing_ids else 0) + 1
        names_seen = set()
        validated: List[Dict[str, Any]] = []
        for idx, raw in enumerate(shifts):
            shift = self._require_dict(raw, f"shifts[{idx}]")
            shift_id = shift.get("id")
            if shift_id is not None:
                if not isinstance(shift_id, int) or shift_id <= 0:
                    raise AttendanceConfigError(
                        "Shift id must be a positive integer",
                        errors=[{"field": f"shifts[{idx}].id", "message": "Shift id must be a positive integer"}],
                    )
            else:
                shift_id = next_id
                next_id += 1

            name = self._require_str(shift.get("name"), f"shifts[{idx}].name", self._SHIFT_NAME_LIMIT)
            key_name = name.lower()
            if key_name in names_seen:
                raise AttendanceConfigError(
                    "Shift names must be unique",
                    errors=[{"field": f"shifts[{idx}].name", "message": "Shift names must be unique"}],
                )
            names_seen.add(key_name)

            start = self._require_time(shift.get("start"), f"shifts[{idx}].start")
            end = self._require_time(shift.get("end"), f"shifts[{idx}].end")
            self._validate_shift_timings(start, end, f"shifts[{idx}]")

            late_buffer = self._require_int_range(shift.get("late_buffer"), f"shifts[{idx}].late_buffer", 0, 60)
            early_buffer = self._require_int_range(shift.get("early_buffer"), f"shifts[{idx}].early_buffer", 0, 60)

            validated.append(
                {
                    "id": shift_id,
                    "name": name,
                    "start": start,
                    "end": end,
                    "late_buffer": late_buffer,
                    "early_buffer": early_buffer,
                }
            )
        return validated

    def _validate_late_mark(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "late_mark")
        enabled = self._require_bool(section.get("enabled"), "late_mark.enabled")
        if not enabled:
            return {"enabled": False}
        late_after = self._require_int_range(section.get("late_after_minutes"), "late_mark.late_after_minutes", 1, 120)
        deduction = self._require_enum(section.get("deduction_mode"), "late_mark.deduction_mode", ["none", "half_day", "lop"])
        threshold = self._require_int_range(section.get("late_threshold"), "late_mark.late_threshold", 1, 30)
        return {
            "enabled": True,
            "late_after_minutes": late_after,
            "deduction_mode": deduction,
            "late_threshold": threshold,
        }

    def _validate_early_out(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "early_out")
        enabled = self._require_bool(section.get("enabled"), "early_out.enabled")
        if not enabled:
            return {"enabled": False}
        before_minutes = self._require_int_range(section.get("before_minutes"), "early_out.before_minutes", 1, 120)
        deduction = self._require_enum(section.get("deduction_mode"), "early_out.deduction_mode", ["none", "half_day", "lop"])
        return {
            "enabled": True,
            "before_minutes": before_minutes,
            "deduction_mode": deduction,
        }

    def _validate_overtime(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "overtime")
        enabled = self._require_bool(section.get("enabled"), "overtime.enabled")
        if not enabled:
            return {"enabled": False}
        min_minutes = self._require_int_range(section.get("min_ot_minutes"), "overtime.min_ot_minutes", 15, 480)
        approval_required = self._require_bool(section.get("approval_required"), "overtime.approval_required")
        return {
            "enabled": True,
            "min_ot_minutes": min_minutes,
            "approval_required": approval_required,
        }

    def _validate_geo_fence(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "geo_fence")
        enabled = self._require_bool(section.get("enabled"), "geo_fence.enabled")
        if not enabled:
            return {"enabled": False}
        radius = self._require_int_range(section.get("radius"), "geo_fence.radius", 10, 10000)
        lat = self._require_float_range(section.get("lat"), "geo_fence.lat", -90, 90)
        lng = self._require_float_range(section.get("lng"), "geo_fence.lng", -180, 180)
        return {
            "enabled": True,
            "radius": radius,
            "lat": lat,
            "lng": lng,
        }

    def _validate_locations(
        self,
        locations: Any,
        existing: List[Dict[str, Any]],
        geo_fence: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if not geo_fence.get("enabled"):
            return []
        if not isinstance(locations, list) or not locations:
            raise AttendanceConfigError(
                "At least one location is required when geo-fence is enabled",
                errors=[{"field": "locations", "message": "Provide at least one location"}],
            )
        existing_ids = [item.get("id") for item in existing if isinstance(item.get("id"), int)]
        next_id = (max(existing_ids) if existing_ids else 0) + 1
        names_seen = set()
        validated: List[Dict[str, Any]] = []
        for idx, raw in enumerate(locations):
            location = self._require_dict(raw, f"locations[{idx}]")
            location_id = location.get("id")
            if location_id is not None:
                if not isinstance(location_id, int) or location_id <= 0:
                    raise AttendanceConfigError(
                        "Location id must be a positive integer",
                        errors=[{"field": f"locations[{idx}].id", "message": "Location id must be a positive integer"}],
                    )
            else:
                location_id = next_id
                next_id += 1

            name = self._require_str(location.get("name"), f"locations[{idx}].name", self._LOCATION_NAME_LIMIT)
            key_name = name.lower()
            if key_name in names_seen:
                raise AttendanceConfigError(
                    "Location names must be unique",
                    errors=[{"field": f"locations[{idx}].name", "message": "Location names must be unique"}],
                )
            names_seen.add(key_name)

            lat = self._require_float_range(location.get("lat"), f"locations[{idx}].lat", -90, 90)
            lng = self._require_float_range(location.get("lng"), f"locations[{idx}].lng", -180, 180)
            radius = self._require_int_range(location.get("radius"), f"locations[{idx}].radius", 10, 10000)

            validated.append(
                {
                    "id": location_id,
                    "name": name,
                    "lat": lat,
                    "lng": lng,
                    "radius": radius,
                }
            )
        return validated

    def _validate_selfie(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "selfie_attendance")
        enabled = self._require_bool(section.get("enabled"), "selfie_attendance.enabled")
        face_check = False
        if enabled:
            face_check = self._require_bool(section.get("face_check"), "selfie_attendance.face_check")
        return {
            "enabled": enabled,
            "face_check": face_check if enabled else False,
        }

    def _validate_manual(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "manual_attendance")
        enabled = self._require_bool(section.get("enabled"), "manual_attendance.enabled")
        if not enabled:
            return {"enabled": False}
        approver = self._require_enum(section.get("approver"), "manual_attendance.approver", ["manager", "hr", "both"])
        auto_days = self._require_int_range(section.get("auto_approve_days"), "manual_attendance.auto_approve_days", 0, 30)
        return {
            "enabled": True,
            "approver": approver,
            "auto_approve_days": auto_days,
        }

    # ------------------------------------------------------------------
    # Primitive validators
    # ------------------------------------------------------------------
    def _require_dict(self, value: Any, field: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise AttendanceConfigError(
                f"{field} must be an object",
                errors=[{"field": field, "message": f"{field} must be an object"}],
            )
        return value

    def _require_str(self, value: Any, field: str, max_length: int) -> str:
        if not isinstance(value, str) or not value.strip():
            raise AttendanceConfigError(
                f"{field} is required",
                errors=[{"field": field, "message": f"{field} is required"}],
            )
        value = value.strip()
        if len(value) > max_length:
            raise AttendanceConfigError(
                f"{field} must be at most {max_length} characters",
                errors=[{"field": field, "message": f"{field} must be at most {max_length} characters"}],
            )
        return value

    def _require_time(self, value: Any, field: str) -> str:
        if not isinstance(value, str) or not self._TIME_PATTERN.match(value):
            raise AttendanceConfigError(
                f"{field} must be in HH:MM format",
                errors=[{"field": field, "message": "Time must be in HH:MM format"}],
            )
        return value

    def _require_int_range(self, value: Any, field: str, min_value: int, max_value: int) -> int:
        if not isinstance(value, int):
            raise AttendanceConfigError(
                f"{field} must be an integer",
                errors=[{"field": field, "message": f"{field} must be an integer"}],
            )
        if not (min_value <= value <= max_value):
            raise AttendanceConfigError(
                f"{field} must be between {min_value} and {max_value}",
                errors=[{"field": field, "message": f"{field} must be between {min_value} and {max_value}"}],
            )
        return value

    def _require_float_range(self, value: Any, field: str, min_value: float, max_value: float) -> float:
        try:
            float_value = float(value)
        except (TypeError, ValueError):
            raise AttendanceConfigError(
                f"{field} must be a number",
                errors=[{"field": field, "message": f"{field} must be a number"}],
            )
        if not (min_value <= float_value <= max_value):
            raise AttendanceConfigError(
                f"{field} must be between {min_value} and {max_value}",
                errors=[{"field": field, "message": f"{field} must be between {min_value} and {max_value}"}],
            )
        return float_value

    def _require_bool(self, value: Any, field: str) -> bool:
        if not isinstance(value, bool):
            raise AttendanceConfigError(
                f"{field} must be a boolean",
                errors=[{"field": field, "message": f"{field} must be a boolean"}],
            )
        return value

    def _require_enum(self, value: Any, field: str, allowed: List[str]) -> str:
        if not isinstance(value, str):
            raise AttendanceConfigError(
                f"{field} must be one of {allowed}",
                errors=[{"field": field, "message": f"{field} must be one of {allowed}"}],
            )
        value_lower = value.lower()
        if value_lower not in allowed:
            raise AttendanceConfigError(
                f"{field} must be one of {allowed}",
                errors=[{"field": field, "message": f"{field} must be one of {allowed}"}],
            )
        return value_lower

    def _validate_shift_timings(self, start: str, end: str, field_prefix: str):
        if start == end:
            raise AttendanceConfigError(
                "Shift start and end time cannot be the same",
                errors=[{"field": f"{field_prefix}.start", "message": "Start time must differ from end time"}],
            )

    def _require_bool(self, value: Any, field: str) -> bool:
        if not isinstance(value, bool):
            raise AttendanceConfigError(
                f"{field} must be a boolean",
                errors=[{"field": field, "message": f"{field} must be a boolean"}],
            )
        return value

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(doc)
        clean["id"] = str(clean.pop("_id"))
        return clean

    def _get_collection(self, tenant_id: str):
        tenant_db = self.client[tenant_id]
        return tenant_db["attendance_config"]

    def _history_from_audit(self, prefix: str, audit_fields: Dict[str, Any], action: Optional[str] = None) -> Dict[str, Any]:
        action = action or prefix
        return {
            "action": action,
            "by": audit_fields.get(f"{prefix}_by"),
            "at": audit_fields.get(f"{prefix}_at"),
            "time": audit_fields.get(f"{prefix}_time"),
        }
