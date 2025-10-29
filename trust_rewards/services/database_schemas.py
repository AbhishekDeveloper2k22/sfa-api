"""
Database Schema Information for Trust Rewards MongoDB Collections
This module contains the complete schema definitions for all collections
used by the AI Agent service.
"""

SCHEMA_INFO = {
    "category_master": {
        "description": "Product categories in the system",
        "fields": {
            "_id": "ObjectId - Unique identifier",
            "category_name": "string - Name of category",
            "category_name_lower": "string - Lowercase name for search",
            "description": "string - Category description",
            "status": "string - active/inactive",
            "created_at": "string - Date created (YYYY-MM-DD)",
            "created_time": "string - Time created (HH:MM:SS)",
            "created_by": "int - User ID who created",
            "updated_at": "string - Date updated",
            "updated_by": "int - User ID who updated",
            "updated_time": "string - Time updated"
        },
        "example": {
            "category_name": "Power Tools",
            "status": "active",
            "description": "Power tools including drills, grinders..."
        }
    },
    "coupon_code": {
        "description": "Individual coupon codes",
        "fields": {
            "_id": "ObjectId - Unique coupon code ID",
            "coupon_master_id": "string - Reference to coupon_master",
            "coupon_value": "int - Points value",
            "valid_from": "string - Start date",
            "valid_to": "string - End date",
            "status": "string - scanned/unscanned",
            "is_scanned": "boolean - Scanned status",
            "scanned_by": "string - Worker ID who scanned",
            "scanned_at": "datetime - Scan timestamp",
            "created_at": "string - Created date",
            "coupon_code": "string - Actual coupon code"
        }
    },
    "coupon_master": {
        "description": "Coupon batch master data",
        "fields": {
            "_id": "ObjectId - Batch ID",
            "coupon_id": "string - Coupon identifier",
            "batch_number": "string - Batch number (BATCH001)",
            "points_value": "int - Points per coupon",
            "number_of_coupons": "int - Total coupons in batch",
            "valid_from": "string - Start date",
            "valid_to": "string - End date",
            "status": "string - active/inactive",
            "created_at": "string - Created date"
        }
    },
    "coupon_scanned_history": {
        "description": "History of all coupon scans",
        "fields": {
            "_id": "ObjectId",
            "coupon_id": "string - Coupon code ID",
            "worker_id": "string - Worker ID",
            "worker_name": "string - Worker name",
            "worker_mobile": "string - Worker phone",
            "points_earned": "int - Points earned",
            "scanned_at": "datetime - Scan timestamp",
            "scanned_date": "string - Scan date",
            "scanned_time": "string - Scan time",
            "coupon_master_id": "string - Batch reference",
            "batch_number": "string - Batch number"
        }
    },
    "gift_master": {
        "description": "Gift catalog for redemption",
        "fields": {
            "_id": "ObjectId",
            "gift_name": "string - Gift name",
            "gift_name_lower": "string - Lowercase for search",
            "description": "string - Gift description",
            "points_required": "int - Points needed to redeem",
            "status": "string - active/inactive",
            "created_at": "string - Created date",
            "images": "array - Array of image objects"
        }
    },
    "gift_redemptions": {
        "description": "Gift redemption requests and history",
        "fields": {
            "_id": "ObjectId - Unique redemption ID",
            "redemption_id": "string - Redemption identifier",
            "worker_id": "string - Worker ID",
            "worker_name": "string - Worker name",
            "worker_mobile": "string - Worker phone",
            "gift_id": "string - Gift master reference",
            "gift_name": "string - Gift name",
            "points_used": "int - Points deducted",
            "status": "string - pending/approved/cancelled/completed",
            "request_date": "string - Request date (YYYY-MM-DD)",
            "request_time": "string - Request time (HH:MM:SS)",
            "request_datetime": "datetime - Request timestamp",
            "redemption_date": "string - Redemption date",
            "redemption_time": "string - Redemption time",
            "redemption_datetime": "datetime - Redemption timestamp",
            "cancelled_at": "datetime - Cancellation timestamp",
            "cancelled_date": "string - Cancellation date",
            "cancelled_time": "string - Cancellation time",
            "status_history": "array - Status change history",
            "status_change_by_id": "string - User who changed status",
            "status_change_date": "string - Status change date",
            "status_changed_time": "string - Status change time",
            "created_at": "string - Created date",
            "created_time": "string - Created time",
            "created_by": "string - Created by user",
            "updated_at": "string - Updated date",
            "updated_time": "string - Updated time",
            "updated_by": "string - Updated by user"
        }
    },
    "location_master": {
        "description": "Indian postal location and pincode master data",
        "fields": {
            "_id": "ObjectId - Unique location ID",
            "pincode": "string - PIN code",
            "officename": "string - Post office name",
            "officetype": "string - Office type (BO/SO/HO)",
            "delivery": "string - Delivery status",
            "district": "string - District name",
            "statename": "string - State name",
            "circlename": "string - Circle name",
            "regionname": "string - Region name",
            "divisionname": "string - Division name",
            "latitude": "string - Latitude coordinate",
            "longitude": "string - Longitude coordinate"
        }
    },
    "points_master": {
        "description": "Points configuration and rules master",
        "fields": {
            "_id": "ObjectId - Unique points rule ID",
            "name": "string - Points rule name",
            "name_lower": "string - Lowercase for search",
            "description": "string - Rule description",
            "category": "string - Points category",
            "value": "int - Points value",
            "valid_from": "string - Valid from date (YYYY-MM-DD)",
            "valid_to": "string - Valid to date (YYYY-MM-DD)",
            "status": "string - active/inactive",
            "created_at": "string - Created date",
            "created_time": "string - Created time",
            "created_by": "int - User ID who created",
            "updated_at": "string - Updated date",
            "updated_time": "string - Updated time",
            "updated_by": "int - User ID who updated"
        }
    },
    "product_master": {
        "description": "Product catalog master data",
        "fields": {
            "_id": "ObjectId - Unique product ID",
            "product_name": "string - Product name",
            "product_name_lower": "string - Lowercase for search",
            "description": "string - Product description",
            "category_id": "string - Category reference",
            "category_name": "string - Category name",
            "sub_category_id": "string - Sub-category reference",
            "sub_category_name": "string - Sub-category name",
            "sku": "string - Stock Keeping Unit",
            "mrp": "int - Maximum Retail Price",
            "status": "string - active/inactive",
            "images": "array - Array of product image objects",
            "created_at": "string - Created date",
            "created_time": "string - Created time",
            "created_by": "int - User ID who created",
            "updated_at": "string - Updated date",
            "updated_time": "string - Updated time",
            "updated_by": "int - User ID who updated"
        }
    },
    "recent_activity": {
        "description": "Recent activity feed for workers",
        "fields": {
            "_id": "ObjectId - Unique activity ID",
            "activity_id": "string - Activity identifier",
            "worker_id": "string - Worker ID",
            "activity_type": "string - Type of activity (scan/redemption/etc)",
            "title": "string - Activity title",
            "description": "string - Activity description",
            "points_change": "int - Points added or deducted",
            "reference_type": "string - Type of reference (coupon/redemption)",
            "reference_id": "string - Reference ID",
            "coupon_code": "string - Coupon code if applicable",
            "batch_number": "string - Batch number if applicable",
            "redemption_id": "string - Redemption ID if applicable",
            "created_at": "string - Created timestamp",
            "created_date": "string - Created date (YYYY-MM-DD)",
            "created_time": "string - Created time (HH:MM:SS)",
            "created_by": "string - Created by user"
        }
    },
    "skilled_workers": {
        "description": "Skilled workers master database",
        "fields": {
            "_id": "ObjectId - Unique worker ID",
            "worker_id": "string - Worker identifier",
            "name": "string - Worker name",
            "mobile": "string - Mobile number",
            "worker_type": "string - Type of worker",
            "status": "string - active/inactive/blocked",
            "status_reason": "string - Reason for status",
            "kyc_status": "string - KYC verification status",
            "wallet_points": "int - Current wallet balance",
            "coupons_scanned": "int - Total coupons scanned",
            "redemption_count": "int - Total redemptions made",
            "scheme_enrolled": "string - Enrolled scheme",
            "pincode": "string - Pincode",
            "city": "string - City name",
            "district": "string - District name",
            "state": "string - State name",
            "last_activity": "string - Last activity timestamp",
            "notes": "string - Additional notes",
            "created_date": "string - Created date",
            "created_time": "string - Created time",
            "created_by_id": "int - Created by user ID"
        }
    },
    "sub_category_master": {
        "description": "Product sub-categories master",
        "fields": {
            "_id": "ObjectId - Unique sub-category ID",
            "sub_category_name": "string - Sub-category name",
            "sub_category_name_lower": "string - Lowercase for search",
            "description": "string - Sub-category description",
            "category_id": "string - Parent category reference",
            "category_name": "string - Parent category name",
            "status": "string - active/inactive",
            "created_at": "string - Created date",
            "created_time": "string - Created time",
            "created_by": "int - User ID who created",
            "updated_at": "string - Updated date",
            "updated_time": "string - Updated time",
            "updated_by": "int - User ID who updated"
        }
    },
    "transaction_ledger": {
        "description": "Complete transaction ledger for all points movements",
        "fields": {
            "_id": "ObjectId - Unique transaction ID",
            "transaction_id": "string - Transaction identifier",
            "worker_id": "string - Worker ID",
            "transaction_type": "string - credit/debit",
            "amount": "int - Transaction amount (points)",
            "previous_balance": "int - Balance before transaction",
            "new_balance": "int - Balance after transaction",
            "reference_type": "string - Type of reference (coupon/redemption)",
            "reference_id": "string - Reference ID",
            "redemption_id": "string - Redemption ID if applicable",
            "batch_number": "string - Batch number if applicable",
            "description": "string - Transaction description",
            "status": "string - Transaction status",
            "transaction_date": "string - Transaction date (YYYY-MM-DD)",
            "transaction_time": "string - Transaction time (HH:MM:SS)",
            "transaction_datetime": "datetime - Transaction timestamp",
            "created_at": "string - Created date",
            "created_time": "string - Created time",
            "created_by": "string - Created by user"
        }
    }
}


def get_collection_names():
    """Get list of all collection names"""
    return list(SCHEMA_INFO.keys())


def get_collection_schema(collection_name: str):
    """Get schema for a specific collection"""
    return SCHEMA_INFO.get(collection_name)


def get_collection_fields(collection_name: str):
    """Get fields for a specific collection"""
    schema = SCHEMA_INFO.get(collection_name)
    return schema.get("fields") if schema else None
