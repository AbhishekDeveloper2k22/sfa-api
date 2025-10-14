from config import settings
import json
from bson import ObjectId
from sfa.database import client1
from datetime import datetime
import os
import uuid
from typing import Union, Optional
import pytz
from sfa.utils.date_utils import build_audit_fields
from sfa.utils.code_generator import generate_unique_code


class product_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.products = self.client_database["products"]
        self.categories = self.client_database["categories"]
        self.field_squad_database = client1["field_squad"]
        self.users_collection = self.field_squad_database["users"]
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
                "existing_product": unique.get('existing_product'),
                "inserted_id": None,
            }

        # Get user_id from request_data or use default
        user_id = request_data.get('created_by', 1)
        
        # Build audit fields using utility
        created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
        updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
        
        # Set default status if not provided
        if 'status' not in request_data:
            request_data['status'] = 'active'

        # build document
        doc = {
            "product_name": request_data.get('product_name'),
            "category_id": request_data.get('category_id'),
            "status": request_data.get('status'),
            "price": int(request_data.get('price', 0)) if request_data.get('price') else 0,
            "retailer_discount": int(request_data.get('retailer_discount', 0)) if request_data.get('retailer_discount') else 0,
            "distributor_discount": int(request_data.get('distributor_discount', 0)) if request_data.get('distributor_discount') else 0,
            "description": request_data.get('description'),
            "sku_code": request_data.get('sku_code'),
            "del": 0,
            **created_fields,
            **updated_fields
        }

        print(doc)
        res = self.products.insert_one(doc)
        
        if res.inserted_id:
            # Generate unique product code
            product_code = generate_unique_code(
                entity_type="product",
                prefix="PRD",
                date_value=created_fields.get("created_at"),
                sequence_length=3
            )
            
            # Update product with product_code
            self.products.update_one(
                {"_id": res.inserted_id},
                {"$set": {"product_code": product_code}}
            )
            
            return {
                "success": True,
                "message": "Product added successfully",
                "inserted_id": str(res.inserted_id),
                "product_code": product_code,
            }
        else:
            return {
                "success": False,
                "message": "Failed to add product",
                "inserted_id": None,
            }

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
            'product_name', 'product_code', 'status', 'image', 'category_id', 'category_name', 'description', 'sku_code', 'retailer_discount', 'distributor_discount', 'price'
        ]:
            if key in request_data:
                update_data[key] = request_data[key]
        
        # Handle numeric fields with type conversion
        if 'price' in request_data:
            update_data['price'] = int(request_data['price']) if request_data['price'] else 0
        if 'retailer_discount' in request_data:
            update_data['retailer_discount'] = int(request_data['retailer_discount']) if request_data['retailer_discount'] else 0
        if 'distributor_discount' in request_data:
            update_data['distributor_discount'] = int(request_data['distributor_discount']) if request_data['distributor_discount'] else 0

        # Get user_id from request_data or use default
        user_id = request_data.get('updated_by', 1)
        
        # Build audit fields using utility
        updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
        update_data.update(updated_fields)

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
        # Extract pagination parameters
        limit = request_data.get('limit', 10)  # Default limit of 10
        page = request_data.get('page', 1)     # Default page 1
        skip = (page - 1) * limit              # Calculate skip value
        
        # Remove pagination and non-query parameters
        query = request_data.copy()
        if 'limit' in query:
            del query['limit']
        if 'page' in query:
            del query['page']
        if 'created_by' in query:
            del query['created_by']  # Remove audit field from query filter
        
        # Add default filter for non-deleted products
        if 'del' not in query:
            query['del'] = 0
        
        # Get total count of products matching the query
        total_count = self.products.count_documents(query)
        
        # Get paginated results sorted by created_at in descending order (latest first)
        result = list(self.products.find(query).sort("created_at", -1).skip(skip).limit(limit))
        
        # Enrich each product with user names and category name
        for product in result:
            # Convert ObjectId to string for JSON serialization
            if '_id' in product:
                product['_id'] = str(product['_id'])
            
            # Get created_by user name
            created_by_id = product.get('created_by')
            if created_by_id:
                try:
                    created_user = self.users_collection.find_one({"_id": ObjectId(created_by_id)})
                    product['created_by_name'] = created_user.get('name', 'Unknown') if created_user else 'Unknown'
                except Exception:
                    product['created_by_name'] = 'Unknown'
            else:
                product['created_by_name'] = 'Unknown'
            
            # Get updated_by user name
            updated_by_id = product.get('updated_by')
            if updated_by_id:
                try:
                    updated_user = self.users_collection.find_one({"_id": ObjectId(updated_by_id)})
                    product['updated_by_name'] = updated_user.get('name', 'Unknown') if updated_user else 'Unknown'
                except Exception:
                    product['updated_by_name'] = 'Unknown'
            else:
                product['updated_by_name'] = 'Unknown'
            
            # Get category name if category_id exists
            category_id = product.get('category_id')
            if category_id:
                try:
                    category = self.categories.find_one({"_id": ObjectId(category_id)})
                    product['category_name'] = category.get('name', 'Unknown') if category else 'Unknown'
                except Exception:
                    product['category_name'] = 'Unknown'
            else:
                product['category_name'] = product.get('category_name', 'Unknown')
            
            # For list view, only show single image (latest one) instead of full array
            if 'product_images' in product:
                # Keep only the latest image (last in array) for list view
                product_images = product.get('product_images', [])
                if product_images:
                    last_image = product_images[-1]
                    # Handle both old format (dict) and new format (string)
                    if isinstance(last_image, dict):
                        product['image_url'] = last_image.get('image_path')
                    else:
                        product['image_url'] = last_image
                # Remove the full array from list response
                del product['product_images']
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            "data": result,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "limit": limit,
                "has_next": has_next,
                "has_prev": has_prev
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
            
            # Convert ObjectId to string
            prod['_id'] = str(prod['_id'])
            
            # Get created_by user name
            created_by_id = prod.get('created_by')
            if created_by_id:
                try:
                    created_user = self.users_collection.find_one({"_id": ObjectId(created_by_id)})
                    prod['created_by_name'] = created_user.get('name', 'Unknown') if created_user else 'Unknown'
                except Exception:
                    prod['created_by_name'] = 'Unknown'
            else:
                prod['created_by_name'] = 'Unknown'
            
            # Get updated_by user name
            updated_by_id = prod.get('updated_by')
            if updated_by_id:
                try:
                    updated_user = self.users_collection.find_one({"_id": ObjectId(updated_by_id)})
                    prod['updated_by_name'] = updated_user.get('name', 'Unknown') if updated_user else 'Unknown'
                except Exception:
                    prod['updated_by_name'] = 'Unknown'
            else:
                prod['updated_by_name'] = 'Unknown'
            
            # Get category name if category_id exists
            category_id = prod.get('category_id')
            if category_id:
                try:
                    category = self.categories.find_one({"_id": ObjectId(category_id)})
                    prod['category_name'] = category.get('name', 'Unknown') if category else 'Unknown'
                except Exception:
                    prod['category_name'] = 'Unknown'
            else:
                prod['category_name'] = prod.get('category_name', 'Unknown')
            
            # Simplify product_images array - only send image paths
            if 'product_images' in prod:
                # Convert old format to new format if needed
                images = prod.get('product_images', [])
                simplified_images = []
                for img in images:
                    if isinstance(img, dict):
                        # Old format with full object
                        simplified_images.append(img.get('image_path', ''))
                    else:
                        # New format - already just path
                        simplified_images.append(img)
                prod['product_images'] = simplified_images
            
            return {"success": True, "message": "Product details", "data": prod}
        except Exception as e:
            return {"success": False, "message": f"Invalid ID: {e}", "data": None}

    def update_product_image(self, product_id: str, upload_file) -> dict:
        if not product_id:
            return {"success": False, "message": "Product ID is required"}
        
        # Validate product exists
        try:
            prod = self.products.find_one({"_id": ObjectId(product_id)})
            if not prod:
                return {"success": False, "message": "Product not found"}
        except Exception as e:
            return {"success": False, "message": f"Invalid product ID: {e}"}

        # Create upload directory if it doesn't exist
        upload_dir = "uploads/sfa_uploads/talbros/products"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        original_filename = upload_file.filename or "file"
        file_extension = os.path.splitext(original_filename)[1].lower()
        unique_filename = f"prod_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Save image file
        try:
            # Reset file pointer to beginning
            upload_file.file.seek(0)
            
            with open(file_path, 'wb') as buffer:
                content = upload_file.file.read()
                buffer.write(content)
        except Exception as e:
            return {
                "success": False,
                "message": "Failed to save image file",
                "error": {"code": "FILE_SAVE_ERROR", "details": f"Could not save image: {str(e)}"}
            }

        # Get current timestamp
        now_iso = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
        
        # Normalize path for API response (use forward slashes)
        normalized_path = file_path.replace("\\", "/")
        
        # Store only image_path in array (simplified structure)
        new_image = normalized_path
        
        # Get existing images array or initialize empty array
        existing_images = prod.get("product_images", [])
        
        # Add new image to the array
        existing_images.append(new_image)
        
        # Update product with multiple images
        update_data = {
            "product_images": existing_images,  # Array of all images
            "image": unique_filename,  # Keep for backward compatibility (latest image)
            "image_updated_at": now_iso
        }
        
        res = self.products.update_one(
            {"_id": ObjectId(product_id)}, 
            {"$set": update_data}
        )
        
        if res.matched_count > 0:
            return {
                "success": True,
                "message": "Product image added successfully",
                "data": {
                    "product_id": product_id,
                    "image_path": normalized_path,
                    "image_filename": unique_filename,
                    "original_filename": original_filename,
                    "uploaded_at": now_iso,
                    "total_images": len(existing_images)
                }
            }
        
        return {"success": False, "message": "Failed to update image"}


