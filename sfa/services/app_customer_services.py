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
                    {"$group": {"_id": None, "sum": {"$sum": "$total_amount"}}}
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
                "total_sales": total_sales,
                "total_orders": total_orders,
                "total_visits": total_visits,
                "checkin_status": checkin_status
            }
            return {"success": True, "data": profile}
        except Exception as e:
            return {"success": False, "message": f"Failed to get profile: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}

    def get_customer_list(self, user_id: str, status_filter: str = "all", page: int = 1, limit: int = 20) -> Dict[str, Any]:
        try:
            # Build query based on filters
            query = {
                "assign_user_id": user_id,
                "del": {"$ne": 1}
            }
            
            # Apply status filter
            if status_filter == "active":
                query["status"] = "active"
            elif status_filter == "pending":
                query["status"] = {"$in": ["pending", "inactive"]}
            # For "all", no additional status filter needed
            
            # Calculate skip for pagination
            skip = (page - 1) * limit
            
            # Get total count
            total_count = self.customers.count_documents(query)
            
            # Get customers with pagination
            customers_cursor = self.customers.find(query).skip(skip).limit(limit).sort("created_at", -1)
            customers = list(customers_cursor)
            
            # Get customer type names for all customers
            customer_type_ids = [c.get("customer_type") for c in customers if c.get("customer_type")]
            customer_types = {}
            if customer_type_ids:
                type_docs = self.all_types.find({
                    "customer_type": {"$in": customer_type_ids},
                    "del": {"$ne": 1}
                })
                for type_doc in type_docs:
                    customer_types[type_doc.get("customer_type")] = type_doc.get("name", "")
            
            # Get order stats for all customers
            customer_ids = [str(c["_id"]) for c in customers]
            order_stats = {}
            if customer_ids:
                try:
                    # Get order counts and total values
                    agg_pipeline = [
                        {"$match": {"customer_id": {"$in": customer_ids}, "del": {"$ne": 1}}},
                        {"$group": {
                            "_id": "$customer_id",
                            "total_orders": {"$sum": 1},
                            "total_value": {"$sum": "$total_amount"},
                            "last_order_date": {"$max": "$created_at"}
                        }}
                    ]
                    order_agg = self.orders.aggregate(agg_pipeline)
                    for stat in order_agg:
                        order_stats[stat["_id"]] = {
                            "total_orders": stat.get("total_orders", 0),
                            "total_value": float(stat.get("total_value", 0)),
                            "last_order_date": stat.get("last_order_date", "")
                        }
                except Exception:
                    # Orders collection might not exist
                    pass
            
            # Format customer list
            customer_list = []
            for customer in customers:
                customer_id = str(customer["_id"])
                customer_type_name = customer_types.get(customer.get("customer_type"), "")
                order_stat = order_stats.get(customer_id, {"total_orders": 0, "total_value": 0.0, "last_order_date": ""})
                
                customer_data = {
                    "id": customer_id,
                    "name": customer.get("name", ""),
                    "company_name": customer.get("company_name", ""),
                    "email": customer.get("email", ""),
                    "phone": customer.get("mobile") or customer.get("phone", ""),
                    "alternate_phone": customer.get("alternate_phone", ""),
                    "whatsapp": customer.get("whatsapp", ""),
                    "type": customer.get("type", ""),
                    "customer_type": customer_type_name,
                    "customer_type_id": customer.get("customer_type"),
                    "status": customer.get("status", "active"),
                    "address": customer.get("billing_address", ""),
                    "city": customer.get("city", ""),
                    "state": customer.get("state", ""),
                    "pincode": customer.get("pincode", ""),
                    "latitude": customer.get("latitude", ""),
                    "longitude": customer.get("longitude", ""),
                    "gst_number": customer.get("gst_number", ""),
                    "pan_number": customer.get("pan_number", ""),
                    "credit_limit": customer.get("credit_limit", ""),
                    "contact_person": customer.get("contact_person", ""),
                    "designation": customer.get("designation", ""),
                    "created_at": customer.get("created_at", ""),
                    "created_at_time": customer.get("created_at_time", ""),
                    "total_orders": order_stat["total_orders"],
                    "total_value": order_stat["total_value"],
                    "last_order_date": order_stat["last_order_date"]
                }
                customer_list.append(customer_data)
            
            # Count by status for summary
            status_counts = {
                "all": total_count,
                "active": 0,
                "pending": 0
            }
            
            # Get status counts
            try:
                active_count = self.customers.count_documents({
                    "assign_user_id": user_id,
                    "status": "active",
                    "del": {"$ne": 1}
                })
                pending_count = self.customers.count_documents({
                    "assign_user_id": user_id,
                    "status": {"$in": ["pending", "inactive"]},
                    "del": {"$ne": 1}
                })
                status_counts["active"] = active_count
                status_counts["pending"] = pending_count
            except Exception:
                pass
            
            return {
                "success": True,
                "data": {
                    "customers": customer_list,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "total_pages": (total_count + limit - 1) // limit
                    },
                    "status_counts": status_counts
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Failed to get customer list: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e), "traceback": traceback.format_exc()}}
