from typing import Dict, Any, List
from datetime import datetime
from sfa.database import client1
from bson import ObjectId
import pytz

from sfa.utils.date_utils import build_audit_fields
from sfa.services.app_otp_services import AppOTPService


class AppOrderService:
    # Yeh service Orders ke business logic handle karti hai (create, validations, DB write)
    def __init__(self):
        # Tenant DB select (multi-tenant ke liye future ready)
        self.client_database = client1["talbros"]
        # Orders, Customers aur Products collections
        self.orders_collection = self.client_database["orders"]
        self.customers_collection = self.client_database["customers"]
        self.products_collection = self.client_database["products"]
        self.timezone = pytz.timezone("Asia/Kolkata")

    def _round2(self, value: float) -> float:
        # Monetary values ko 2 decimals tak round karne ka helper
        return float(f"{value:.2f}")

    def _validate_order_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Top-level required fields check (frontend se kuch miss na ho)
        required_top = [
            "customer_id",
            "customer_type",
            "order_items",
            "subtotal",
            "total_amount",
            "order_date",
            "order_type",
            "status",
        ]
        for key in required_top:
            if key not in payload or payload[key] in [None, "", []]:
                return {
                    "success": False,
                    "message": f"{key} is required",
                    "error": {"code": "VALIDATION_ERROR", "details": f"Missing field: {key}"},
                }

        if not isinstance(payload["order_items"], list) or len(payload["order_items"]) == 0:
            return {
                "success": False,
                "message": "order_items must be a non-empty list",
                "error": {"code": "VALIDATION_ERROR", "details": "order_items invalid"},
            }

        # Per-item validation aur Products collection ke against cross-check
        # Goal: frontend calculation galat ho toh server sahi values compute karke verify kare
        normalized_items: List[Dict[str, Any]] = []
        customer_type = str(payload.get("customer_type", "")).strip()
        # Safely read customer_type_id (0 if missing)
        try:
            customer_type_id = int(payload.get("customer_type_id", 0) or 0)
        except Exception:
            customer_type_id = 0
        for idx, item in enumerate(payload["order_items"]):
            # Minimum required item fields (baaki fields hum compute kar denge)
            for f in ["product_id", "sku_code", "quantity"]:
                if f not in item:
                    return {
                        "success": False,
                        "message": f"order_items[{idx}].{f} is required",
                        "error": {"code": "VALIDATION_ERROR", "details": f"Missing field: order_items[{idx}].{f}"},
                    }
            try:
                qty = float(item["quantity"])
            except Exception:
                return {
                    "success": False,
                    "message": f"order_items[{idx}].quantity must be a number",
                    "error": {"code": "VALIDATION_ERROR", "details": f"Invalid quantity at index {idx}"},
                }
            if qty <= 0:
                return {
                    "success": False,
                    "message": f"order_items[{idx}].quantity must be > 0",
                    "error": {"code": "VALIDATION_ERROR", "details": "Quantity must be greater than 0"},
                }

            # Product fetch: pehle _id se, agar format/record na mile toh sku_code se
            product = None
            prod_err_details = None
            try:
                product = self.products_collection.find_one({"_id": ObjectId(item["product_id"])})
            except Exception:
                prod_err_details = "Invalid product_id format"
            if not product:
                product = self.products_collection.find_one({"sku_code": item.get("sku_code")})
                if not product and prod_err_details is None:
                    prod_err_details = "Product not found by product_id or sku_code"
            if not product:
                return {
                    "success": False,
                    "message": f"Product not found for order_items[{idx}]",
                    "error": {"code": "PRODUCT_NOT_FOUND", "details": prod_err_details},
                }

            # Discount policy: customer_type ke hisaab se max allowed discount (server side enforce)
            allowed_discount = 0.0
            try:
                if customer_type_id == 1: # Distributor
                    allowed_discount = float(product.get("distributor_discount", 0) or 0)
                    print("allowed_discount", allowed_discount)
                else: # Retailer or Dealer
                    allowed_discount = float(product.get("retailer_discount", 0) or 0)
                    print("allowed_discount", allowed_discount)
            except Exception:
                allowed_discount = 0.0

            provided_discount_pct = float(item.get("discount_percentage") or 0)
            if provided_discount_pct < 0:
                return {
                    "success": False,
                    "message": f"order_items[{idx}] (product_id={item.get('product_id')}).discount_percentage cannot be negative",
                    "error": {"code": "VALIDATION_ERROR", "details": "Negative discount not allowed"},
                }
            if provided_discount_pct - allowed_discount > 0.001:
                return {
                    "success": False,
                    "message": f"order_items[{idx}] (product_id={item.get('product_id')}).discount_percentage exceeds allowed ({allowed_discount}%)",
                    "error": {"code": "DISCOUNT_NOT_ALLOWED", "details": f"Provided {provided_discount_pct}% > allowed {allowed_discount}%"},
                }

            # Pricing computation (server-truth):
            # unit_price -> product.price
            # discount_amount_per_unit -> unit_price * (discount%/100)
            # net_price_per_unit -> unit_price - discount_amount_per_unit
            # total_discount_amount -> discount_amount_per_unit * quantity
            # total_amount -> net_price_per_unit * quantity
            unit_price_expected = float(product.get("price", 0))
            discount_amount_per_unit = unit_price_expected * (provided_discount_pct / 100.0)
            net_price_per_unit = unit_price_expected - discount_amount_per_unit
            total_discount_amount = discount_amount_per_unit * qty
            total_expected = net_price_per_unit * qty

            # Round for monetary comparison
            unit_price_expected_r = self._round2(unit_price_expected)
            discount_amount_per_unit_r = self._round2(discount_amount_per_unit)
            net_price_per_unit_r = self._round2(net_price_per_unit)
            total_discount_amount_r = self._round2(total_discount_amount)
            total_expected_r = self._round2(total_expected)

            # Frontend provided values vs server-computed values compare
            def mismatch(provided, expected):
                try:
                    return abs(float(provided) - float(expected)) > 0.01
                except Exception:
                    return True

            provided_unit = item.get("unit_price", unit_price_expected_r)
            provided_disc_amt = item.get("discount_amount", total_discount_amount_r)
            provided_net = item.get("net_price", total_expected_r)  # Frontend sends total amount as net_price
            provided_total = item.get("total_amount", total_expected_r)

            if mismatch(provided_unit, unit_price_expected_r) or mismatch(provided_disc_amt, total_discount_amount_r) or mismatch(provided_net, total_expected_r) or mismatch(provided_total, total_expected_r):
                return {
                    "success": False,
                    "message": f"Price calculation mismatch for order_items[{idx}]",
                    "error": {
                        "code": "PRICE_VALIDATION_FAILED",
                        "details": {
                            "expected": {
                                "unit_price": unit_price_expected_r,
                                "discount_percentage": provided_discount_pct,
                                "discount_amount": total_discount_amount_r,
                                "net_price": total_expected_r,  # Frontend sends total as net_price
                                "total_amount": total_expected_r,
                            },
                            "provided": {
                                "unit_price": provided_unit,
                                "discount_percentage": provided_discount_pct,
                                "discount_amount": provided_disc_amt,
                                "net_price": provided_net,
                                "total_amount": provided_total,
                            },
                        },
                    },
                }

            # Store normalized, server-verified item values (consistent persistence)
            # Note: net_price stored as per unit for consistency, but frontend sends total
            normalized_items.append({
                "product_id": str(product.get("_id")),
                "product_name": item.get("product_name") or product.get("name"),
                "sku_code": product.get("sku_code"),
                "quantity": qty,
                "unit_price": unit_price_expected_r,
                "discount_percentage": provided_discount_pct,
                "discount_amount": total_discount_amount_r,
                "net_price": net_price_per_unit_r,  # Store per unit net price for consistency
                "total_amount": total_expected_r,
            })

        # Validate subtotal/total
        try:
            provided_subtotal = float(payload["subtotal"])
            provided_total = float(payload["total_amount"])
        except Exception:
            return {
                "success": False,
                "message": "subtotal and total_amount must be numbers",
                "error": {"code": "VALIDATION_ERROR", "details": "Invalid subtotal/total_amount"},
            }

        # Subtotal ko hamesha server par recompute kiya jaata hai (tamper-proof)
        computed_subtotal = sum(float(i["total_amount"]) for i in normalized_items)
        # Allow small rounding tolerance
        if abs(computed_subtotal - provided_subtotal) > 0.01:
            return {
                "success": False,
                "message": "subtotal mismatch",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "details": f"Provided subtotal {provided_subtotal} != computed {computed_subtotal}",
                },
            }

        # Abhi ke liye extra charges (tax/shipping) support nahi hai, isliye total == subtotal enforce
        if abs(provided_total - provided_subtotal) > 0.01:
            return {
                "success": False,
                "message": "total_amount must equal subtotal (no extra charges supported)",
                "error": {"code": "VALIDATION_ERROR", "details": "total_amount != subtotal"},
            }

        # Validate order_date
        try:
            datetime.strptime(payload["order_date"], "%Y-%m-%d")
        except Exception:
            return {
                "success": False,
                "message": "order_date must be YYYY-MM-DD",
                "error": {"code": "VALIDATION_ERROR", "details": "Invalid order_date format"},
            }

        return {"success": True, "items": normalized_items, "computed_subtotal": self._round2(computed_subtotal)}

    def create_order(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Public API method: payload validate karo, pricing verify karo, phir DB me order insert karo
        try:
            # OTP verification token required for secure order creation
            verification_token = payload.get("verification_token")
            if not verification_token:
                return {
                    "success": False,
                    "message": "verification_token is required",
                    "error": {"code": "OTP_REQUIRED", "details": "Please verify OTP and include verification_token"},
                }

            otp_service = AppOTPService()
            token_check = otp_service.validate_verification_token(
                verification_token=verification_token,
                purpose="order_create",
                entity_type="order",
                consume=True,
            )
            if not token_check.get("success"):
                return {
                    "success": False,
                    "message": token_check.get("message", "OTP verification required"),
                    "error": token_check.get("error", {"code": "OTP_INVALID"}),
                }

            validation = self._validate_order_payload(payload)
            if not validation.get("success"):
                return validation

            # Build order doc
            # Audit fields: created_* / updated_* (date + time + by) for traceability
            created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")

            order_doc: Dict[str, Any] = {
                "customer_id": payload["customer_id"],
                "customer_type": payload.get("customer_type"),
                "customer_type_id": payload.get("customer_type_id"),
                "customer_type_name": payload.get("customer_type_name"),
                "order_items": validation.get("items", payload["order_items"]),
                "subtotal": float(validation.get("computed_subtotal", payload["subtotal"])),
                "total_amount": float(validation.get("computed_subtotal", payload["total_amount"])),
                "order_date": payload["order_date"],
                "order_type": payload.get("order_type", "Primary"),
                "notes": payload.get("notes", ""),
                "status": payload.get("status", "pending"),
                **created_fields,
                **updated_fields,
                "verification_token": verification_token,
            }

            result = self.orders_collection.insert_one(order_doc)
            if not result.inserted_id:
                return {
                    "success": False,
                    "message": "Failed to create order",
                    "error": {"code": "DATABASE_ERROR", "details": "Insert failed"},
                }

            return {
                "success": True,
                "message": "Order created successfully",
                "data": {
                    "order_id": str(result.inserted_id),
                    "status": order_doc["status"],
                    "subtotal": order_doc["subtotal"],
                    "total_amount": order_doc["total_amount"],
                    "verification_token": verification_token,
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create order: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }


    def list_orders(self, user_id: str, page: int = 1, limit: int = 20, status: str = "all", customer_id: str = None, date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        try:
            query: Dict[str, Any] = {}
            if customer_id:
                query["customer_id"] = customer_id
            if status and status != "all":
                query["status"] = status
            if date_from:
                query["order_date"] = {"$gte": date_from}
            if date_to:
                if "order_date" in query:
                    query["order_date"]["$lte"] = date_to
                else:
                    query["order_date"] = {"$lte": date_to}

            total = self.orders_collection.count_documents(query)
            skip = (page - 1) * limit
            orders = list(self.orders_collection.find(query).sort("created_at", -1).skip(skip).limit(limit))

            def to_dict(doc: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    "order_id": str(doc.get("_id")),
                    "customer_id": doc.get("customer_id"),
                    "customer_type": doc.get("customer_type"),
                    "status": doc.get("status"),
                    "subtotal": doc.get("subtotal"),
                    "total_amount": doc.get("total_amount"),
                    "order_date": doc.get("order_date"),
                    "created_at": doc.get("created_at"),
                }

            data_list = [to_dict(o) for o in orders]
            total_pages = (total + limit - 1) // limit
            pagination = {
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages,
                "hasNext": page < total_pages,
                "hasPrev": page > 1
            }

            return {"success": True, "data": {"orders": data_list, "pagination": pagination}}
        except Exception as e:
            return {"success": False, "message": f"Failed to list orders: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}


    def get_order_detail(self, user_id: str, order_id: str) -> Dict[str, Any]:
        try:
            try:
                oid = ObjectId(order_id)
            except Exception:
                return {"success": False, "message": "Invalid order_id", "error": {"code": "VALIDATION_ERROR", "details": "order_id must be ObjectId"}}

            doc = self.orders_collection.find_one({"_id": oid})
            if not doc:
                return {"success": False, "message": "Order not found", "error": {"code": "NOT_FOUND"}}

            detail = {
                "order_id": str(doc.get("_id")),
                "customer_id": doc.get("customer_id"),
                "customer_type": doc.get("customer_type"),
                "customer_type_id": doc.get("customer_type_id"),
                "customer_type_name": doc.get("customer_type_name"),
                "order_items": doc.get("order_items", []),
                "subtotal": doc.get("subtotal"),
                "total_amount": doc.get("total_amount"),
                "order_date": doc.get("order_date"),
                "order_type": doc.get("order_type"),
                "notes": doc.get("notes"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
            }
            return {"success": True, "data": detail}
        except Exception as e:
            return {"success": False, "message": f"Failed to get order detail: {str(e)}", "error": {"code": "SERVER_ERROR", "details": str(e)}}

