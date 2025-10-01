from sfa.database import client1
from bson import ObjectId
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

class AppMasterService:
    def __init__(self):
        self.tenant_id_db = client1["talbros"]
        self.categories_collection = self.tenant_id_db['categories']
        self.products_collection = self.tenant_id_db['products']

    def get_categories(self, status: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        try:
            query = {"del": {"$ne": 1}}
            if status:
                query["status"] = status

            categories = list(self.categories_collection.find(query).sort("name", 1).limit(limit))
            for c in categories:
                c["_id"] = str(c["_id"]) 
            return {"success": True, "data": {"categories": categories, "total": len(categories)}}
        except Exception as e:
            print(traceback.format_exc())
            return {
                "success": False,
                "message": f"Failed to get categories: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e), "trace": traceback.format_exc()}
            }

    def get_products(self, category_id: Optional[str] = None, status: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        try:
            query: Dict[str, Any] = {"del": {"$ne": 1}}
            if status:
                query["status"] = status
            if category_id:
                # support both direct id and nested field like category_id
                try:
                    query["category_id"] = str(category_id)
                except Exception:
                    query["category_id"] = category_id

            products = list(self.products_collection.find(query).sort("name", 1).limit(limit))
            for p in products:
                p["_id"] = str(p["_id"]) 
            return {"success": True, "data": {"products": products, "total": len(products)}}
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get products: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e), "trace": traceback.format_exc()}
            }
