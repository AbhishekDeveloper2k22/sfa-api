from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import uuid

from bson import ObjectId

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class PayrollError(Exception):
    """Domain error for payroll operations."""
    def __init__(self, message: str, *, status_code: int = 400, code: str = "VALIDATION_FAILED", errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.errors = errors or []


class PayrollService:
    """Service layer for tenant-scoped payroll module."""

    def __init__(self):
        self.client = client1

    # ------------------------------------------------------------------
    # 1. Payroll Run APIs
    # ------------------------------------------------------------------
    def get_payroll_runs(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match_query = {"tenant_id": tenant_id}
        
        if query_params.get("status"):
            match_query["status"] = query_params["status"]
            
        if query_params.get("year"):
            match_query["period_year"] = int(query_params["year"])

        data = list(db["payroll_runs"].find(match_query).sort("created_at", -1))
        
        return {
            "data": [self._sanitize(d) for d in data],
            "meta": {"total": len(data)}
        }

    def get_payroll_run(self, tenant_id: str, run_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["payroll_runs"].find_one({"_id": run_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["payroll_runs"].find_one({"_id": ObjectId(run_id), "tenant_id": tenant_id})
             except:
                 pass
        if not doc:
             doc = db["payroll_runs"].find_one({"id": run_id, "tenant_id": tenant_id})
        
        if not doc:
             raise PayrollError("Payroll run not found", status_code=404, code="NOT_FOUND")
             
        return self._sanitize(doc)

    def start_preview(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        self._require(payload.get("period_month"), "period_month")
        self._require(payload.get("period_year"), "period_year")
        
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        job_doc = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "type": "payroll_preview",
            "payload": payload,
            "created_by": actor,
            "created_at": datetime.utcnow()
        }
        db["jobs"].insert_one(job_doc)
        
        # Simulate processing
        self._process_payroll_preview(tenant_id, job_id, payload)
        
        return {"job_id": job_id, "status": "queued", "message": "Preview started"}

    def get_job_status(self, tenant_id: str, job_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["jobs"].find_one({"job_id": job_id, "tenant_id": tenant_id})
        if not doc:
             raise PayrollError("Job not found", status_code=404)
        
        return {
            "job_id": doc["job_id"],
            "status": doc["status"],
            "progress": doc.get("progress", 0),
            "result_url": f"/payroll/preview/{job_id}/employees" if doc["status"] == "completed" else None
        }

    def get_preview_results(self, tenant_id: str, job_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        previews = list(db["payroll_previews"].find({"job_id": job_id, "tenant_id": tenant_id}))
        
        total_gross = sum(p.get("gross", 0) for p in previews)
        total_net = sum(p.get("net_pay", 0) for p in previews)
        total_deduc = sum(p.get("total_deductions", 0) for p in previews)
        
        return {
            "data": [self._sanitize(p) for p in previews],
            "meta": {
                "page": 1,
                "page_size": 50,
                "total": len(previews),
                "total_pages": 1
            },
            "summary": {
                "total_employees": len(previews),
                "total_gross": total_gross,
                "total_net": total_net,
                "total_deductions": total_deduc,
                "warnings_count": 0,
                "errors_count": 0
            }
        }

    def finalize_payroll(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        job_id = self._require(payload.get("preview_job_id"), "preview_job_id")
        
        job = db["jobs"].find_one({"job_id": job_id, "tenant_id": tenant_id})
        if not job or job["status"] != "completed":
            raise PayrollError("Preview job not completed or found")
            
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        run_data = {
            "id": run_id,
            "tenant_id": tenant_id,
            "period_month": job["payload"]["period_month"],
            "period_year": job["payload"]["period_year"],
            "run_type": job["payload"]["run_type"],
            "status": "finalized",
            "created_by": actor,
            "created_at": datetime.utcnow(),
            "finalized_at": datetime.utcnow(),
            "notes": payload.get("finalize_notes")
        }
        
        previews = db["payroll_previews"].find({"job_id": job_id})
        payslips = []
        for p in previews:
            p_data = dict(p)
            del p_data["_id"]
            p_data["payroll_run_id"] = run_id
            p_data["status"] = "finalized"
            p_data["id"] = f"ps_{run_id}_{p_data.get('employee_id')}"
            payslips.append(p_data)
            
        if payslips:
             db["payslips"].insert_many(payslips)
             gross = sum(p["gross"] for p in payslips)
             net = sum(p["net_pay"] for p in payslips)
             run_data["totals"] = {"gross": gross, "net": net, "employer_cost": gross}
             run_data["employee_count"] = len(payslips)
             
        db["payroll_runs"].insert_one(run_data)
        return {"payroll_run_id": run_id, "status": "finalized", "message": "Payroll finalized successfully"}

    def export_payroll_run(self, tenant_id: str, run_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
         return {"download_url": f"#export_run_{run_id}_{query_params.get('format')}", "expires_at": datetime.utcnow() + timedelta(hours=1)}

    # ------------------------------------------------------------------
    # 2. Payslip APIs
    # ------------------------------------------------------------------
    def get_payslips(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("period_month"): match["period_month"] = int(query_params["period_month"])
        if query_params.get("period_year"): match["period_year"] = int(query_params["period_year"])
        if query_params.get("status"): match["status"] = query_params["status"]
        if q := query_params.get("q"):
             match["employee.display_name"] = {"$regex": q, "$options": "i"}
        
        data = list(db["payslips"].find(match))
        return {
            "data": [self._sanitize(d) for d in data],
            "meta": {"total": len(data)}
        }

    def get_payslip_by_id(self, tenant_id: str, payslip_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["payslips"].find_one({"id": payslip_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["payslips"].find_one({"_id": ObjectId(payslip_id), "tenant_id": tenant_id})
             except:
                 pass
        if not doc:
             raise PayrollError("Payslip not found", status_code=404)
        return self._sanitize(doc)

    def get_employee_payslips(self, tenant_id: str, employee_id: str, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
         db = self._get_db(tenant_id)
         q = {"tenant_id": tenant_id, "employee_id": employee_id}
         if query_params:
             if query_params.get("period_month"): q["period_month"] = int(query_params["period_month"])
             if query_params.get("period_year"): q["period_year"] = int(query_params["period_year"])
         
         data = list(db["payslips"].find(q))
         return {"data": [self._sanitize(d) for d in data]}

    def download_payslip(self, tenant_id: str, payslip_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
         return {"download_url": f"#download_ps_{payslip_id}_{query_params.get('format')}", "expires_at": datetime.utcnow() + timedelta(hours=1)}

    # ------------------------------------------------------------------
    # 3. Salary Structure APIs
    # ------------------------------------------------------------------
    def get_salary_structures(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        data = list(db["salary_structures"].find({"tenant_id": tenant_id}))
        return {"data": [self._sanitize(d) for d in data]}

    def create_salary_structure(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        if db["salary_structures"].find_one({"tenant_id": tenant_id, "code": payload.get("code")}):
             raise PayrollError("Structure code already exists")
             
        doc = payload.copy()
        doc["tenant_id"] = tenant_id
        doc.update(build_audit_fields(prefix="created", by=actor))
        res = db["salary_structures"].insert_one(doc)
        doc["_id"] = res.inserted_id
        return self._sanitize(doc)

    def get_salary_structure(self, tenant_id: str, code: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["salary_structures"].find_one({"tenant_id": tenant_id, "code": code})
        if not doc:
             try:
                 doc = db["salary_structures"].find_one({"tenant_id": tenant_id, "_id": ObjectId(code)})
             except:
                 pass
        if not doc:
             raise PayrollError("Structure not found", status_code=404)
        return self._sanitize(doc)

    def update_salary_structure(self, tenant_id: str, code: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        existing = db["salary_structures"].find_one({"tenant_id": tenant_id, "code": code})
        if not existing:
             raise PayrollError("Structure not found", status_code=404)
             
        updates = payload.copy()
        updates.update(build_audit_fields(prefix="updated", by=actor))
        db["salary_structures"].update_one({"_id": existing["_id"]}, {"$set": updates})
        updated_doc = db["salary_structures"].find_one({"_id": existing["_id"]})
        return self._sanitize(updated_doc)

    def delete_salary_structure(self, tenant_id: str, code: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        res = db["salary_structures"].delete_one({"tenant_id": tenant_id, "code": code})
        if res.deleted_count == 0:
             raise PayrollError("Structure not found", status_code=404)
        return {"success": True}

    def validate_formula(self, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "errors": []}

    # ------------------------------------------------------------------
    # 4. Statutory & Challan APIs
    # ------------------------------------------------------------------
    def get_challans(self, tenant_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        match = {"tenant_id": tenant_id}
        if query_params.get("status"): match["status"] = query_params["status"]
        if query_params.get("type"): match["type"] = query_params["type"]
        
        data = list(db["statutory_challans"].find(match))
        
        total_due = sum(c.get('amount', 0) for c in data)
        total_paid = sum(c.get('amount', 0) for c in data if c.get('status') == 'paid')
        pending_count = len([c for c in data if c.get('status') != 'paid'])
        
        return {
            "data": [self._sanitize(d) for d in data],
            "summary": {
                "total_due": total_due,
                "total_paid": total_paid,
                "pending_count": pending_count
            }
        }
    
    def get_challan(self, tenant_id: str, challan_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        doc = db["statutory_challans"].find_one({"id": challan_id, "tenant_id": tenant_id})
        if not doc:
             try:
                 doc = db["statutory_challans"].find_one({"_id": ObjectId(challan_id), "tenant_id": tenant_id})
             except:
                 pass
        if not doc:
             raise PayrollError("Challan not found", status_code=404)
        return self._sanitize(doc)

    def generate_challan(self, tenant_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        cid = f"ch_new_{uuid.uuid4().hex[:8]}"
        doc = {
            "id": cid,
            "tenant_id": tenant_id,
            "status": "draft",
            "period_month": payload.get("period_month"),
            "period_year": payload.get("period_year"),
            "types": payload.get("types"),
            "created_at": datetime.utcnow()
        }
        db["statutory_challans"].insert_one(doc)
        return {"challan_id": cid, "status": "draft", "message": "Challan generated"}

    def mark_challan_paid(self, tenant_id: str, challan_id: str, payload: Dict[str, Any], actor: Optional[str]) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        q = {"id": challan_id, "tenant_id": tenant_id}
        doc = db["statutory_challans"].find_one(q)
        if not doc:
             try:
                 q = {"_id": ObjectId(challan_id), "tenant_id": tenant_id}
                 doc = db["statutory_challans"].find_one(q)
             except:
                 pass
        if not doc:
             raise PayrollError("Challan not found", 404)
             
        db["statutory_challans"].update_one(q, {"$set": {"status": "paid", "paid_details": payload, "updated_at": datetime.utcnow()}})
        return {"id": challan_id, "status": "paid", "message": "marked as paid"}

    def download_challan(self, tenant_id: str, challan_id: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
         return {"download_url": f"#download_ch_{challan_id}_{query_params.get('format')}", "expires_at": datetime.utcnow() + timedelta(hours=1)}

    def get_statutory_rules(self, tenant_id: str) -> Dict[str, Any]:
        return {"data": [{
            "id": "rule_001",
            "name": "India Statutory Rules FY 2024-25",
            "version": "v2024_04",
            "effective_from": "2024-04-01",
            "config": {}
        }]}

    def get_active_statutory_rule(self, tenant_id: str) -> Dict[str, Any]:
         # Mock
         return {
            "id": "rule_001",
            "name": "India Statutory Rules FY 2024-25",
            "version": "v2024_04",
            "effective_from": "2024-04-01",
            "config": {}
        }

    # ------------------------------------------------------------------
    # 5. Stats
    # ------------------------------------------------------------------
    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        db = self._get_db(tenant_id)
        return {
            "total_employees": db["users"].count_documents({"tenant_id": tenant_id, "status": "active"}),
            "current_month_payroll": 0,
            "ytd_payroll": 0,
            "pending_requests": 0,
            "pending_challans": 0,
            "last_run_date": None
        }

    def get_filter_options(self, tenant_id: str) -> Dict[str, Any]:
        return {
            "departments": [],
            "employees": [],
            "salary_structures": [],
            "statutory_versions": [],
            "run_types": [{"value": "regular", "label": "Regular Monthly"}],
            "challan_types": [{"value": "PF", "label": "Provident Fund"}]
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _process_payroll_preview(self, tenant_id, job_id, payload):
        db = self._get_db(tenant_id)
        users = list(db["users"].find({"tenant_id": tenant_id, "status": "active"}))
        previews = []
        for u in users:
            basic = u.get("salary", 50000) * 0.4
            previews.append({
                "job_id": job_id,
                "tenant_id": tenant_id,
                "employee_id": str(u["_id"]),
                "employee": {
                    "id": str(u["_id"]),
                    "display_name": u.get("display_name", "Unknown"),
                    "employee_code": u.get("employee_code", "EMP"),
                    "department": u.get("department")
                },
                "period_month": payload["period_month"],
                "period_year": payload["period_year"],
                "salary_structure": "STD_INDIA",
                "earnings": [{"code": "BASIC", "label": "Basic Salary", "amount": basic}],
                "deductions": [{"code": "PF", "label": "PF", "amount": 1800}],
                "gross": basic,
                "total_deductions": 1800,
                "net_pay": basic - 1800,
                "status": "preview",
                "generated_at": datetime.utcnow()
            })
        if previews:
            db["payroll_previews"].insert_many(previews)
        db["jobs"].update_one({"job_id": job_id}, {"$set": {"status": "completed", "progress": 100}})

    def _get_db(self, tenant_id: str):
        return self.client[tenant_id]

    def _sanitize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc = dict(doc)
        if "_id" in doc:
             doc["id"] = str(doc.pop("_id"))
        return doc

    def _require(self, value, name):
        if not value:
            raise PayrollError(f"{name} is required")
        return value
