from typing import Dict, Any, List
from datetime import datetime
from sfa.database import client1
from bson import ObjectId
import pytz

from sfa.utils.date_utils import build_audit_fields


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
            "created_by",
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
                else: # Retailer or Dealer
                    allowed_discount = float(product.get("retailer_discount", 0) or 0)
            except Exception:
                allowed_discount = 0.0

            provided_discount_pct = float(item.get("discount_percentage") or 0)
            if provided_discount_pct < 0:
                return {
                    "success": False,
                    "message": f"order_items[{idx}].discount_percentage cannot be negative",
                    "error": {"code": "VALIDATION_ERROR", "details": "Negative discount not allowed"},
                }
            if provided_discount_pct - allowed_discount > 0.001:
                return {
                    "success": False,
                    "message": f"order_items[{idx}].discount_percentage exceeds allowed ({allowed_discount}%)",
                    "error": {"code": "DISCOUNT_NOT_ALLOWED", "details": f"Provided {provided_discount_pct}% > allowed {allowed_discount}%"},
                }

            # Pricing computation (server-truth):
            # unit_price -> product.price
            # discount_amount -> unit_price * (discount%/100)
            # net_price -> unit_price - discount_amount
            # total_amount -> net_price * quantity
            unit_price_expected = float(product.get("price", 0))
            discount_amount_expected = unit_price_expected * (provided_discount_pct / 100.0)
            net_price_expected = unit_price_expected - discount_amount_expected
            total_expected = net_price_expected * qty

            # Round for monetary comparison
            unit_price_expected_r = self._round2(unit_price_expected)
            discount_amount_expected_r = self._round2(discount_amount_expected)
            net_price_expected_r = self._round2(net_price_expected)
            total_expected_r = self._round2(total_expected)

            # Frontend provided values vs server-computed values compare
            def mismatch(provided, expected):
                try:
                    return abs(float(provided) - float(expected)) > 0.01
                except Exception:
                    return True

            provided_unit = item.get("unit_price", unit_price_expected_r)
            provided_disc_amt = item.get("discount_amount", discount_amount_expected_r)
            provided_net = item.get("net_price", net_price_expected_r)
            provided_total = item.get("total_amount", total_expected_r)

            if mismatch(provided_unit, unit_price_expected_r) or mismatch(provided_disc_amt, discount_amount_expected_r) or mismatch(provided_net, net_price_expected_r) or mismatch(provided_total, total_expected_r):
                return {
                    "success": False,
                    "message": f"Price calculation mismatch for order_items[{idx}]",
                    "error": {
                        "code": "PRICE_VALIDATION_FAILED",
                        "details": {
                            "expected": {
                                "unit_price": unit_price_expected_r,
                                "discount_percentage": provided_discount_pct,
                                "discount_amount": discount_amount_expected_r,
                                "net_price": net_price_expected_r,
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
            normalized_items.append({
                "product_id": str(product.get("_id")),
                "product_name": item.get("product_name") or product.get("name"),
                "sku_code": product.get("sku_code"),
                "quantity": qty,
                "unit_price": unit_price_expected_r,
                "discount_percentage": provided_discount_pct,
                "discount_amount": discount_amount_expected_r,
                "net_price": net_price_expected_r,
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
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create order: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)},
            }


