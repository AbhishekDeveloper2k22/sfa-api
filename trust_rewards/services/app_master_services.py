from bson import ObjectId
from trust_rewards.database import client1
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import uuid

class AppMasterService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.categories = self.client_database["category_master"]
        self.sub_categories = self.client_database["sub_category_master"]
        self.product_master = self.client_database["product_master"]
        self.gift_master = self.client_database["gift_master"]

    def get_categories_list(self, request_data: dict) -> dict:
        """Get list of active categories for app users"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 50)
            skip = (page - 1) * limit

            # Build query for active categories only
            query = {"status": "active"}

            # Get total count
            total_count = self.categories.count_documents(query)

            # Get categories with pagination (sort first, then paginate)
            categories = list(
                self.categories.find(query)
                .sort("_id", -1)
                .skip(skip)
                .limit(limit)
            )

            # Convert ObjectId to string and add additional fields
            for category in categories:
                category['_id'] = str(category['_id'])
                category['created_datetime'] = f"{category.get('created_at', '')} {category.get('created_time', '')}"
                category['updated_datetime'] = f"{category.get('updated_at', '')} {category.get('updated_time', '')}"

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "records": categories,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get categories list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_sub_categories_list(self, request_data: dict) -> dict:
        """Get list of active sub-categories for a specific category"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 50)
            skip = (page - 1) * limit

            # Extract category_id from request
            category_id = request_data.get('category_id')
            if not category_id:
                return {
                    "success": False,
                    "message": "category_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "category_id is mandatory"}
                }

            # Validate category_id format
            try:
                ObjectId(category_id)
            except:
                return {
                    "success": False,
                    "message": "Invalid category_id format",
                    "error": {"code": "VALIDATION_ERROR", "details": "category_id must be a valid ObjectId"}
                }

            # Build query for active sub-categories of specific category
            query = {
                "category_id": category_id,
                "status": "active"
            }

            # Get total count
            total_count = self.sub_categories.count_documents(query)

            # Get sub-categories with pagination (sort first, then paginate)
            sub_categories = list(
                self.sub_categories.find(query)
                .sort("_id", -1)
                .skip(skip)
                .limit(limit)
            )

            # Convert ObjectId to string and add additional fields
            for sub_category in sub_categories:
                sub_category['_id'] = str(sub_category['_id'])
                sub_category['created_datetime'] = f"{sub_category.get('created_at', '')} {sub_category.get('created_time', '')}"
                sub_category['updated_datetime'] = f"{sub_category.get('updated_at', '')} {sub_category.get('updated_time', '')}"

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "records": sub_categories,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get sub-categories list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_products_list(self, request_data: dict) -> dict:
        """Get list of active products for specific category and sub-category"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 50)
            skip = (page - 1) * limit

            # Extract category_id and sub_category_id from request
            category_id = request_data.get('category_id')
            sub_category_id = request_data.get('sub_category_id')

            if not category_id:
                return {
                    "success": False,
                    "message": "category_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "category_id is mandatory"}
                }

            if not sub_category_id:
                return {
                    "success": False,
                    "message": "sub_category_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "sub_category_id is mandatory"}
                }

            # Validate ObjectId formats
            try:
                ObjectId(category_id)
                ObjectId(sub_category_id)
            except:
                return {
                    "success": False,
                    "message": "Invalid category_id or sub_category_id format",
                    "error": {"code": "VALIDATION_ERROR", "details": "category_id and sub_category_id must be valid ObjectIds"}
                }

            # Build query for active products of specific category and sub-category
            query = {
                "category_id": category_id,
                "sub_category_id": sub_category_id,
                "status": "active"
            }

            # Get total count
            total_count = self.product_master.count_documents(query)

            # Get products with pagination (sort first, then paginate)
            products = list(
                self.product_master.find(query)
                .sort("_id", -1)
                .skip(skip)
                .limit(limit)
            )

            # Convert ObjectId to string and add additional fields
            for product in products:
                product['_id'] = str(product['_id'])
                product['created_datetime'] = f"{product.get('created_at', '')} {product.get('created_time', '')}"
                product['updated_datetime'] = f"{product.get('updated_at', '')} {product.get('updated_time', '')}"
                
                # Add thumbnail (first image file_url) and remove images array
                if product.get('images') and len(product['images']) > 0:
                    product['thumbnail'] = product['images'][0].get('file_url', '')
                else:
                    product['thumbnail'] = ''
                
                # Remove images array from response
                if 'images' in product:
                    del product['images']

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "records": products,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get products list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_gift_list(self, request_data: dict) -> dict:
        """Get list of active gifts for app users"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 50)
            skip = (page - 1) * limit

            # Build query for active gifts only
            query = {"status": "active"}

            # Get total count
            total_count = self.gift_master.count_documents(query)

            # Get gifts with pagination (sort first, then paginate)
            gifts = list(
                self.gift_master.find(query)
                .sort("_id", -1)
                .skip(skip)
                .limit(limit)
            )

            # Convert ObjectId to string and add additional fields
            for gift in gifts:
                gift['_id'] = str(gift['_id'])
                gift['created_datetime'] = f"{gift.get('created_at', '')} {gift.get('created_time', '')}"
                gift['updated_datetime'] = f"{gift.get('updated_at', '')} {gift.get('updated_time', '')}"
                
                # Add thumbnail (first image file_url) and remove images array
                if gift.get('images') and len(gift['images']) > 0:
                    gift['thumbnail'] = gift['images'][0].get('file_url', '')
                else:
                    gift['thumbnail'] = ''
                
                # Remove images array from response
                if 'images' in gift:
                    del gift['images']

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "records": gifts,
                    "pagination": {
                        "current_page": page,
                        "total_pages": total_pages,
                        "total_count": total_count,
                        "limit": limit,
                        "has_next": has_next,
                        "has_prev": has_prev
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get gift master list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_product_detail(self, request_data: dict) -> dict:
        """Get details of a specific product for app users"""
        try:
            # Extract product_id from request
            product_id = request_data.get('product_id')
            if not product_id:
                return {
                    "success": False,
                    "message": "product_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "product_id is mandatory"}
                }

            # Validate product_id format
            try:
                ObjectId(product_id)
            except:
                return {
                    "success": False,
                    "message": "Invalid product_id format",
                    "error": {"code": "VALIDATION_ERROR", "details": "product_id must be a valid ObjectId"}
                }

            # Find the product
            product = self.product_master.find_one({"_id": ObjectId(product_id), "status": "active"})
            
            if not product:
                return {
                    "success": False,
                    "message": "Product not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Product with given ID does not exist or is inactive"}
                }

            # Convert ObjectId to string and add additional fields
            product['_id'] = str(product['_id'])
            product['created_datetime'] = f"{product.get('created_at', '')} {product.get('created_time', '')}"
            product['updated_datetime'] = f"{product.get('updated_at', '')} {product.get('updated_time', '')}"
            
            # Simplify images array to only include image_id and file_url
            if product.get('images'):
                simplified_images = []
                for img in product['images']:
                    simplified_images.append({
                        'image_id': img.get('image_id', ''),
                        'file_url': img.get('file_url', '')
                    })
                product['images'] = simplified_images
            else:
                product['images'] = []

            return {
                "success": True,
                "data": product
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get product detail: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_gift_detail(self, request_data: dict) -> dict:
        """Get details of a specific gift for app users"""
        try:
            # Extract gift_id from request
            gift_id = request_data.get('gift_id')
            if not gift_id:
                return {
                    "success": False,
                    "message": "gift_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "gift_id is mandatory"}
                }

            # Validate gift_id format
            try:
                ObjectId(gift_id)
            except:
                return {
                    "success": False,
                    "message": "Invalid gift_id format",
                    "error": {"code": "VALIDATION_ERROR", "details": "gift_id must be a valid ObjectId"}
                }

            # Find the gift
            gift = self.gift_master.find_one({"_id": ObjectId(gift_id), "status": "active"})
            
            if not gift:
                return {
                    "success": False,
                    "message": "Gift not found or inactive",
                    "error": {"code": "NOT_FOUND", "details": "Gift with given ID does not exist or is inactive"}
                }

            # Convert ObjectId to string and add additional fields
            gift['_id'] = str(gift['_id'])
            gift['created_datetime'] = f"{gift.get('created_at', '')} {gift.get('created_time', '')}"
            gift['updated_datetime'] = f"{gift.get('updated_at', '')} {gift.get('updated_time', '')}"
            
            # Simplify images array to only include image_id and file_url
            if gift.get('images'):
                simplified_images = []
                for img in gift['images']:
                    simplified_images.append({
                        'image_id': img.get('image_id', ''),
                        'file_url': img.get('file_url', '')
                    })
                gift['images'] = simplified_images
            else:
                gift['images'] = []

            return {
                "success": True,
                "data": gift
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get gift detail: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
