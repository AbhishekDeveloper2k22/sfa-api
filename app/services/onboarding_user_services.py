import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import UploadFile
from passlib.hash import bcrypt

from app.database import client1
from app.utils.audit_utils import build_audit_fields


class TenantOnboardingService:
    """Service layer for managing multi-step tenant onboarding with progress tracking."""

    def __init__(self):
        self.client_database = client1["hrms_master"]
        self.onboarding_collection = self.client_database["tenant_onboarding"]
        self.tenants_collection = self.client_database["tenants"]
        self.users_collection = self.client_database["users"]

    # -------------------------------------------------------------------------
    # Public APIs
    # -------------------------------------------------------------------------
    def save_step1(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update company details for step 1."""
        if not company:
            raise ValueError("Company details are required.")

        business_email = (company.get("business_email") or "").strip().lower()
        if not business_email:
            raise ValueError("Company business email is required.")

        existing = self.onboarding_collection.find_one(
            {"business_email": business_email, "status": {"$ne": "archived"}}
        )

        if existing and existing.get("status") != "completed":
            updates = {
                "company": company,
                "business_email": business_email,
                "current_step": 1,
                "step_completed": 1,
                "next_step": 2,
                "status": "in_progress",
            }
            updates.update(build_audit_fields(prefix="updated", by=business_email))
            self.onboarding_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": updates},
            )
            onboarding_id = existing["onboarding_id"]
        else:
            onboarding_id = self._generate_onboarding_id()
            doc = {
                "onboarding_id": onboarding_id,
                "company": company,
                "business_email": business_email,
                "current_step": 1,
                "step_completed": 1,
                "next_step": 2,
                "status": "in_progress",
            }
            doc.update(build_audit_fields(prefix="created", by=business_email))
            self.onboarding_collection.insert_one(doc)

        return {
            "onboarding_id": onboarding_id,
            "step_completed": 1,
            "next_step": 2,
            "business_email": business_email,
        }

    def save_step2(self, onboarding_id: str, admin_user: Dict[str, Any]) -> Dict[str, Any]:
        """Save admin user details for step 2."""
        onboarding = self._get_active_onboarding(onboarding_id)
        if not admin_user:
            raise ValueError("Admin user details are required.")

        password_setup = admin_user.get("password_setup", {}) or {}
        method = (password_setup.get("method") or "email").lower()
        temp_password = password_setup.get("temporary_password")
        password_hash = None
        if method == "temporary":
            if not temp_password:
                raise ValueError("Temporary password is required for method 'temporary'.")
            password_hash = bcrypt.hash(temp_password)
            password_setup.pop("temporary_password", None)

        admin_payload = {
            "full_name": admin_user.get("full_name"),
            "email": admin_user.get("email"),
            "contact_number": admin_user.get("contact_number"),
            "password_setup": password_setup,
            "password_hash": password_hash,
        }

        if not admin_payload["email"]:
            raise ValueError("Admin user email is required.")

        updates = {
            "admin_user": admin_payload,
            "current_step": 2,
            "step_completed": 2,
            "next_step": 3,
            "status": "in_progress",
        }
        updates.update(build_audit_fields(prefix="updated", by=admin_payload["email"]))

        self.onboarding_collection.update_one(
            {"_id": onboarding["_id"]},
            {"$set": updates},
        )

        return {
            "onboarding_id": onboarding_id,
            "step_completed": 2,
            "next_step": 3,
        }

    def save_step3(self, onboarding_id: str, branding: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize onboarding with branding details and tenant creation."""
        onboarding = self._get_active_onboarding(onboarding_id)
        admin_user = onboarding.get("admin_user") or {}
        company = onboarding.get("company") or {}

        if not admin_user:
            raise ValueError("Admin user details are missing. Complete step 2 first.")
        if not company:
            raise ValueError("Company details are missing. Complete step 1 first.")
        if not branding:
            raise ValueError("Branding details are required.")

        tenant_id = onboarding.get("tenant_id") or self._generate_tenant_id()
        tenant_code = onboarding.get("tenant_code") or self._generate_tenant_code(
            company.get("name") or company.get("company_name")
        )
        login_url = self._build_login_url(company.get("name") or tenant_code)

        tenant_doc = {
            "tenant_id": tenant_id,
            "tenant_code": tenant_code,
            "company": company,
            "branding": branding,
            "onboarding_id": onboarding_id,
            "status": "active",
        }
        tenant_doc.update(build_audit_fields(prefix="created", by=admin_user.get("email")))
        self.tenants_collection.update_one(
            {"tenant_id": tenant_id},
            {"$set": tenant_doc},
            upsert=True,
        )

        admin_user_id = self._create_or_update_admin_user(
            tenant_id=tenant_id,
            admin_user=admin_user,
        )

        updates = {
            "branding": branding,
            "status": "completed",
            "current_step": 3,
            "step_completed": 3,
            "next_step": None,
            "tenant_id": tenant_id,
            "tenant_code": tenant_code,
            "admin_user_id": admin_user_id,
        }
        updates.update(build_audit_fields(prefix="updated", by=admin_user.get("email")))
        self.onboarding_collection.update_one(
            {"_id": onboarding["_id"]},
            {"$set": updates},
        )

        return {
            "tenant_id": tenant_id,
            "tenant_code": tenant_code,
            "admin_user_id": admin_user_id,
            "login_url": login_url,
        }

    def check_progress(self, email: str) -> Optional[Dict[str, Any]]:
        """Return onboarding progress for a business email."""
        if not email:
            raise ValueError("Email is required.")

        doc = self.onboarding_collection.find_one(
            {"business_email": email.strip().lower()},
            sort=[("_id", -1)],
        )
        if not doc or doc.get("status") == "completed":
            return None

        return {
            "onboarding_id": doc.get("onboarding_id"),
            "business_email": doc.get("business_email"),
            "company_name": doc.get("company", {}).get("name"),
            "current_step": doc.get("step_completed"),
            "next_step": doc.get("next_step"),
            "status": doc.get("status"),
        }

    def get_onboarding_data(self, onboarding_id: str) -> Optional[Dict[str, Any]]:
        """Fetch stored onboarding data (for resume flows)."""
        doc = self.onboarding_collection.find_one({"onboarding_id": onboarding_id})
        if not doc:
            return None

        # Convert ObjectId to string for responses
        doc["_id"] = str(doc["_id"])
        return doc

    def save_uploaded_asset(
        self,
        *,
        onboarding_id: Optional[str],
        asset_type: str,
        upload: UploadFile,
        base_path: str = "uploads",
        uploaded_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist uploaded file on disk and register asset record."""
        os.makedirs(base_path, exist_ok=True)
        filename = upload.filename or f"{asset_type}_{secrets.token_hex(4)}"
        unique_name = f"{asset_type}_{secrets.token_hex(8)}_{filename}"
        file_path = os.path.join(base_path, unique_name)

        with open(file_path, "wb") as buffer:
            buffer.write(upload.file.read())

        file_url = f"/{file_path.replace(os.sep, '/')}"

        asset_record = {
            "onboarding_id": onboarding_id,
            "asset_type": asset_type,
            "file_url": file_url,
            "original_filename": upload.filename,
        }
        asset_record.update(build_audit_fields(prefix="created", by=uploaded_by))

        assets_collection = self.client_database["tenant_onboarding_assets"]
        insert_result = assets_collection.insert_one(asset_record)
        asset_record["_id"] = str(insert_result.inserted_id)

        if onboarding_id:
            update_fields = {f"assets.{asset_type}": file_url}
            self.onboarding_collection.update_one(
                {"onboarding_id": onboarding_id},
                {"$set": update_fields, "$push": {"asset_history": asset_record}},
            )

        return asset_record

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _get_active_onboarding(self, onboarding_id: str) -> Dict[str, Any]:
        doc = self.onboarding_collection.find_one({"onboarding_id": onboarding_id})
        if not doc:
            raise ValueError("Invalid onboarding ID.")
        if doc.get("status") == "completed":
            raise ValueError("Onboarding already completed.")
        return doc

    def _generate_onboarding_id(self) -> str:
        token = secrets.token_urlsafe(6)
        return f"onb_{token.replace('-', '').lower()}"

    def _generate_tenant_id(self) -> str:
        token = secrets.token_urlsafe(6)
        return f"tenant_{token.replace('-', '').lower()}"

    def _generate_tenant_code(self, company_name: Optional[str]) -> str:
        cleaned = "".join(ch for ch in (company_name or "TEN") if ch.isalnum()).upper()
        cleaned = (cleaned or "TEN")[:6]
        suffix = "".join(secrets.choice(string.digits) for _ in range(3))
        return f"{cleaned}{suffix}"

    def _build_login_url(self, company_name: str) -> str:
        subdomain = "".join(ch for ch in (company_name or "tenant").lower() if ch.isalnum()) or "tenant"
        return f"https://{subdomain}.hrms.com/login"

    def _create_or_update_admin_user(self, tenant_id: str, admin_user: Dict[str, Any]) -> str:
        email = (admin_user.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Admin user email is required.")

        password_hash = admin_user.get("password_hash")
        if not password_hash:
            # Generate a temporary secure password if none provided
            random_password = secrets.token_urlsafe(8)
            password_hash = bcrypt.hash(random_password)

        user_doc = {
            "full_name": admin_user.get("full_name"),
            "email": email,
            "contact_number": admin_user.get("contact_number"),
            "role": "Admin",
            "tenant_id": tenant_id,
            "status": "active",
            "password": password_hash,
        }

        existing = self.users_collection.find_one({"email": email})
        if existing:
            self.users_collection.update_one(
                {"_id": existing["_id"]},
                {"$set": user_doc},
            )
            return str(existing["_id"])

        user_doc.update(build_audit_fields(prefix="created", by=email))
        result = self.users_collection.insert_one(user_doc)
        return str(result.inserted_id)


class TenantOnboardingOTPService:
    """OTP helper for onboarding email verification."""

    def __init__(self):
        self.client_database = client1["hrms_master"]
        self.otp_collection = self.client_database["tenant_onboarding_otps"]

    def send_otp(self, email: str, purpose: str = "tenant_onboarding", ttl_minutes: int = 10) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("Email is required.")

        # otp = "".join(secrets.choice(string.digits) for _ in range(6))
        otp = "123456"
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ttl_minutes)

        doc = {
            "email": email,
            "purpose": purpose,
            "otp": otp,
            "status": "sent",
            "attempts": 0,
            "created_at_utc": now,
            "expires_at_utc": expires_at,
        }
        doc.update(build_audit_fields(prefix="created", by=email))

        self.otp_collection.insert_one(doc)

        return {
            "target": self._mask_email(email),
            "expires_at": expires_at.isoformat() + "Z",
            "purpose": purpose,
        }

    def verify_otp(self, email: str, otp: str, purpose: str = "tenant_onboarding") -> Dict[str, Any]:
        email = (email or "").strip().lower()
        if not email or not otp:
            raise ValueError("Email and OTP are required.")

        record = self.otp_collection.find_one(
            {
                "email": email,
                "purpose": purpose,
                "status": {"$in": ["sent", "attempted"]},
            },
            sort=[("created_at_utc", -1)],
        )

        if not record:
            raise ValueError("No OTP found. Please request a new one.")

        now = datetime.utcnow()
        expires_at = record.get("expires_at_utc")
        if expires_at and now > expires_at:
            self.otp_collection.update_one(
                {"_id": record["_id"]},
                {"$set": {"status": "expired", "expired_at_utc": now}},
            )
            raise ValueError("OTP expired. Please request a new one.")

        if str(record.get("otp")) != str(otp):
            self.otp_collection.update_one(
                {"_id": record["_id"]},
                {
                    "$inc": {"attempts": 1},
                    "$set": {"status": "attempted", "last_attempt_at_utc": now},
                },
            )
            raise ValueError("Invalid OTP.")

        verification_token = secrets.token_urlsafe(24)
        token_expires_at = now + timedelta(minutes=15)

        self.otp_collection.update_one(
            {"_id": record["_id"]},
            {
                "$set": {
                    "status": "verified",
                    "verified_at_utc": now,
                    "verification_token": verification_token,
                    "verification_token_expires_at": token_expires_at,
                }
            },
        )

        return {
            "verification_token": verification_token,
            "verification_token_expires_at": token_expires_at.isoformat() + "Z",
            "purpose": purpose,
        }

    @staticmethod
    def _mask_email(email: str) -> str:
        if "@" not in email:
            return "***"
        name, domain = email.split("@", 1)
        if len(name) <= 2:
            masked = name[0] + "*" * (len(name) - 1) if name else "***"
        else:
            masked = name[0] + "***" + name[-1]
        return f"{masked}@{domain}"
