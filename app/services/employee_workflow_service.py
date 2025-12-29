import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class EmployeeWorkflowError(Exception):
    """Domain error for employee workflow operations."""

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


class EmployeeWorkflowService:
    """Tenant scoped workflow for add/edit employee journey with drafts."""

    REQUIRED_SECTIONS = [
        "personal",
        "employment",
        "compensation",
        "bank_tax",
        "documents",
        "emergency_address",
    ]

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # Draft lifecycle
    # ------------------------------------------------------------------
    def save_step_one(
        self,
        tenant_id: str,
        user_id: str,
        personal: Dict[str, Any],
        draft_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._require_dict(personal, "personal")
        drafts = self._drafts(tenant_id)
        now = self._now()

        if draft_id:
            draft = self._get_draft_doc(tenant_id, draft_id)
            self._ensure_mutable(draft)
        else:
            draft_id = self._generate_draft_id()
            draft = {
                "draft_id": draft_id,
                "tenant_id": tenant_id,
                "status": "in_progress",
                "step_completed": 0,
                "next_step": 1,
                "history": [],
            }
            draft.update(build_audit_fields(prefix="created", by=user_id))
            draft.update(build_audit_fields(prefix="updated", by=user_id))
            drafts.insert_one(draft)

        updates = {
            "personal": personal,
            "step_completed": max(draft.get("step_completed", 0), 1),
            "next_step": 2,
        }
        updates.update(build_audit_fields(prefix="updated", by=user_id))
        self._push_history(drafts, draft_id, 1, user_id, now, details="Saved personal info")
        drafts.update_one(
            {"tenant_id": tenant_id, "draft_id": draft_id},
            {"$set": updates},
        )

        return {
            "draft_id": draft_id,
            "step_completed": updates["step_completed"],
            "next_step": updates["next_step"],
            "employee_id": draft.get("employee_id"),
        }

    def save_step(
        self,
        tenant_id: str,
        user_id: str,
        draft_id: str,
        section_key: str,
        section_payload: Dict[str, Any],
        step_number: int,
        next_step: int,
    ) -> Dict[str, Any]:
        self._require_dict(section_payload, section_key)
        draft = self._get_draft_doc(tenant_id, draft_id)
        self._ensure_mutable(draft)
        drafts = self._drafts(tenant_id)
        now = self._now()

        updates = {
            section_key: section_payload,
            "step_completed": max(draft.get("step_completed", 0), step_number),
            "next_step": next_step,
            "updated_at": now,
            "updated_by": user_id,
        }
        updates.update(build_audit_fields(prefix="updated", by=user_id))
        self._push_history(
            drafts,
            draft_id,
            step_number,
            user_id,
            now,
            details=f"Saved section {section_key}",
        )
        drafts.update_one(
            {"tenant_id": tenant_id, "draft_id": draft_id},
            {"$set": updates},
        )
        return {
            "draft_id": draft_id,
            "step_completed": updates["step_completed"],
            "next_step": updates["next_step"],
        }

    def save_documents(
        self,
        tenant_id: str,
        user_id: str,
        draft_id: str,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(documents, list) or not documents:
            raise EmployeeWorkflowError(
                "documents must be a non-empty array",
                errors=[{"field": "documents", "message": "Provide at least one document"}],
            )
        payload = {"documents": documents}
        return self.save_step(
            tenant_id,
            user_id,
            draft_id,
            "documents",
            payload,
            step_number=5,
            next_step=6,
        )

    def save_emergency_and_address(
        self,
        tenant_id: str,
        user_id: str,
        draft_id: str,
        emergency_address: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.save_step(
            tenant_id,
            user_id,
            draft_id,
            "emergency_address",
            emergency_address,
            step_number=6,
            next_step=None,
        )

    def complete_employee(self, tenant_id: str, user_id: str, draft_id: str) -> Dict[str, Any]:
        drafts = self._drafts(tenant_id)
        draft = self._get_draft_doc(tenant_id, draft_id)
        self._ensure_mutable(draft)

        missing = [section for section in self.REQUIRED_SECTIONS if not draft.get(section)]
        if missing:
            raise EmployeeWorkflowError(
                "All steps must be completed before final submission",
                status_code=422,
                errors=[{"field": section, "message": "Section missing"} for section in missing],
            )

        employees = self._employees(tenant_id)
        now = self._now()
        etag = self._generate_etag()
        employee_doc = {
            "tenant_id": tenant_id,
            "draft_id": draft_id,
            "personal": draft.get("personal"),
            "employment": draft.get("employment"),
            "compensation": draft.get("compensation"),
            "bank_tax": draft.get("bank_tax"),
            "documents": draft.get("documents"),
            "emergency_address": draft.get("emergency_address"),
            "status": "active",
            "version": 1,
            "etag": etag,
            "created_by": draft.get("created_by"),
            "created_at": draft.get("created_at", now),
            "updated_at": now,
            "updated_by": user_id,
        }
        insert_result = employees.insert_one(employee_doc)
        employee_id = str(insert_result.inserted_id)

        drafts.update_one(
            {"tenant_id": tenant_id, "draft_id": draft_id},
            {
                "$set": {
                    "status": "completed",
                    "employee_id": employee_id,
                    "completed_at": now,
                    "step_completed": 7,
                    "next_step": None,
                    **build_audit_fields(prefix="updated", by=user_id),
                }
            },
        )

        return {
            "employee_id": employee_id,
            "employee_code": draft.get("employment", {}).get("employee_code"),
            "work_email": draft.get("employment", {}).get("work_email"),
            "status": "active",
            "etag": etag,
        }

    # ------------------------------------------------------------------
    # Listing & bulk operations
    # ------------------------------------------------------------------
    def list_employees(self, tenant_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        employees = self._employees(tenant_id)
        query = self._build_employee_filters(tenant_id, filters)

        page = max(int(filters.get("page", 1)), 1)
        limit = min(max(int(filters.get("limit", 20)), 1), 100)
        skip = (page - 1) * limit
        sort_field = filters.get("sort_by") or "updated_at"
        sort_order = -1 if (filters.get("sort_order") or "desc").lower() == "desc" else 1

        cursor = (
            employees.find(query)
            .sort(sort_field, sort_order)
            .skip(skip)
            .limit(limit)
        )
        items = [self._project_employee_list_item(doc) for doc in cursor]
        total = employees.count_documents(query)
        total_pages = (total + limit - 1) // limit

        return {
            "items": items,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "filters_applied": {k: v for k, v in filters.items() if v is not None},
        }

    def get_filter_options(self, tenant_id: str) -> Dict[str, Any]:
        tenant_db = self._tenant_db(tenant_id)
        departments = list(
            tenant_db["tenant_departments"]
            .find({"del": {"$ne": 1}})
            .sort("name", 1)
        )
        designations = list(
            tenant_db["tenant_designations"]
            .find({"del": {"$ne": 1}})
            .sort("name", 1)
        )
        locations = list(tenant_db["tenant_locations"].find({}).sort("name", 1))
        roles = list(tenant_db["permission_roles"].find({}).sort("name", 1))
        tags = [
            tag
            for tag in self._employees(tenant_id).distinct("tags")
            if isinstance(tag, str) and tag.strip()
        ]
        statuses = [
            {"value": "active", "label": "Active"},
            {"value": "inactive", "label": "Inactive"},
            {"value": "suspended", "label": "Suspended"},
            {"value": "terminated", "label": "Terminated"},
        ]
        return {
            "departments": [
                {"id": str(doc.get("_id")), "name": doc.get("name"), "code": doc.get("code")}
                for doc in departments
            ],
            "designations": [
                {"id": str(doc.get("_id")), "name": doc.get("name"), "department": doc.get("department")}
                for doc in designations
            ],
            "locations": [
                {"id": str(doc.get("_id")), "name": doc.get("name")}
                for doc in locations
            ],
            "roles": [
                {"id": str(doc.get("_id")), "name": doc.get("name"), "code": doc.get("code")}
                for doc in roles
            ],
            "tags": tags,
            "statuses": statuses,
        }

    def export_employees(self, tenant_id: str, filters: Dict[str, Any], limit: int = 1000) -> Dict[str, Any]:
        employees = self._employees(tenant_id)
        query = self._build_employee_filters(tenant_id, filters)
        cursor = (
            employees.find(query)
            .sort("updated_at", -1)
            .limit(max(min(limit, 5000), 1))
        )
        rows = [self._project_employee_export_row(doc) for doc in cursor]
        return {
            "items": rows,
            "count": len(rows),
        }

    def bulk_assign_role(
        self,
        tenant_id: str,
        employee_ids: List[str],
        role_id: str,
        role_name: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        if not role_id:
            raise EmployeeWorkflowError(
                "role_id is required",
                status_code=422,
                errors=[{"field": "role_id", "message": "Role id is required"}],
            )
        updates = {
            "permission_profile_id": role_id,
            "permission_profile_name": role_name,
            "updated_at": self._now(),
            "updated_by": actor,
        }
        modified = self._update_many_employees(tenant_id, employee_ids, updates)
        return {"updated": modified}

    def bulk_suspend(
        self,
        tenant_id: str,
        employee_ids: List[str],
        reason: Optional[str],
        effective_date: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        updates = {
            "status": "inactive",
            "employment_status": "suspended",
            "suspension_reason": reason,
            "suspension_effective_date": effective_date,
            "updated_at": self._now(),
            "updated_by": actor,
        }
        modified = self._update_many_employees(tenant_id, employee_ids, updates)
        return {"updated": modified}

    def bulk_terminate(
        self,
        tenant_id: str,
        employee_ids: List[str],
        reason: Optional[str],
        last_working_day: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        updates = {
            "status": "inactive",
            "employment_status": "terminated",
            "termination_reason": reason,
            "termination_date": last_working_day,
            "updated_at": self._now(),
            "updated_by": actor,
        }
        modified = self._update_many_employees(tenant_id, employee_ids, updates)
        return {"updated": modified}

    def bulk_activate_ess(
        self,
        tenant_id: str,
        employee_ids: List[str],
        enable: bool,
        actor: str,
    ) -> Dict[str, Any]:
        updates = {
            "ess_enabled": bool(enable),
            "ess_activated_at": self._now() if enable else None,
            "updated_at": self._now(),
            "updated_by": actor,
        }
        modified = self._update_many_employees(tenant_id, employee_ids, updates)
        return {"updated": modified}

    def bulk_add_tag(
        self,
        tenant_id: str,
        employee_ids: List[str],
        tag: str,
        actor: str,
    ) -> Dict[str, Any]:
        if not tag or not tag.strip():
            raise EmployeeWorkflowError(
                "tag is required",
                status_code=422,
                errors=[{"field": "tag", "message": "Tag text is required"}],
            )
        tag_value = tag.strip()
        employees = self._employees(tenant_id)
        object_ids = self._ensure_employee_object_ids(employee_ids)
        result = employees.update_many(
            {"_id": {"$in": object_ids}},
            {
                "$set": {
                    "updated_at": self._now(),
                    "updated_by": actor,
                },
                "$addToSet": {"tags": tag_value},
            },
        )
        return {"updated": result.modified_count}

    def update_employee_status(
        self,
        tenant_id: str,
        employee_id: str,
        status_value: str,
        actor: str,
        reason: Optional[str] = None,
        effective_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not status_value:
            raise EmployeeWorkflowError(
                "status is required",
                status_code=422,
                errors=[{"field": "status", "message": "Status is required"}],
            )
        doc = self._get_employee_doc(tenant_id, employee_id)
        employees = self._employees(tenant_id)
        normalized_status = status_value.lower()
        allowed = {"active", "inactive", "suspended", "terminated"}
        if normalized_status not in allowed:
            raise EmployeeWorkflowError(
                "Invalid status value",
                status_code=422,
                errors=[{"field": "status", "message": f"Status must be one of {sorted(allowed)}"}],
            )
        updates = {
            "status": "active" if normalized_status == "active" else "inactive",
            "employment_status": normalized_status,
            "status_reason": reason,
            "status_effective_date": effective_date,
            "updated_at": self._now(),
            "updated_by": actor,
        }
        employees.update_one({"_id": doc["_id"]}, {"$set": updates})
        doc.update(updates)
        return self._sanitize_employee(doc)

    # ------------------------------------------------------------------
    # Draft querying
    # ------------------------------------------------------------------
    def get_draft(self, tenant_id: str, draft_id: str) -> Dict[str, Any]:
        draft = self._get_draft_doc(tenant_id, draft_id)
        draft["_id"] = str(draft.get("_id"))
        return draft

    def list_drafts(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        drafts = self._drafts(tenant_id)
        cursor = drafts.find({"tenant_id": tenant_id, "created_by": user_id, "status": {"$ne": "completed"}}).sort(
            "updated_at", -1
        )
        results = []
        for doc in cursor:
            doc["_id"] = str(doc.get("_id"))
            results.append(
                {
                    "draft_id": doc.get("draft_id"),
                    "employee_name": doc.get("personal", {}).get("first_name"),
                    "step_completed": doc.get("step_completed"),
                    "next_step": doc.get("next_step"),
                    "updated_at": doc.get("updated_at"),
                }
            )
        return results

    def delete_draft(self, tenant_id: str, draft_id: str) -> None:
        draft = self._get_draft_doc(tenant_id, draft_id)
        self._ensure_mutable(draft)
        drafts = self._drafts(tenant_id)
        drafts.delete_one({"tenant_id": tenant_id, "draft_id": draft_id})

    # ------------------------------------------------------------------
    # Employee read/update
    # ------------------------------------------------------------------
    def get_employee(self, tenant_id: str, employee_id: str) -> Dict[str, Any]:
        doc = self._get_employee_doc(tenant_id, employee_id)
        return self._sanitize_employee(doc)

    def update_employee(
        self,
        tenant_id: str,
        employee_id: str,
        payload: Dict[str, Any],
        actor: str,
        etag: Optional[str],
    ) -> Dict[str, Any]:
        self._require_dict(payload, "payload")
        doc = self._get_employee_doc(tenant_id, employee_id)
        self._ensure_etag(doc, etag)
        employees = self._employees(tenant_id)
        now = self._now()
        new_etag = self._generate_etag()
        updates = {
            "personal": payload.get("personal", doc.get("personal")),
            "employment": payload.get("employment", doc.get("employment")),
            "compensation": payload.get("compensation", doc.get("compensation")),
            "bank_tax": payload.get("bank_tax", doc.get("bank_tax")),
            "documents": payload.get("documents", doc.get("documents")),
            "emergency_address": payload.get("emergency_address", doc.get("emergency_address")),
            "status": payload.get("status", doc.get("status", "active")),
            "version": doc.get("version", 1) + 1,
            "etag": new_etag,
            "updated_at": now,
            "updated_by": actor,
        }
        employees.update_one({"_id": doc["_id"]}, {"$set": updates})
        doc.update(updates)
        return self._sanitize_employee(doc)

    def update_employee_step(
        self,
        tenant_id: str,
        employee_id: str,
        step_number: int,
        section_key: str,
        section_payload: Dict[str, Any],
        actor: str,
        etag: Optional[str],
    ) -> Dict[str, Any]:
        self._require_dict(section_payload, section_key)
        doc = self._get_employee_doc(tenant_id, employee_id)
        self._ensure_etag(doc, etag)
        employees = self._employees(tenant_id)
        now = self._now()
        new_etag = self._generate_etag()
        updates = {
            section_key: section_payload,
            "version": doc.get("version", 1) + 1,
            "etag": new_etag,
            "updated_at": now,
            "updated_by": actor,
        }
        employees.update_one({"_id": doc["_id"]}, {"$set": updates})
        doc.update(updates)
        return self._sanitize_employee(doc)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_email(self, tenant_id: str, email: str, exclude_id: Optional[str]) -> Dict[str, Any]:
        return self._validate_unique_field(tenant_id, "employment.work_email", email, exclude_id)

    def validate_code(self, tenant_id: str, code: str, exclude_id: Optional[str]) -> Dict[str, Any]:
        return self._validate_unique_field(tenant_id, "employment.employee_code", code, exclude_id)

    def validate_username(self, tenant_id: str, username: str, exclude_id: Optional[str]) -> Dict[str, Any]:
        return self._validate_unique_field(tenant_id, "employment.work_email_username", username, exclude_id)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    def get_lookup(self, tenant_id: str, resource: str) -> Dict[str, Any]:
        tenant_db = self._tenant_db(tenant_id)
        mapping = {
            "departments": ("tenant_departments", {"del": {"$ne": 1}}),
            "locations": ("tenant_locations", {}),
            "shifts": ("tenant_shifts", {}),
            "designations": ("tenant_designations", {"del": {"$ne": 1}}),
            "salary-structures": ("salary_structures", {}),
            "roles": ("permission_roles", {}),
            "employees": ("employees", {"status": "active"}),
            "document-categories": None,
            "permission-profiles": None,
        }
        collection_info = mapping.get(resource)
        if collection_info is None:
            # Static resources
            if resource == "document-categories":
                return {
                    "data": [
                        {"code": "offer_letter", "label": "Offer Letter"},
                        {"code": "id_proof", "label": "ID Proof"},
                        {"code": "address_proof", "label": "Address Proof"},
                        {"code": "experience_letter", "label": "Experience Letter"},
                    ]
                }
            if resource == "permission-profiles":
                return {
                    "data": [
                        {"code": "admin", "label": "Administrator"},
                        {"code": "hr_manager", "label": "HR Manager"},
                        {"code": "people_manager", "label": "People Manager"},
                    ]
                }
            raise EmployeeWorkflowError("Lookup not supported", status_code=404, code="NOT_FOUND")

        collection_name, base_query = collection_info
        collection = tenant_db[collection_name]
        query = dict(base_query)
        if "tenant_id" not in query:
            query["tenant_id"] = tenant_id
        cursor = collection.find(query).sort("created_at", -1)
        data = []
        for doc in cursor:
            doc_id = doc.get("_id")
            data.append(
                {
                    "id": str(doc_id),
                    "name": doc.get("name") or doc.get("department") or doc.get("title"),
                    "code": doc.get("code"),
                    "extra": {
                        "department": doc.get("department"),
                        "level": doc.get("level"),
                    },
                }
            )
        return {"data": data}

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------
    def init_upload(
        self,
        tenant_id: str,
        user_id: str,
        file_name: str,
        file_size: int,
        mime_type: str,
        category: str,
    ) -> Dict[str, Any]:
        uploads = self._uploads(tenant_id)
        upload_id = self._generate_upload_id()
        now = self._now()
        signed_url = f"https://uploads.example.com/{upload_id}?token={secrets.token_urlsafe(8)}"
        record = {
            "upload_id": upload_id,
            "tenant_id": tenant_id,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "category": category,
            "status": "authorized",
            "signed_url": signed_url,
            "created_at": now,
            "created_by": user_id,
        }
        uploads.insert_one(record)
        return {
            "upload_id": upload_id,
            "signed_url": signed_url,
            "expires_at": now,
        }

    def complete_upload(self, tenant_id: str, upload_id: str, final_url: Optional[str]) -> Dict[str, Any]:
        uploads = self._uploads(tenant_id)
        record = uploads.find_one({"tenant_id": tenant_id, "upload_id": upload_id})
        if not record:
            raise EmployeeWorkflowError("Upload not found", status_code=404, code="NOT_FOUND")
        uploads.update_one(
            {"tenant_id": tenant_id, "upload_id": upload_id},
            {
                "$set": {
                    "status": "completed",
                    "file_url": final_url or f"https://cdn.example.com/{upload_id}",
                    "completed_at": self._now(),
                }
            },
        )
        record = uploads.find_one({"tenant_id": tenant_id, "upload_id": upload_id})
        return {
            "upload_id": upload_id,
            "file_url": record.get("file_url"),
            "file_size": record.get("file_size"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _tenant_db(self, tenant_id: str):
        if not tenant_id:
            raise EmployeeWorkflowError("Tenant context missing", status_code=403, code="TENANT_REQUIRED")
        return self.client[tenant_id]

    def _drafts(self, tenant_id: str):
        return self._tenant_db(tenant_id)["employee_drafts"]

    def _employees(self, tenant_id: str):
        return self._tenant_db(tenant_id)["employees"]

    def _uploads(self, tenant_id: str):
        return self._tenant_db(tenant_id)["employee_uploads"]

    def _get_draft_doc(self, tenant_id: str, draft_id: str) -> Dict[str, Any]:
        if not draft_id:
            raise EmployeeWorkflowError("draft_id is required", status_code=422)
        draft = self._drafts(tenant_id).find_one({"tenant_id": tenant_id, "draft_id": draft_id})
        if not draft:
            raise EmployeeWorkflowError("Draft not found", status_code=404, code="NOT_FOUND")
        return draft

    def _get_employee_doc(self, tenant_id: str, employee_id: str) -> Dict[str, Any]:
        try:
            object_id = ObjectId(employee_id)
        except Exception:
            raise EmployeeWorkflowError("Employee not found", status_code=404, code="NOT_FOUND")
        doc = self._employees(tenant_id).find_one({"_id": object_id})
        if not doc:
            raise EmployeeWorkflowError("Employee not found", status_code=404, code="NOT_FOUND")
        return doc

    def _ensure_mutable(self, draft: Dict[str, Any]) -> None:
        if draft.get("status") == "completed":
            raise EmployeeWorkflowError(
                "Draft already completed",
                status_code=409,
                code="CONFLICT",
            )

    def _ensure_etag(self, doc: Dict[str, Any], provided: Optional[str]) -> None:
        current = doc.get("etag")
        if current and provided and current != provided:
            raise EmployeeWorkflowError(
                "Version mismatch. Refresh employee before updating",
                status_code=412,
                code="PRECONDITION_FAILED",
            )

    def _validate_unique_field(
        self,
        tenant_id: str,
        field_path: str,
        value: Optional[str],
        exclude_id: Optional[str],
    ) -> Dict[str, Any]:
        if not value:
            raise EmployeeWorkflowError(
                "value query parameter is required",
                status_code=422,
                errors=[{"field": "value", "message": "Provide value to validate"}],
            )
        employees = self._employees(tenant_id)
        query: Dict[str, Any] = {field_path: value}
        if exclude_id:
            try:
                query["_id"] = {"$ne": ObjectId(exclude_id)}
            except Exception:
                pass
        exists = employees.find_one(query) is not None
        return {
            "is_unique": not exists,
            "message": "Value is available" if not exists else "Value already exists",
        }

    def _push_history(
        self,
        drafts,
        draft_id: str,
        step: int,
        user_id: str,
        timestamp: str,
        details: Optional[str] = None,
    ) -> None:
        drafts.update_one(
            {"draft_id": draft_id},
            {
                "$push": {
                    "history": {
                        "step": step,
                        "by": user_id,
                        "at": timestamp,
                        "details": details,
                    }
                }
            },
        )

    def _sanitize_employee(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(doc)
        clean["id"] = str(clean.pop("_id"))
        return clean

    def _generate_draft_id(self) -> str:
        return f"draft_{uuid4().hex[:12]}"

    def _generate_upload_id(self) -> str:
        return f"upload_{uuid4().hex}"

    def _generate_etag(self) -> str:
        return uuid4().hex

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _require_dict(self, value: Any, field: str) -> Dict[str, Any]:
        if not isinstance(value, dict) or not value:
            raise EmployeeWorkflowError(
                f"{field} must be an object",
                errors=[{"field": field, "message": f"{field} must be an object"}],
            )
        return value

    def _build_employee_filters(self, tenant_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        query: Dict[str, Any] = {"tenant_id": tenant_id}
        search = (filters.get("search") or "").strip()
        if search:
            regex = {"$regex": search, "$options": "i"}
            query["$or"] = [
                {"personal.first_name": regex},
                {"personal.last_name": regex},
                {"personal.personal_email": regex},
                {"employment.employee_code": regex},
                {"employment.work_email": regex},
            ]

        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("employment_status"):
            query["employment_status"] = filters["employment_status"]
        if filters.get("department_id"):
            query["employment.department_id"] = filters["department_id"]
        if filters.get("designation"):
            query["employment.designation"] = filters["designation"]
        if filters.get("role_id"):
            query["permission_profile_id"] = filters["role_id"]
        if filters.get("location_id"):
            query["employment.work_location_id"] = filters["location_id"]
        if filters.get("manager_id"):
            query["employment.manager_id"] = filters["manager_id"]
        if filters.get("tags"):
            tags = filters["tags"]
            if isinstance(tags, list) and tags:
                query["tags"] = {"$all": tags}
        join_from = filters.get("join_date_from")
        join_to = filters.get("join_date_to")
        if join_from or join_to:
            date_query: Dict[str, Any] = {}
            if join_from:
                date_query["$gte"] = join_from
            if join_to:
                date_query["$lte"] = join_to
            query["employment.join_date"] = date_query
        return query

    def _project_employee_list_item(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        employment = doc.get("employment", {})
        personal = doc.get("personal", {})
        return {
            "id": str(doc.get("_id")),
            "employee_code": employment.get("employee_code"),
            "name": " ".join(
                filter(
                    None,
                    [
                        personal.get("first_name"),
                        personal.get("middle_name"),
                        personal.get("last_name"),
                    ],
                )
            ).strip(),
            "department": employment.get("department_id"),
            "designation": employment.get("designation"),
            "manager_id": employment.get("manager_id"),
            "work_location_id": employment.get("work_location_id"),
            "status": doc.get("status"),
            "employment_status": doc.get("employment_status"),
            "tags": doc.get("tags", []),
            "ess_enabled": doc.get("ess_enabled", False),
            "work_email": employment.get("work_email"),
            "join_date": employment.get("join_date"),
            "updated_at": doc.get("updated_at"),
        }

    def _project_employee_export_row(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        employment = doc.get("employment", {})
        personal = doc.get("personal", {})
        bank_tax = doc.get("bank_tax", {})
        return {
            "employee_code": employment.get("employee_code"),
            "full_name": " ".join(
                filter(
                    None,
                    [
                        personal.get("first_name"),
                        personal.get("middle_name"),
                        personal.get("last_name"),
                    ],
                )
            ).strip(),
            "department_id": employment.get("department_id"),
            "designation": employment.get("designation"),
            "work_email": employment.get("work_email"),
            "personal_email": personal.get("personal_email"),
            "employment_type": employment.get("employment_type"),
            "join_date": employment.get("join_date"),
            "manager_id": employment.get("manager_id"),
            "status": doc.get("status"),
            "employment_status": doc.get("employment_status"),
            "tags": doc.get("tags", []),
            "bank_name": bank_tax.get("bank_name"),
            "ifsc": bank_tax.get("ifsc"),
        }

    def _update_many_employees(
        self,
        tenant_id: str,
        employee_ids: List[str],
        updates: Dict[str, Any],
    ) -> int:
        employees = self._employees(tenant_id)
        object_ids = self._ensure_employee_object_ids(employee_ids)
        result = employees.update_many(
            {"_id": {"$in": object_ids}},
            {"$set": updates},
        )
        return result.modified_count

    def _ensure_employee_object_ids(self, employee_ids: List[str]) -> List[ObjectId]:
        object_ids: List[ObjectId] = []
        for emp_id in employee_ids or []:
            try:
                object_ids.append(ObjectId(emp_id))
            except Exception:
                continue
        if not object_ids:
            raise EmployeeWorkflowError(
                "employee_ids must include at least one valid identifier",
                status_code=422,
                errors=[{"field": "employee_ids", "message": "Provide at least one valid employee id"}],
            )
        return object_ids
