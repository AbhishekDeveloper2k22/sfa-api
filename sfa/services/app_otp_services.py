from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
import pytz
from sfa.database import client1
import secrets
from sfa.utils.date_utils import build_audit_fields


class AppOTPService:
    # Common OTP service: OTP generate, store, verify + logging
    def __init__(self):
        self.client_database = client1["talbros"]
        self.otp_collection = self.client_database["otp_logs"]
        self.timezone = pytz.timezone("Asia/Kolkata")

    def _now(self):
        return datetime.now(self.timezone)

    def _generate_otp(self, digits: int = 6) -> str:
        # Simple numeric OTP generator
        start = 10 ** (digits - 1)
        end = (10 ** digits) - 1
        return str(random.randint(start, end))

    def send_otp(self, target: str, purpose: str, channel: str = "sms", ttl_minutes: int = 5, entity_type: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not target or not purpose:
                return {"success": False, "message": "target and purpose are required", "error": {"code": "VALIDATION_ERROR"}}

            otp = self._generate_otp(6)
            now = self._now()
            expires_at = now + timedelta(minutes=ttl_minutes)
            created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")

            # In real-world, integrate with SMS/Email gateway here
            # For now, we store and return masked info

            doc = {
                "target": target,              # e.g. phone/email
                "purpose": purpose,            # e.g. login, password_reset, change_phone
                "channel": channel,            # sms/email
                "otp": otp,
                "status": "sent",            # sent, verified, expired, failed
                "attempts": 0,
                **created_fields,
                "expires_at": expires_at.isoformat(),
                # Optional linking to any business entity (order, expense, etc.)
                "entity_type": entity_type,
            }

            result = self.otp_collection.insert_one(doc)
            if not result.inserted_id:
                return {"success": False, "message": "Failed to store OTP", "error": {"code": "DATABASE_ERROR"}}

            return {
                "success": True,
                "message": "OTP sent successfully",
                "data": {
                    "otp_id": str(result.inserted_id),
                    "target_masked": self._mask_target(target),
                    "expires_at": doc["expires_at"],
                    "entity_type": entity_type,
                    "otp": otp,
                    # NOTE: Do not return OTP in production APIs. For testing, include if needed.
                }
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to send OTP: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}

    def verify_otp(self, target: str, purpose: str, otp: str) -> Dict[str, Any]:
        try:
            if not target or not purpose or not otp:
                return {"success": False, "message": "target, purpose and otp are required", "error": {"code": "VALIDATION_ERROR"}}

            # Get latest unverified OTP for this target+purpose
            record = self.otp_collection.find_one({
                "target": target,
                "purpose": purpose,
                "status": {"$in": ["sent", "attempted"]}
            }, sort=[("created_at", -1)])

            if not record:
                return {"success": False, "message": "No active OTP found", "error": {"code": "OTP_NOT_FOUND"}}

            now = self._now()
            if record.get("expires_at") and now > datetime.fromisoformat(record["expires_at"]):
                # Mark expired
                self.otp_collection.update_one({"_id": record["_id"]}, {"$set": {"status": "expired", "expired_at": now.isoformat()}})
                return {"success": False, "message": "OTP expired", "error": {"code": "OTP_EXPIRED"}}

            # Compare OTP
            if str(otp) != str(record.get("otp")):
                self.otp_collection.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}, "$set": {"status": "attempted", "last_attempt_at": now.isoformat()}})
                return {"success": False, "message": "Invalid OTP", "error": {"code": "OTP_INVALID", "details": {"attempts": record.get("attempts", 0) + 1}}}

            # Mark verified and issue a short-lived verification token (to be used by sensitive flows like order create)
            verification_token = secrets.token_urlsafe(24)
            token_ttl_minutes = 10
            token_expires_at = (now + timedelta(minutes=token_ttl_minutes)).isoformat()

            self.otp_collection.update_one(
                {"_id": record["_id"]},
                {"$set": {
                    "status": "verified",
                    "verified_at": now.isoformat(),
                    "verification_token": verification_token,
                    "verification_token_expires_at": token_expires_at,
                    "verification_token_consumed": False
                }}
            )

            return {
                "success": True,
                "message": "OTP verified successfully",
                "data": {
                    "verified_at": now.isoformat(),
                    "purpose": purpose,
                    "verification_token": verification_token,
                    "verification_token_expires_at": token_expires_at
                }
            }

        except Exception as e:
            return {"success": False, "message": f"Failed to verify OTP: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}

    def validate_verification_token(self, verification_token: str, purpose: Optional[str] = None, target: Optional[str] = None, entity_type: Optional[str] = None, consume: bool = True) -> Dict[str, Any]:
        """
        Verify that a previously issued verification token is valid, unexpired and (optionally) linked
        to the same purpose/target/entity. Optionally mark it consumed.
        """
        try:
            if not verification_token:
                return {"success": False, "message": "verification_token is required", "error": {"code": "VALIDATION_ERROR"}}

            query: Dict[str, Any] = {
                "verification_token": verification_token,
                "status": "verified",
                "verification_token_consumed": {"$ne": True}
            }
            if purpose:
                query["purpose"] = purpose
            if target:
                query["target"] = target
            if entity_type is not None:
                query["entity_type"] = entity_type

            record = self.otp_collection.find_one(query, sort=[("verified_at", -1)])
            if not record:
                return {"success": False, "message": "Invalid or already used token", "error": {"code": "TOKEN_INVALID"}}

            now = self._now()
            if record.get("verification_token_expires_at") and now > datetime.fromisoformat(record["verification_token_expires_at"]):
                return {"success": False, "message": "Verification token expired", "error": {"code": "TOKEN_EXPIRED"}}

            if consume:
                self.otp_collection.update_one({"_id": record["_id"]}, {"$set": {"verification_token_consumed": True, "token_consumed_at": now.isoformat()}})

            return {"success": True, "data": {"purpose": record.get("purpose"), "target": record.get("target"), "entity_type": record.get("entity_type")}}
        except Exception as e:
            return {"success": False, "message": f"Failed to validate token: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}

    def _mask_target(self, target: str) -> str:
        # Phone/email masking utility for responses
        if "@" in target:
            name, domain = target.split("@", 1)
            masked = (name[0] + "***" + name[-1]) if len(name) > 2 else "***"
            return f"{masked}@{domain}"
        # assume phone
        if len(target) >= 4:
            return "*" * (len(target) - 4) + target[-4:]
        return "***"


