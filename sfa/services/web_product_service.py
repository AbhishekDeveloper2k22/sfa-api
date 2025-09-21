from config import settings
import json
from bson import ObjectId
from sfa.database import client1
from datetime import datetime
import os
import uuid
from typing import Union, Optional


class product_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.products = self.client_database["products"]
        self.categories = self.client_database["categories"]
        self.current_datetime = datetime.now()

    def _now_fields(self):
        return {
            "created_at": self.current_datetime.strftime("%Y-%m-%d"),
            "created_at_time": self.current_datetime.strftime("%H:%M:%S"),
        }

    def check_product_exists(self, request_data: dict) -> dict:
        or_conditions = []
        if request_data.get('product_name'):
            or_conditions.append({'product_name': request_data['product_name']})
        if request_data.get('product_code'):
            or_conditions.append({'product_code': request_data['product_code']})

        if not or_conditions:
            return {"exists": False, "message": "No unique fields provided to check"}

        query = {'$or': or_conditions, 'del': 0}
        existing = self.products.find_one(query)
        if existing:
            return {
                "exists": True,
                "existing_product": {
                    "id": str(existing.get('_id')),
                    "product_name": existing.get('product_name'),
                    "product_code": existing.get('product_code')
                }
            }
        return {"exists": False}

    def _attach_category(self, request_data: dict) -> tuple[bool, Optional[dict], Optional[str]]:
        cat_id = request_data.get('category_id') or request_data.get('categoryId')
        cat_name = request_data.get('category_name')

        if cat_id:
            try:
                category = self.categories.find_one({"_id": ObjectId(cat_id), "del": 0})
                if not category:
                    return False, None, "Invalid category_id"
                return True, {
                    "category_id": str(category['_id']),
                    "category_name": category.get('category_name')
                }, None
            except Exception:
                return False, None, "Invalid category_id format"
        elif cat_name:
            category = self.categories.find_one({"category_name": cat_name, "del": 0})
            if not category:
                return False, None, "Invalid category_name"
            return True, {
                "category_id": str(category['_id']),
                "category_name": category.get('category_name')
            }, None
        else:
            return False, None, "category_id or category_name is required"

    def add_product(self, request_data: dict) -> dict:
        # uniqueness
        unique = self.check_product_exists(request_data)
        if unique.get('exists'):
            return {
                "success": False,
                "message": "Product already exists with this name/code",
                "existing_product": unique.get('existing_product')
            }

        # category link
        ok, cat_info, err = self._attach_category(request_data)
        if not ok:
            return {"success": False, "message": err}

        # build document
        doc = {
            "product_name": request_data.get('product_name'),
            "product_code": request_data.get('product_code'),
            "status": request_data.get('status', 'active'),
            "image": request_data.get('image'),
            "dealer_discount": request_data.get('dealer_discount', 0),
            "distributor_discount": request_data.get('distributor_discount', 0),
            "del": 0,
            **cat_info,
            **self._now_fields(),
            "created_by": request_data.get('created_by', 1)
        }

        res = self.products.insert_one(doc)
        if res.inserted_id:
            return {"success": True, "message": "Product added", "inserted_id": str(res.inserted_id)}
        return {"success": False, "message": "Failed to add product"}

    def update_product(self, request_data: dict) -> dict:
        prod_id = request_data.get('_id') or request_data.get('id')
        if not prod_id:
            return {"success": False, "message": "Product ID is required"}

        # if name/code provided, ensure uniqueness against others
        unique = self.check_product_exists(request_data)
        if unique.get('exists') and unique['existing_product']['id'] != prod_id:
            return {
                "success": False,
                "message": "Product already exists with this name/code",
                "existing_product": unique.get('existing_product')
            }

        update_data = {}
        for key in [
            'product_name', 'product_code', 'status', 'image',
            'dealer_discount', 'distributor_discount'
        ]:
            if key in request_data:
                update_data[key] = request_data[key]

        # category link if provided
        if 'category_id' in request_data or 'category_name' in request_data or 'categoryId' in request_data:
            ok, cat_info, err = self._attach_category(request_data)
            if not ok:
                return {"success": False, "message": err}
            update_data.update(cat_info)

        update_data['updated_at'] = self.current_datetime.strftime("%Y-%m-%d")
        update_data['updated_at_time'] = self.current_datetime.strftime("%H:%M:%S")

        res = self.products.update_one({"_id": ObjectId(prod_id)}, {"$set": update_data})
        if res.matched_count > 0:
            return {
                "success": True,
                "message": "Product updated",
                "matched_count": res.matched_count,
                "modified_count": res.modified_count
            }
        return {"success": False, "message": "Product not found"}

    def products_list(self, request_data: dict) -> dict:
        limit = request_data.get('limit', 10)
        page = request_data.get('page', 1)
        skip = (page - 1) * limit

        query = request_data.copy()
        for k in ['limit', 'page']:
            if k in query:
                del query[k]
        if 'del' not in query:
            query['del'] = 0

        total_count = self.products.count_documents(query)
        items = list(self.products.find(query).skip(skip).limit(limit))
        for it in items:
            it['_id'] = str(it['_id'])

        total_pages = (total_count + limit - 1) // limit
        return {
            "data": items,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "limit": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }

    def product_details(self, request_data: dict) -> dict:
        prod_id = request_data.get('_id') or request_data.get('id')
        if not prod_id:
            return {"success": False, "message": "Product ID is required", "data": None}
        try:
            prod = self.products.find_one({"_id": ObjectId(prod_id)})
            if not prod:
                return {"success": False, "message": "Product not found", "data": None}
            prod['_id'] = str(prod['_id'])
            return {"success": True, "message": "Product details", "data": prod}
        except Exception as e:
            return {"success": False, "message": f"Invalid ID: {e}", "data": None}

    def update_product_image(self, product_id: str, upload_file) -> dict:
        if not product_id:
            return {"success": False, "message": "Product ID is required"}
        try:
            # verify product exists
            prod = self.products.find_one({"_id": ObjectId(product_id)})
            if not prod:
                return {"success": False, "message": "Product not found"}
        except Exception as e:
            return {"success": False, "message": f"Invalid product ID: {e}"}

        # prepare directories
        base_dir = os.path.join("uploads", "sfa", "products")
        os.makedirs(base_dir, exist_ok=True)

        # unique filename with original extension
        original = upload_file.filename or "file"
        _, ext = os.path.splitext(original)
        unique_name = f"prod_{uuid.uuid4().hex}{ext.lower()}"
        file_path = os.path.join(base_dir, unique_name)

        # write file to disk
        with open(file_path, 'wb') as f:
            f.write(upload_file.file.read())

        # update product doc
        update = {
            "image": unique_name,
            "image_updated_at": self.current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        }
        res = self.products.update_one({"_id": ObjectId(product_id)}, {"$set": update})
        if res.matched_count > 0:
            return {"success": True, "message": "Product image updated", "file_name": unique_name}
        return {"success": False, "message": "Failed to update image"}


