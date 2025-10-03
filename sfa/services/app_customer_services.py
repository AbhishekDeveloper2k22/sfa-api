from sfa.database import client1
from bson import ObjectId
from typing import Dict, Any
from datetime import datetime
import traceback

class AppCustomerService:
    def __init__(self):
        self.talbros_db = client1['talbros']
        self.customers = self.talbros_db['customers']
        self.orders = self.talbros_db['orders']
        self.checkins = self.talbros_db['customer_checkins']
        self.all_types = self.talbros_db['all_type']

    def _safe_str(self, v: Any) -> str:
        return "" if v is None else str(v)

    def get_customer_profile(self, customer_id: str, user_id: str) -> Dict[str, Any]:
        try:
            try:
                obj_id = ObjectId(customer_id)
            except Exception:
                return {"success": False, "message": "Invalid customer_id", "error": {"code": "VALIDATION_ERROR"}}

            # Get customer with user assignment check
            customer = self.customers.find_one({
                "_id": obj_id, 
                "assign_user_id": user_id,
                "del": {"$ne": 1}
            })
            if not customer:
                return {"success": False, "message": "Customer not found or not assigned to you", "error": {"code": "CUSTOMER_NOT_FOUND"}}

            # Get customer type name from all_type collection
            customer_type_name = ""
            if customer.get("customer_type"):
                customer_type_doc = self.all_types.find_one({
                    "customer_type": customer.get("customer_type"),
                    "del": {"$ne": 1}
                })
                if customer_type_doc:
                    customer_type_name = customer_type_doc.get("name", "")

            # Stats
            total_sales = 0.0
            total_orders = 0
            total_visits = 0
            
            # Check if orders collection exists and get stats
            try:
                total_orders = self.orders.count_documents({"customer_id": str(obj_id), "del": {"$ne": 1}})
                agg = self.orders.aggregate([
                    {"$match": {"customer_id": str(obj_id), "del": {"$ne": 1}}},
                    {"$group": {"_id": None, "sum": {"$sum": "$grand_total"}}}
                ])
                for row in agg:
                    total_sales = float(row.get('sum', 0.0))
            except Exception:
                # Collection might not exist or have different structure
                pass
            
            # Check if checkins collection exists and get visit count
            try:
                total_visits = self.checkins.count_documents({"customer_id": str(obj_id)})
            except Exception:
                # Collection might not exist or have different structure
                pass

            # Check checkin status for today
            from datetime import datetime as _dt
            today_str = _dt.now().strftime('%Y-%m-%d')
            checkin_status = "can_start_checkin"  # Default status
            
            # First, check if user has any active checkin with ANY customer today
            any_active_checkin = self.checkins.find_one({
                "user_id": user_id,
                "plan_date": today_str,
                "status": "in",
                "del": {"$ne": 1}
            })
            
            # Check if there's a checkin record for this specific customer today
            checkin_record = self.checkins.find_one({
                "user_id": user_id,
                "customer_id": str(obj_id),
                "plan_date": today_str,
                "del": {"$ne": 1}
            })
            
            if checkin_record:
                # User has a checkin record for this customer
                if checkin_record.get("status") == "in":
                    checkin_status = "can_end_checkin"
                elif checkin_record.get("status") in ["out", "completed"]:
                    checkin_status = "completed"
            elif any_active_checkin:
                # User has active checkin with another customer
                checkin_status = "blocked_by_other_checkin"
            else:
                # No checkin record for this customer and no active checkin elsewhere
                checkin_status = "can_start_checkin"

            profile = {
                "id": str(customer["_id"]),
                "name": customer.get("name", ""),
                "company_name": customer.get("company_name", ""),
                "customer_type": customer_type_name,
                "customer_type_id": customer.get("customer_type"),
                "status": customer.get("status", "active"),
                "phone": customer.get("mobile") or customer.get("phone", ""),
                "address": customer.get("billing_address", ""),
                "city": customer.get("city", ""),
                "state": customer.get("state", ""),
                "pincode": customer.get("pincode", ""),
                "country": customer.get("country", ""),
                "totalSales": total_sales,
                "totalOrders": total_orders,
                "totalVisits": total_visits,
                "checkin_status": checkin_status
            }
            return {"success": True, "data": profile}
        except Exception as e:
            return {"success": False, "message": f"Failed to get profile: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}
