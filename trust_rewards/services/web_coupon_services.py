from bson import ObjectId
from trust_rewards.database import client1
from datetime import datetime, timedelta
from typing import Optional

class CouponService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.coupon_master = self.client_database["coupon_master"]
        self.coupon_code = self.client_database["coupon_code"]
        self.current_datetime = datetime.now()

    def generate_points_coupons(self, request_data: dict) -> dict:
        """Generate points redemption coupons for skilled workers"""
        try:
            # Extract and validate input data
            points_value = request_data.get('points_value')
            batch_number = request_data.get('batch_number')
            number_of_coupons = request_data.get('number_of_coupons')
            valid_from = request_data.get('valid_from')
            valid_to = request_data.get('valid_to')
            created_by_id = request_data.get('created_by_id', 1)

            # Validate required fields
            if not points_value or not isinstance(points_value, int) or points_value < 1 or points_value > 10000:
                return {
                    "success": False,
                    "message": "Points value must be between 1 and 10000",
                    "error": {"code": "VALIDATION_ERROR", "details": "Invalid points value"}
                }

            if not batch_number or not isinstance(batch_number, str):
                return {
                    "success": False,
                    "message": "Batch number is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Invalid batch number"}
                }

            if not number_of_coupons or not isinstance(number_of_coupons, int) or number_of_coupons < 1 or number_of_coupons > 1000:
                return {
                    "success": False,
                    "message": "Number of coupons must be between 1 and 1000",
                    "error": {"code": "VALIDATION_ERROR", "details": "Invalid number of coupons"}
                }

            if not valid_from or not valid_to:
                return {
                    "success": False,
                    "message": "Valid from and valid to dates are required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing date fields"}
                }

            # Validate date format and logic
            try:
                valid_from_date = datetime.strptime(valid_from, "%Y-%m-%d")
                valid_to_date = datetime.strptime(valid_to, "%Y-%m-%d")
                
                # Check if valid_from is not in the past
                if valid_from_date.date() < self.current_datetime.date():
                    return {
                        "success": False,
                        "message": "Valid from date cannot be in the past",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid valid from date"}
                    }
                
                # Check if valid_to is after valid_from
                if valid_to_date <= valid_from_date:
                    return {
                        "success": False,
                        "message": "Valid to date must be after valid from date",
                        "error": {"code": "VALIDATION_ERROR", "details": "Invalid date range"}
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format. Use yyyy-mm-dd",
                    "error": {"code": "VALIDATION_ERROR", "details": "Invalid date format"}
                }

            # Check if batch number already exists in coupon_master
            existing_batch = self.coupon_master.find_one({"batch_number": batch_number})
            if existing_batch:
                return {
                    "success": False,
                    "message": "Batch number already exists",
                    "error": {"code": "VALIDATION_ERROR", "details": "Duplicate batch number"}
                }

            # Step 1: Create coupon_master record
            master_doc = {
                "batch_number": batch_number,
                "points_value": points_value,
                "number_of_coupons": number_of_coupons,
                "valid_from": valid_from_date.strftime("%Y-%m-%d"),
                "valid_to": valid_to_date.strftime("%Y-%m-%d"),
                "status": "active",
                "created_at": self.current_datetime.strftime("%Y-%m-%d"),
                "created_time": self.current_datetime.strftime("%H:%M:%S"),
                "created_by_id": created_by_id
            }
            
            master_result = self.coupon_master.insert_one(master_doc)
            coupon_master_id = str(master_result.inserted_id)

            # Step 2: Generate individual coupon codes
            generated_coupons = []
            for i in range(number_of_coupons):
                # Generate unique coupon code using MongoDB _id for guaranteed uniqueness
                coupon_doc = {
                    "coupon_master_id": coupon_master_id,
                    "coupon_value": points_value,
                    "valid_from": valid_from_date.strftime("%Y-%m-%d"),
                    "valid_to": valid_to_date.strftime("%Y-%m-%d"),
                    "is_redeemed": False,
                    "redeemed_by": None,
                    "redeemed_at": None,
                    "created_at": self.current_datetime.strftime("%Y-%m-%d"),
                    "created_time": self.current_datetime.strftime("%H:%M:%S"),
                    "created_by_id": created_by_id
                }
                
                # Insert coupon to get unique _id
                coupon_result = self.coupon_code.insert_one(coupon_doc)
                coupon_id = coupon_result.inserted_id
                
                # Use ObjectId as coupon_code for guaranteed uniqueness
                coupon_code = str(coupon_id)
                
                # Update coupon with coupon_code
                self.coupon_code.update_one(
                    {"_id": coupon_id},
                    {
                        "$set": {
                            "coupon_code": coupon_code
                        }
                    }
                )
                
                generated_coupons.append({
                    "coupon_id": str(coupon_id),
                    "coupon_code": coupon_code
                })

            return {
                "success": True,
                "message": f"Successfully generated {number_of_coupons} points redemption coupons",
                "data": {
                    "coupon_master_id": str(coupon_master_id),
                    "batch_number": batch_number,
                    "points_value": points_value,
                    "number_of_coupons": number_of_coupons,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                    "generated_coupons": generated_coupons,
                    "summary": f"This generated {number_of_coupons} points redemption coupons with {points_value} points each for batch {batch_number}. Skilled workers can scan these coupons to add points to their wallet."
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate QR coupons: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_coupons_list(self, request_data: dict) -> dict:
        """Get paginated list of coupons with filters using aggregation"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            batch_number = filters.get('batch_number')
            status = filters.get('status', 'all')
            is_redeemed = filters.get('is_redeemed')

            # Build match conditions
            match_conditions = {}
            if batch_number:
                match_conditions["master.batch_number"] = batch_number
            if status != 'all':
                match_conditions["master.status"] = status
            if is_redeemed is not None:
                match_conditions["is_redeemed"] = is_redeemed

            # Aggregation pipeline to join coupon_code with coupon_master
            pipeline = [
                {
                    "$addFields": {
                        "coupon_master_object_id": {"$toObjectId": "$coupon_master_id"}
                    }
                },
                {
                    "$lookup": {
                        "from": "coupon_master",
                        "localField": "coupon_master_object_id",
                        "foreignField": "_id",
                        "as": "master"
                    }
                },
                {"$unwind": "$master"},
                {"$match": match_conditions},
                {
                    "$project": {
                        "_id": 1,
                        "coupon_master_id": 1,
                        "coupon_code": 1,
                        "coupon_value": 1,
                        "valid_from": 1,
                        "valid_to": 1,
                        "is_redeemed": 1,
                        "redeemed_by": 1,
                        "redeemed_at": 1,
                        "created_at": 1,
                        "created_time": 1,
                        "batch_number": "$master.batch_number",
                        "master_status": "$master.status",
                        "coupon_master_object_id": 0
                    }
                },
                {"$sort": {"created_at": -1, "created_time": -1}}
            ]

            # Get total count
            count_pipeline = pipeline + [{"$count": "total"}]
            count_result = list(self.coupon_code.aggregate(count_pipeline))
            total_count = count_result[0]["total"] if count_result else 0
            
            # Add pagination
            pipeline.extend([
                {"$skip": skip},
                {"$limit": limit}
            ])
            
            # Execute aggregation
            coupons = list(self.coupon_code.aggregate(pipeline))
            
            # Convert ObjectId to string
            for coupon in coupons:
                coupon['_id'] = str(coupon['_id'])

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "coupons": coupons,
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
                "message": f"Failed to get coupons list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_coupon_master_list(self, request_data: dict) -> dict:
        """Get list of coupon master batches"""
        try:
            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'all')

            # Build query
            query = {}
            if status != 'all':
                query['status'] = status

            # Get total count
            total_count = self.coupon_master.count_documents(query)
            
            # Get master records with coupon counts
            pipeline = [
                {"$match": query},
                {
                    "$lookup": {
                        "from": "coupon_code",
                        "localField": "_id",
                        "foreignField": "coupon_master_id",
                        "as": "coupons"
                    }
                },
                {
                    "$addFields": {
                        "total_coupons": {"$size": "$coupons"},
                        "redeemed_coupons": {
                            "$size": {
                                "$filter": {
                                    "input": "$coupons",
                                    "cond": {"$eq": ["$$this.is_redeemed", True]}
                                }
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "coupons": 0  # Remove the coupons array to reduce response size
                    }
                },
                {"$sort": {"created_at": -1, "created_time": -1}},
                {"$skip": skip},
                {"$limit": limit}
            ]
            
            masters = list(self.coupon_master.aggregate(pipeline))
            
            # Convert ObjectId to string
            for master in masters:
                master['_id'] = str(master['_id'])

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "masters": masters,
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
                "message": f"Failed to get coupon master list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
