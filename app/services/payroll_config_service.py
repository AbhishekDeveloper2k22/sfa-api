import re
from typing import Any, Dict, List, Optional

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class PayrollConfigError(Exception):
    """Domain error for payroll configuration operations."""

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


class PayrollConfigService:
    """Service layer for payroll configuration per tenant."""

    _COMPONENT_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{1,10}$")
    _COMPONENT_NAME_LIMIT = 100
    _DESCRIPTION_LIMIT = 500

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------
    def get_config(self, tenant_id: str) -> Dict[str, Any]:
        collection = self._get_collection(tenant_id)
        doc = collection.find_one({"tenant_id": tenant_id})
        if not doc:
            raise PayrollConfigError(
                "Payroll configuration not found",
                status_code=404,
                code="NOT_FOUND",
            )
        return self._sanitize(doc)

    def save_config(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise PayrollConfigError(
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
        validated["payroll_cycle"] = self._validate_payroll_cycle(data.get("payroll_cycle"))
        validated["salary_components"] = self._validate_salary_components(
            data.get("salary_components", []), existing.get("salary_components", [])
        )
        validated["statutory"] = self._validate_statutory(data.get("statutory"))
        return validated

    def _validate_payroll_cycle(self, value: Any) -> Dict[str, Any]:
        cycle = self._require_dict(value, "payroll_cycle")
        payroll_cycle = self._require_enum(
            cycle.get("payroll_cycle"),
            "payroll_cycle.payroll_cycle",
            ["monthly", "bi_weekly", "weekly"],
        )
        cutoff_day = self._require_int_range(cycle.get("cutoff_day"), "payroll_cycle.cutoff_day", 1, 31)
        pay_day = self._require_int_range(cycle.get("pay_day"), "payroll_cycle.pay_day", 1, 31)
        adjustment_rule = self._require_enum(
            cycle.get("adjustment_rule"),
            "payroll_cycle.adjustment_rule",
            ["previous_working_day", "next_working_day"],
        )
        return {
            "payroll_cycle": payroll_cycle,
            "cutoff_day": cutoff_day,
            "pay_day": pay_day,
            "adjustment_rule": adjustment_rule,
        }

    def _validate_salary_components(self, components: Any, existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(components, list) or not components:
            raise PayrollConfigError(
                "salary_components must be a non-empty array",
                errors=[{"field": "salary_components", "message": "Provide at least one component"}],
            )
        existing_ids = [item.get("id") for item in existing if isinstance(item.get("id"), int)]
        next_id = (max(existing_ids) if existing_ids else 0) + 1
        codes_seen = set()
        names_seen = set()
        validated: List[Dict[str, Any]] = []
        earnings_total = 0

        for idx, raw in enumerate(components):
            component = self._require_dict(raw, f"salary_components[{idx}]")
            component_id = component.get("id")
            if component_id is not None:
                if not isinstance(component_id, int) or component_id <= 0:
                    raise PayrollConfigError(
                        "Component id must be a positive integer",
                        errors=[{"field": f"salary_components[{idx}].id", "message": "Component id must be a positive integer"}],
                    )
            else:
                component_id = next_id
                next_id += 1

            code = component.get("code")
            if not isinstance(code, str) or not self._COMPONENT_CODE_PATTERN.match(code.upper()):
                raise PayrollConfigError(
                    "Component code must be uppercase alphanumeric (and underscore) up to 10 characters",
                    errors=[{"field": f"salary_components[{idx}].code", "message": "Component code must be uppercase alphanumeric (and underscore) up to 10 characters"}],
                )
            normalized_code = code.upper()
            if normalized_code in codes_seen:
                raise PayrollConfigError(
                    "Component codes must be unique",
                    errors=[{"field": f"salary_components[{idx}].code", "message": "Component codes must be unique"}],
                )
            codes_seen.add(normalized_code)

            name = self._require_str(component.get("name"), f"salary_components[{idx}].name", self._COMPONENT_NAME_LIMIT)
            name_key = name.lower()
            if name_key in names_seen:
                raise PayrollConfigError(
                    "Component names must be unique",
                    errors=[{"field": f"salary_components[{idx}].name", "message": "Component names must be unique"}],
                )
            names_seen.add(name_key)

            comp_type = self._require_enum(
                component.get("type"),
                f"salary_components[{idx}].type",
                ["earning", "deduction"],
            )
            percentage = self._require_int_range(
                component.get("percentage"),
                f"salary_components[{idx}].percentage",
                0,
                100,
            )
            description = component.get("description")
            if description is not None:
                if not isinstance(description, str):
                    raise PayrollConfigError(
                        "Description must be a string",
                        errors=[{"field": f"salary_components[{idx}].description", "message": "Description must be a string"}],
                    )
                if len(description.strip()) > self._DESCRIPTION_LIMIT:
                    raise PayrollConfigError(
                        "Description too long",
                        errors=[{"field": f"salary_components[{idx}].description", "message": f"Description must be at most {self._DESCRIPTION_LIMIT} characters"}],
                    )
                description = description.strip()
            else:
                description = None

            if comp_type == "earning":
                earnings_total += percentage

            validated.append(
                {
                    "id": component_id,
                    "code": normalized_code,
                    "name": name,
                    "type": comp_type,
                    "percentage": percentage,
                    "description": description,
                }
            )

        if earnings_total != 100:
            raise PayrollConfigError(
                "Total earnings percentage must equal 100%",
                errors=[{"field": "salary_components", "message": "Total earnings percentage must equal 100%"}],
                code="CONFLICT",
            )

        return validated

    def _validate_statutory(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "statutory")
        pf = self._validate_pf(section.get("pf"))
        esi = self._validate_esi(section.get("esi"))
        return {"pf": pf, "esi": esi}

    def _validate_pf(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "statutory.pf")
        enabled = self._require_bool(section.get("enabled"), "statutory.pf.enabled")
        if not enabled:
            return {"enabled": False}
        employee_percent = self._require_float_range(
            section.get("employee_percent"), "statutory.pf.employee_percent", 0, 100
        )
        employer_percent = self._require_float_range(
            section.get("employer_percent"), "statutory.pf.employer_percent", 0, 100
        )
        basic_cap = self._require_int_range(section.get("basic_cap"), "statutory.pf.basic_cap", 0, 50000)
        return {
            "enabled": True,
            "employee_percent": employee_percent,
            "employer_percent": employer_percent,
            "basic_cap": basic_cap,
        }

    def _validate_esi(self, value: Any) -> Dict[str, Any]:
        section = self._require_dict(value, "statutory.esi")
        enabled = self._require_bool(section.get("enabled"), "statutory.esi.enabled")
        if not enabled:
            return {"enabled": False}
        employee_percent = self._require_float_range(
            section.get("employee_percent"), "statutory.esi.employee_percent", 0, 5
        )
        employer_percent = self._require_float_range(
            section.get("employer_percent"), "statutory.esi.employer_percent", 0, 10
        )
        wage_limit = self._require_int_range(section.get("wage_limit"), "statutory.esi.wage_limit", 0, 50000)
        return {
            "enabled": True,
            "employee_percent": employee_percent,
            "employer_percent": employer_percent,
            "wage_limit": wage_limit,
        }

    # ------------------------------------------------------------------
    # Primitive validators
    # ------------------------------------------------------------------
    def _require_dict(self, value: Any, field: str) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise PayrollConfigError(
                f"{field} must be an object",
                errors=[{"field": field, "message": f"{field} must be an object"}],
            )
        return value

    def _require_str(self, value: Any, field: str, max_length: int) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PayrollConfigError(
                f"{field} is required",
                errors=[{"field": field, "message": f"{field} is required"}],
            )
        value = value.strip()
        if len(value) > max_length:
            raise PayrollConfigError(
                f"{field} must be at most {max_length} characters",
                errors=[{"field": field, "message": f"{field} must be at most {max_length} characters"}],
            )
        return value

    def _require_enum(self, value: Any, field: str, allowed: List[str]) -> str:
        if not isinstance(value, str):
            raise PayrollConfigError(
                f"{field} must be one of {allowed}",
                errors=[{"field": field, "message": f"{field} must be one of {allowed}"}],
            )
        value_lower = value.lower()
        if value_lower not in allowed:
            raise PayrollConfigError(
                f"{field} must be one of {allowed}",
                errors=[{"field": field, "message": f"{field} must be one of {allowed}"}],
            )
        return value_lower

    def _require_int_range(self, value: Any, field: str, min_value: int, max_value: int) -> int:
        if not isinstance(value, int):
            raise PayrollConfigError(
                f"{field} must be an integer",
                errors=[{"field": field, "message": f"{field} must be an integer"}],
            )
        if not (min_value <= value <= max_value):
            raise PayrollConfigError(
                f"{field} must be between {min_value} and {max_value}",
                errors=[{"field": field, "message": f"{field} must be between {min_value} and {max_value}"}],
            )
        return value

    def _require_float_range(self, value: Any, field: str, min_value: float, max_value: float) -> float:
        try:
            float_value = float(value)
        except (TypeError, ValueError):
            raise PayrollConfigError(
                f"{field} must be a number",
                errors=[{"field": field, "message": f"{field} must be a number"}],
            )
        if not (min_value <= float_value <= max_value):
            raise PayrollConfigError(
                f"{field} must be between {min_value} and {max_value}",
                errors=[{"field": field, "message": f"{field} must be between {min_value} and {max_value}"}],
            )
        return float_value

    def _require_bool(self, value: Any, field: str) -> bool:
        if not isinstance(value, bool):
            raise PayrollConfigError(
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
        return tenant_db["payroll_config"]

    def _history_from_audit(self, prefix: str, audit_fields: Dict[str, Any], action: Optional[str] = None) -> Dict[str, Any]:
        action = action or prefix
        return {
            "action": action,
            "by": audit_fields.get(f"{prefix}_by"),
            "at": audit_fields.get(f"{prefix}_at"),
            "time": audit_fields.get(f"{prefix}_time"),
        }
