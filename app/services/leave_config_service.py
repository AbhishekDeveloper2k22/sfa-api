import re
from typing import Any, Dict, List, Optional

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class LeaveConfigError(Exception):
    """Domain error for leave configuration operations."""

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


class LeaveConfigService:
    """Service layer for leave configuration per tenant."""

    _LEAVE_CODE_PATTERN = re.compile(r"^[A-Z0-9]{1,10}$")
    _LEAVE_NAME_LIMIT = 100

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------
    def get_config(self, tenant_id: str) -> Dict[str, Any]:
        collection = self._get_collection(tenant_id)
        doc = collection.find_one({"tenant_id": tenant_id})
        if not doc:
            raise LeaveConfigError(
                "Leave configuration not found",
                status_code=404,
                code="NOT_FOUND",
            )
        return self._sanitize(doc)

    def save_config(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise LeaveConfigError(
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
        validated["leave_types"] = self._validate_leave_types(
            data.get("leave_types", []), existing.get("leave_types", [])
        )
        validated["approval_workflow"] = self._validate_workflow(data.get("approval_workflow"))
        return validated

    def _validate_leave_types(self, leave_types: Any, existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if leave_types is None:
            return []
        if not isinstance(leave_types, list):
            raise LeaveConfigError(
                "leave_types must be an array",
                errors=[{"field": "leave_types", "message": "leave_types must be an array"}],
            )
        existing_ids = [item.get("id") for item in existing if isinstance(item.get("id"), int)]
        next_id = (max(existing_ids) if existing_ids else 0) + 1
        codes_seen = set()
        names_seen = set()
        validated: List[Dict[str, Any]] = []
        for idx, raw in enumerate(leave_types):
            leave = self._require_dict(raw, f"leave_types[{idx}]")
            leave_id = leave.get("id")
            if leave_id is not None:
                if not isinstance(leave_id, int) or leave_id <= 0:
                    raise LeaveConfigError(
                        "Leave type id must be a positive integer",
                        errors=[{"field": f"leave_types[{idx}].id", "message": "Leave type id must be a positive integer"}],
                    )
            else:
                leave_id = next_id
                next_id += 1

            name = self._require_str(leave.get("name"), f"leave_types[{idx}].name", self._LEAVE_NAME_LIMIT)
            key_name = name.lower()
            if key_name in names_seen:
                raise LeaveConfigError(
                    "Leave names must be unique",
                    errors=[{"field": f"leave_types[{idx}].name", "message": "Leave names must be unique"}],
                )
            names_seen.add(key_name)

            code = leave.get("code")
            if not isinstance(code, str) or not self._LEAVE_CODE_PATTERN.match(code.upper()):
                raise LeaveConfigError(
                    "Leave code must be uppercase alphanumeric up to 10 characters",
                    errors=[{"field": f"leave_types[{idx}].code", "message": "Leave code must be uppercase alphanumeric up to 10 characters"}],
                )
            normalized_code = code.upper()
            if normalized_code in codes_seen:
                raise LeaveConfigError(
                    "Leave codes must be unique",
                    errors=[{"field": f"leave_types[{idx}].code", "message": "Leave codes must be unique"}],
                )
            codes_seen.add(normalized_code)

            max_per_year = self._require_int_range(
                leave.get("max_per_year"), f"leave_types[{idx}].max_per_year", 0, 365
            )

            is_paid = self._require_bool(leave.get("is_paid"), f"leave_types[{idx}].is_paid")
            is_encashable = self._require_bool(leave.get("is_encashable"), f"leave_types[{idx}].is_encashable")
            allow_half_day = self._require_bool(leave.get("allow_half_day"), f"leave_types[{idx}].allow_half_day")
            attachment_required = self._require_bool(
                leave.get("attachment_required"), f"leave_types[{idx}].attachment_required"
            )

            validated.append(
                {
                    "id": leave_id,
                    "name": name,
                    "code": normalized_code,
                    "max_per_year": max_per_year,
                    "is_paid": is_paid,
                    "is_encashable": is_encashable,
                    "allow_half_day": allow_half_day,
                    "attachment_required": attachment_required,
                }
            )
        return validated

    def _validate_workflow(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "approval_workflow")
        workflow_type = self._require_enum(
            section.get("type"),
            "approval_workflow.type",
            ["manager", "manager_hr", "hr"],
        )
        auto_days = self._require_int_range(
            section.get("auto_approve_if_days_less_than"),
            "approval_workflow.auto_approve_if_days_less_than",
            0,
            30,
        )
        escalation = self._require_int_range(
            section.get("escalation_hours"),
            "approval_workflow.escalation_hours",
            1,
            168,
        )
        return {
            "type": workflow_type,
            "auto_approve_if_days_less_than": auto_days,
            "escalation_hours": escalation,
        }

    # ------------------------------------------------------------------
    # Primitive validators
    # ------------------------------------------------------------------
    def _require_dict(self, value: Any, field: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise LeaveConfigError(
                f"{field} must be an object",
                errors=[{"field": field, "message": f"{field} must be an object"}],
            )
        return value

    def _require_str(self, value: Any, field: str, max_length: int) -> str:
        if not isinstance(value, str) or not value.strip():
            raise LeaveConfigError(
                f"{field} is required",
                errors=[{"field": field, "message": f"{field} is required"}],
            )
        value = value.strip()
        if len(value) > max_length:
            raise LeaveConfigError(
                f"{field} must be at most {max_length} characters",
                errors=[{"field": field, "message": f"{field} must be at most {max_length} characters"}],
            )
        return value

    def _require_int_range(self, value: Any, field: str, min_value: int, max_value: int) -> int:
        if not isinstance(value, int):
            raise LeaveConfigError(
                f"{field} must be an integer",
                errors=[{"field": field, "message": f"{field} must be an integer"}],
            )
        if not (min_value <= value <= max_value):
            raise LeaveConfigError(
                f"{field} must be between {min_value} and {max_value}",
                errors=[{"field": field, "message": f"{field} must be between {min_value} and {max_value}"}],
            )
        return value

    def _require_bool(self, value: Any, field: str) -> bool:
        if not isinstance(value, bool):
            raise LeaveConfigError(
                f"{field} must be a boolean",
                errors=[{"field": field, "message": f"{field} must be a boolean"}],
            )
        return value

    def _require_enum(self, value: Any, field: str, allowed: List[str]) -> str:
        if not isinstance(value, str):
            raise LeaveConfigError(
                f"{field} must be one of {allowed}",
                errors=[{"field": field, "message": f"{field} must be one of {allowed}"}],
            )
        value_lower = value.lower()
        if value_lower not in allowed:
            raise LeaveConfigError(
                f"{field} must be one of {allowed}",
                errors=[{"field": field, "message": f"{field} must be one of {allowed}"}],
            )
        return value_lower

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(doc)
        clean["id"] = str(clean.pop("_id"))
        return clean

    def _get_collection(self, tenant_id: str):
        tenant_db = self.client[tenant_id]
        return tenant_db["leave_config"]

    def _history_from_audit(self, prefix: str, audit_fields: Dict[str, Any], action: Optional[str] = None) -> Dict[str, Any]:
        action = action or prefix
        return {
            "action": action,
            "by": audit_fields.get(f"{prefix}_by"),
            "at": audit_fields.get(f"{prefix}_at"),
            "time": audit_fields.get(f"{prefix}_time"),
        }
