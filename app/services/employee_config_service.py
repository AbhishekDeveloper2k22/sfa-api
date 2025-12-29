import re
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class EmployeeConfigError(Exception):
    """Domain error for employee configuration operations."""

    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class EmployeeConfigService:
    """Service layer for tenant-scoped departments and designations."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # Departments
    # ------------------------------------------------------------------
    def list_departments(self, tenant_id: str) -> Tuple[List[Dict[str, Any]], int]:
        departments, _, _ = self._get_collections(tenant_id)
        docs = list(
            departments.find({"tenant_id": tenant_id, "del": 0}).sort("created_at", -1)
        )
        return [self._sanitize(doc) for doc in docs], len(docs)

    def create_department(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        departments, _, _ = self._get_collections(tenant_id)
        code = self._normalize_code(payload.get("code"))
        name = self._require(payload.get("name"), "name")
        head = self._optional_str(payload.get("head"))

        self._ensure_department_code_unique(departments, tenant_id, code)

        doc = {
            "tenant_id": tenant_id,
            "code": code,
            "name": name,
            "head": head,
            "del": 0,
        }
        created_audit = build_audit_fields(prefix="created", by=actor)
        updated_audit = build_audit_fields(prefix="updated", by=actor)
        doc.update(created_audit)
        doc.update(updated_audit)
        doc["history"] = [self._history_from_audit("created", created_audit)]
        insert_result = departments.insert_one(doc)
        doc["_id"] = insert_result.inserted_id
        return self._sanitize(doc)

    def update_department(self, tenant_id: str, dept_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        departments, _, _ = self._get_collections(tenant_id)
        department = self._get_department_or_404(departments, tenant_id, dept_id)

        code = payload.get("code")
        if code is not None:
            code = self._normalize_code(code)
            if code != department["code"]:
                self._ensure_department_code_unique(departments, tenant_id, code)
        else:
            code = department["code"]

        name = payload.get("name", department["name"])
        if not name:
            raise EmployeeConfigError("Department name is required", errors=[{"field": "name", "message": "Department name is required"}])
        head = self._optional_str(payload.get("head", department.get("head")))

        updates = {
            "code": code,
            "name": name,
            "head": head,
        }
        updated_audit = build_audit_fields(prefix="updated", by=actor)
        updates.update(updated_audit)
        history_entry = self._history_from_audit("updated", updated_audit)

        departments.update_one(
            {"_id": department["_id"]},
            {
                "$set": updates,
                "$push": {"history": history_entry},
            },
        )

        department.update(updates)
        department.setdefault("history", []).append(history_entry)
        return self._sanitize(department)

    def delete_department(self, tenant_id: str, dept_id: str, actor: Optional[str]):
        departments, _, users = self._get_collections(tenant_id)
        department = self._get_department_or_404(departments, tenant_id, dept_id)
        if users.count_documents({"tenant_id": tenant_id, "department": department.get("name")}) > 0:
            raise EmployeeConfigError(
                "Cannot delete department. Employees are assigned to this department",
                status_code=409,
                code="CONFLICT",
            )

        updates = {
            "del": 1,
        }
        updated_audit = build_audit_fields(prefix="updated", by=actor)
        updates.update(updated_audit)
        history_entry = self._history_from_audit("updated", updated_audit, action="deleted")
        departments.update_one(
            {"_id": department["_id"]},
            {
                "$set": updates,
                "$push": {"history": history_entry},
            },
        )

    # ------------------------------------------------------------------
    # Designations
    # ------------------------------------------------------------------
    def list_designations(self, tenant_id: str, department: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        _, designations, _ = self._get_collections(tenant_id)
        query: Dict[str, Any] = {"tenant_id": tenant_id}
        if department:
            query["department"] = department
        query["del"] = 0
        docs = list(designations.find(query).sort("created_at", -1))
        return [self._sanitize(doc) for doc in docs], len(docs)

    def create_designation(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        departments, designations, _ = self._get_collections(tenant_id)
        code = self._normalize_code(payload.get("code"))
        name = self._require(payload.get("name"), "name")
        dept_name = self._require(payload.get("department"), "department")
        level = self._require_level(payload.get("level"))

        self._ensure_designation_code_unique(designations, tenant_id, code)
        self._ensure_department_exists_if_needed(departments, tenant_id, dept_name)

        doc = {
            "tenant_id": tenant_id,
            "code": code,
            "name": name,
            "department": dept_name,
            "level": level,
            "del": 0,
        }
        created_audit = build_audit_fields(prefix="created", by=actor)
        updated_audit = build_audit_fields(prefix="updated", by=actor)
        doc.update(created_audit)
        doc.update(updated_audit)
        doc["history"] = [self._history_from_audit("created", created_audit)]
        insert_result = designations.insert_one(doc)
        doc["_id"] = insert_result.inserted_id
        return self._sanitize(doc)

    def update_designation(self, tenant_id: str, designation_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        departments, designations, _ = self._get_collections(tenant_id)
        designation = self._get_designation_or_404(designations, tenant_id, designation_id)

        code = payload.get("code")
        if code is not None:
            code = self._normalize_code(code)
            if code != designation["code"]:
                self._ensure_designation_code_unique(designations, tenant_id, code)
        else:
            code = designation["code"]

        name = payload.get("name", designation["name"])
        if not name:
            raise EmployeeConfigError("Designation name is required", errors=[{"field": "name", "message": "Designation name is required"}])

        dept_name = payload.get("department", designation.get("department"))
        self._ensure_department_exists_if_needed(departments, tenant_id, dept_name)

        level = payload.get("level", designation.get("level"))
        level = self._require_level(level)

        updates = {
            "code": code,
            "name": name,
            "department": dept_name,
            "level": level,
        }
        updated_audit = build_audit_fields(prefix="updated", by=actor)
        updates.update(updated_audit)
        history_entry = self._history_from_audit("updated", updated_audit)

        designations.update_one(
            {"_id": designation["_id"]},
            {
                "$set": updates,
                "$push": {"history": history_entry},
            },
        )
        designation.update(updates)
        designation.setdefault("history", []).append(history_entry)
        return self._sanitize(designation)

    def delete_designation(self, tenant_id: str, designation_id: str, actor: Optional[str]):
        _, designations, users = self._get_collections(tenant_id)
        designation = self._get_designation_or_404(designations, tenant_id, designation_id)
        if users.count_documents({"tenant_id": tenant_id, "designation": designation.get("name")}) > 0:
            raise EmployeeConfigError(
                "Cannot delete designation. Employees are assigned to this designation",
                status_code=409,
                code="CONFLICT",
            )

        updates = {"del": 1}
        updated_audit = build_audit_fields(prefix="updated", by=actor)
        updates.update(updated_audit)
        history_entry = self._history_from_audit("updated", updated_audit, action="deleted")
        designations.update_one(
            {"_id": designation["_id"]},
            {
                "$set": updates,
                "$push": {"history": history_entry},
            },
        )

    # ------------------------------------------------------------------
    # Bulk save
    # ------------------------------------------------------------------
    def bulk_save(self, tenant_id: str, data: Dict[str, Any], actor: Optional[str]) -> Dict[str, int]:
        departments_payload = data.get("departments", [])
        designations_payload = data.get("designations", [])

        stats = {
            "departments_created": 0,
            "departments_updated": 0,
            "designations_created": 0,
            "designations_updated": 0,
        }

        for dept in departments_payload:
            if dept.get("id"):
                self.update_department(tenant_id, dept["id"], dept, actor)
                stats["departments_updated"] += 1
            else:
                self.create_department(tenant_id, dept, actor)
                stats["departments_created"] += 1

        for des in designations_payload:
            if des.get("id"):
                self.update_designation(tenant_id, des["id"], des, actor)
                stats["designations_updated"] += 1
            else:
                self.create_designation(tenant_id, des, actor)
                stats["designations_created"] += 1

        return stats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    def _normalize_code(self, value: Optional[str]) -> str:
        if not value:
            raise EmployeeConfigError(
                "Code is required",
                errors=[{"field": "code", "message": "Code is required"}],
            )
        value = value.strip().upper()
        if len(value) > 15 or not re.match(r"^[A-Z0-9_]+$", value):
            raise EmployeeConfigError(
                "Code must be alphanumeric/underscore and up to 15 characters",
                errors=[{"field": "code", "message": "Code must be alphanumeric/underscore and up to 15 characters"}],
            )
        return value

    def _ensure_department_code_unique(self, departments, tenant_id: str, code: str):
        if departments.find_one({"tenant_id": tenant_id, "code": code}):
            raise EmployeeConfigError(
                "Department code already exists",
                status_code=409,
                code="CONFLICT",
            )

    def _ensure_designation_code_unique(self, designations, tenant_id: str, code: str):
        if designations.find_one({"tenant_id": tenant_id, "code": code}):
            raise EmployeeConfigError(
                "Designation code already exists",
                status_code=409,
                code="CONFLICT",
            )

    def _ensure_department_exists_if_needed(self, departments, tenant_id: str, dept_name: Optional[str]):
        if not dept_name or dept_name == "All":
            return
        exists = departments.find_one({"tenant_id": tenant_id, "name": dept_name, "status": {"$ne": "inactive"}})
        if not exists:
            raise EmployeeConfigError(
                "Department does not exist",
                errors=[{"field": "department", "message": "Department does not exist"}],
            )

    def _require_level(self, level: Optional[int]) -> int:
        if level is None:
            raise EmployeeConfigError(
                "Level is required",
                errors=[{"field": "level", "message": "Level is required"}],
            )
        try:
            level = int(level)
        except (TypeError, ValueError):
            raise EmployeeConfigError(
                "Level must be a number between 1 and 10",
                errors=[{"field": "level", "message": "Level must be a number between 1 and 10"}],
            )
        if not 1 <= level <= 10:
            raise EmployeeConfigError(
                "Level must be between 1 and 10",
                errors=[{"field": "level", "message": "Level must be between 1 and 10"}],
            )
        return level

    def _get_department_or_404(self, departments, tenant_id: str, dept_id: str) -> Dict[str, Any]:
        try:
            object_id = ObjectId(dept_id)
        except Exception:
            raise EmployeeConfigError("Department not found", status_code=404, code="NOT_FOUND")
        doc = departments.find_one({"_id": object_id, "tenant_id": tenant_id})
        if not doc:
            raise EmployeeConfigError("Department not found", status_code=404, code="NOT_FOUND")
        return doc

    def _get_designation_or_404(self, designations, tenant_id: str, designation_id: str) -> Dict[str, Any]:
        try:
            object_id = ObjectId(designation_id)
        except Exception:
            raise EmployeeConfigError("Designation not found", status_code=404, code="NOT_FOUND")
        doc = designations.find_one({"_id": object_id, "tenant_id": tenant_id})
        if not doc:
            raise EmployeeConfigError("Designation not found", status_code=404, code="NOT_FOUND")
        return doc

    def _require(self, value: Optional[str], field: str) -> str:
        if value is None or str(value).strip() == "":
            raise EmployeeConfigError(
                f"{field} is required",
                errors=[{"field": field, "message": f"{field.capitalize()} is required"}],
            )
        value = str(value).strip()
        if field == "name" and len(value) > 100:
            raise EmployeeConfigError(
                "Name must be at most 100 characters",
                errors=[{"field": "name", "message": "Name must be at most 100 characters"}],
            )
        return value

    def _optional_str(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        if len(value) > 100:
            raise EmployeeConfigError(
                "Value must be at most 100 characters",
                errors=[{"message": "Value must be at most 100 characters"}],
            )
        return value

    def _history_from_audit(self, prefix: str, audit_fields: Dict[str, Any], action: Optional[str] = None) -> Dict[str, Any]:
        action = action or prefix
        return {
            "action": action,
            "by": audit_fields.get(f"{prefix}_by"),
            "at": audit_fields.get(f"{prefix}_at"),
            "time": audit_fields.get(f"{prefix}_time"),
        }

    def _get_collections(self, tenant_id: str):
        tenant_db = self.client[tenant_id]
        departments = tenant_db["tenant_departments"]
        designations = tenant_db["tenant_designations"]
        users = tenant_db["users"]
        return departments, designations, users
