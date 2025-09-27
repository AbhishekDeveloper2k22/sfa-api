from bson import ObjectId
from trust_rewards.database import client1
from datetime import datetime, timedelta
from typing import Optional

class CouponService:
    def __init__(self):
        self.client_database = client1['trust_rewards']
        self.coupon_master = self.client_database["coupon_master"]
        self.coupon_code = self.client_database["coupon_code"]
        self.skilled_workers = self.client_database["skilled_workers"]
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

            # Step 1: Get next coupon_id (auto-increment)
            next_coupon_id = self._get_next_coupon_id()
            
            # Step 2: Create coupon_master record
            master_doc = {
                "coupon_id": next_coupon_id,
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
                    "status": "active",
                    "is_scanned": False,
                    "scanned_by": None,
                    "scanned_at": None,
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

            return {
                "success": True,
                "message": f"Successfully generated {number_of_coupons} points redemption coupons",
                "data": {
                    "coupon_id": next_coupon_id,
                    "coupon_master_id": str(coupon_master_id),
                    "batch_number": batch_number,
                    "points_value": points_value,
                    "number_of_coupons": number_of_coupons,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
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
        """Get paginated list of individual coupons for a specific batch"""
        try:
            # Extract mandatory coupon_master_id
            coupon_master_id = request_data.get('coupon_master_id')
            if not coupon_master_id:
                return {
                    "success": False,
                    "message": "coupon_master_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing coupon_master_id"}
                }

            # Extract pagination parameters
            page = request_data.get('page', 1)
            limit = request_data.get('limit', 10)
            skip = (page - 1) * limit

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'all')
            is_scanned = filters.get('is_scanned')
            scanned_by_name = filters.get('scanned_by_name')  # Optional filter by worker name

            # Build match conditions with mandatory coupon_master_id
            match_conditions = {"coupon_master_id": coupon_master_id}
            if status != 'all':
                match_conditions["status"] = status
            if is_scanned is not None:
                match_conditions["is_scanned"] = is_scanned

            # If filter by scanned_by_name is provided, resolve matching worker IDs and filter by scanned_by
            if scanned_by_name:
                try:
                    # Find skilled workers whose name matches (case-insensitive)
                    matching_workers = list(
                        self.client_database["skilled_workers"].find(
                            {"name": {"$regex": scanned_by_name, "$options": "i"}},
                            {"_id": 1}
                        )
                    )
                    matching_worker_ids = [str(w["_id"]) for w in matching_workers]
                    # If no matches, ensure result is empty by adding impossible condition
                    if not matching_worker_ids:
                        return {
                            "success": True,
                            "data": {
                                "batch_info": None,
                                "coupons": [],
                                "pagination": {
                                    "current_page": page,
                                    "total_pages": 0,
                                    "total_count": 0,
                                    "limit": limit,
                                    "has_next": False,
                                    "has_prev": False
                                }
                            }
                        }
                    match_conditions["scanned_by"] = {"$in": matching_worker_ids}
                except Exception:
                    # If lookup fails, fall back to no results
                    return {
                        "success": True,
                        "data": {
                            "batch_info": None,
                            "coupons": [],
                            "pagination": {
                                "current_page": page,
                                "total_pages": 0,
                                "total_count": 0,
                                "limit": limit,
                                "has_next": False,
                                "has_prev": False
                            }
                        }
                    }

            # Get total count
            total_count = self.coupon_code.count_documents(match_conditions)
            
            # Get coupons with pagination (sort first, then paginate)
            coupons = list(self.coupon_code.find(match_conditions).sort("_id", -1).skip(skip).limit(limit))
            
            # Convert ObjectId to string
            for coupon in coupons:
                coupon['_id'] = str(coupon['_id'])

            # Enrich coupons with scanned_by_name by joining to skilled_workers using scanned_by (stored as string id)
            scanned_ids = list({c.get("scanned_by") for c in coupons if c.get("scanned_by")})
            if scanned_ids:
                # Validate and convert to ObjectId list
                valid_obj_ids = [ObjectId(sid) for sid in scanned_ids if ObjectId.is_valid(sid)]
                if valid_obj_ids:
                    workers = list(self.client_database["skilled_workers"].find({"_id": {"$in": valid_obj_ids}}, {"name": 1}))
                    id_to_name = {str(w["_id"]): w.get("name", "") for w in workers}
                else:
                    id_to_name = {}
                for c in coupons:
                    sid = c.get("scanned_by")
                    c["scanned_by_name"] = id_to_name.get(sid) if sid else None
            else:
                for c in coupons:
                    c["scanned_by_name"] = None

            # Get batch information for the coupon_master_id
            batch_info = self.coupon_master.find_one({"_id": ObjectId(coupon_master_id)})
            
            # Calculate usage statistics
            total_coupons = self.coupon_code.count_documents({"coupon_master_id": coupon_master_id})
            used_coupons = self.coupon_code.count_documents({"coupon_master_id": coupon_master_id, "is_scanned": True})
            available_coupons = total_coupons - used_coupons
            usage_rate = round((used_coupons / total_coupons * 100), 1) if total_coupons > 0 else 0
            
            # Calculate days left for validity
            from datetime import datetime
            days_left = 0
            if batch_info and batch_info.get('valid_to'):
                valid_to_date = datetime.strptime(batch_info['valid_to'], '%Y-%m-%d')
                days_left = (valid_to_date - datetime.now()).days

            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "success": True,
                "data": {
                    "batch_info": {
                        "batch_number": batch_info.get('batch_number', 'N/A') if batch_info else 'N/A',
                        "total_coupons": total_coupons,
                        "points_each": batch_info.get('points_value', 0) if batch_info else 0,
                        "used": used_coupons,
                        "available": available_coupons,
                        "usage_rate": f"{usage_rate}%",
                        "valid_from": batch_info.get('valid_from', 'N/A') if batch_info else 'N/A',
                        "valid_to": batch_info.get('valid_to', 'N/A') if batch_info else 'N/A',
                        "days_left": days_left
                    },
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

    def get_coupon_code_list_csv(self, request_data: dict) -> dict:
        """Get coupon codes as CSV for a specific batch"""
        try:
            # Extract mandatory coupon_master_id
            coupon_master_id = request_data.get('coupon_master_id')
            if not coupon_master_id:
                return {
                    "success": False,
                    "message": "coupon_master_id is required",
                    "error": {"code": "VALIDATION_ERROR", "details": "Missing coupon_master_id"}
                }

            # Extract filters
            filters = request_data.get('filters', {})
            status = filters.get('status', 'active')
            is_scanned = filters.get('is_scanned', False)  # Default to unused coupons only

            # Build query with mandatory coupon_master_id - only unused coupons by default
            query = {
                "coupon_master_id": coupon_master_id,
                "is_scanned": False,  # Only unused coupons
                "status": "active"     # Only active coupons
            }

            # Get all coupon codes for the batch (sort first)
            coupons = list(self.coupon_code.find(query, {"coupon_code": 1, "_id": 0}).sort("_id", -1))
            
            # Extract only coupon codes
            coupon_codes = [coupon['coupon_code'] for coupon in coupons]
            
            # Get batch info for filename
            batch_info = self.coupon_master.find_one({"_id": ObjectId(coupon_master_id)})
            batch_number = batch_info.get('batch_number', 'unknown') if batch_info else 'unknown'
            
            # Generate filename
            filename = f"coupon_codes_{batch_number}_{self.current_datetime.strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Create uploads directory if it doesn't exist
            import os
            upload_dir = "uploads/trust_rewards/coupons"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Full file path
            file_path = os.path.join(upload_dir, filename)
            
            # Create CSV content and save to file
            csv_content = "Coupon Code\n" + "\n".join(coupon_codes)
            
            # Write CSV file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            # Convert file path to use forward slashes for response
            response_file_path = file_path.replace('\\', '/')
            
            # Create full URL for file access
            # base_url = "http://127.0.0.1:8000"  # You can make this configurable
            base_url = "http://getpe.shop"
            full_url = f"{base_url}/{response_file_path}"
            
            return {
                "success": True,
                "message": f"Successfully generated CSV with {len(coupon_codes)} coupon codes",
                "data": {
                    "filename": filename,
                    "file_path": response_file_path,
                    "full_url": full_url,
                    "total_codes": len(coupon_codes),
                    "batch_number": batch_number,
                    "coupon_master_id": coupon_master_id
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate CSV: {str(e)}",
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
            if status == 'expired':
                # Filter for expired batches (valid_to date is in the past)
                current_date = self.current_datetime.strftime("%Y-%m-%d")
                query['valid_to'] = {"$lt": current_date}
            elif status != 'all':
                query['status'] = status

            # Get total count
            total_count = self.coupon_master.count_documents(query)
            
            # Get master records with coupon counts
            pipeline = [
                {"$match": query},
                {
                    "$addFields": {
                        "coupon_master_id_str": {"$toString": "$_id"}
                    }
                },
                {
                    "$lookup": {
                        "from": "coupon_code",
                        "localField": "coupon_master_id_str",
                        "foreignField": "coupon_master_id",
                        "as": "coupons"
                    }
                },
                {
                    "$addFields": {
                        "total_coupons": {"$size": "$coupons"},
                        "scanned_coupons": {
                            "$size": {
                                "$filter": {
                                    "input": "$coupons",
                                    "cond": {"$eq": ["$$this.is_scanned", True]}
                                }
                            }
                        },
                        "usage": {
                            "$concat": [
                                {"$toString": {
                                    "$size": {
                                        "$filter": {
                                            "input": "$coupons",
                                            "cond": {"$eq": ["$$this.is_scanned", True]}
                                        }
                                    }
                                }},
                                "/",
                                {"$toString": {"$size": "$coupons"}}
                            ]
                        }
                    }
                },
                {
                    "$project": {
                        "coupons": 0,  # Remove the coupons array to reduce response size
                        "coupon_master_id_str": 0  # Remove the temporary field
                    }
                },
                {"$sort": {"_id": -1}},
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

            # Get stats data
            stats = self.get_coupon_stats()

            return {
                "success": True,
                "data": {
                    "masters": masters,
                    "stats": stats,
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

    def get_coupon_stats(self) -> dict:
        """Get coupon statistics for dashboard"""
        try:
            # Total QR Coupons (Total coupon codes)
            total_coupons = self.coupon_code.count_documents({})
            
            # Active Coupons (Not scanned)
            active_coupons = self.coupon_code.count_documents({"is_scanned": False})
            
            # Used Coupons (Scanned)
            used_coupons = self.coupon_code.count_documents({"is_scanned": True})
            
            # Expired Coupons (valid_to date is in the past)
            current_date = self.current_datetime.strftime("%Y-%m-%d")
            expired_coupons = self.coupon_code.count_documents({"valid_to": {"$lt": current_date}})
            
            # Total Points (Sum of all coupon values)
            pipeline = [
                {"$group": {"_id": None, "total_points": {"$sum": "$coupon_value"}}}
            ]
            points_result = list(self.coupon_code.aggregate(pipeline))
            total_points = points_result[0]["total_points"] if points_result else 0
            
            return {
                "total_qr_coupons": total_coupons,
                "active_coupons": active_coupons,
                "used_coupons": used_coupons,
                "expired_coupons": expired_coupons,
                "total_points": total_points
            }
            
        except Exception as e:
            return {
                "total_qr_coupons": 0,
                "active_coupons": 0,
                "used_coupons": 0,
                "expired_coupons": 0,
                "total_points": 0
            }

    def _get_next_coupon_id(self) -> str:
        """Get next auto-incrementing coupon_id like COU-1, COU-2, etc."""
        try:
            # Find the highest coupon_id
            pipeline = [
                {
                    "$project": {
                        "coupon_id": 1,
                        "numeric_part": {
                            "$toInt": {
                                "$substr": [
                                    "$coupon_id",
                                    4,  # Skip "COU-"
                                    -1
                                ]
                            }
                        }
                    }
                },
                {"$sort": {"numeric_part": -1}},
                {"$limit": 1}
            ]
            
            result = list(self.coupon_master.aggregate(pipeline))
            
            if result and result[0].get('coupon_id'):
                # Extract numeric part and increment
                last_coupon_id = result[0]['coupon_id']
                numeric_part = int(last_coupon_id.split('-')[1])
                next_number = numeric_part + 1
            else:
                # First coupon
                next_number = 1
            
            return f"COU-{next_number}"
            
        except Exception as e:
            # Fallback: use timestamp-based ID
            timestamp = int(self.current_datetime.timestamp())
            return f"COU-{timestamp}"

    def get_analytics_overview(self) -> dict:
        """Get analytics overview for common header stats."""
        try:
            # Total coupons
            total_coupons = self.coupon_code.count_documents({})

            # Active coupons (not scanned)
            active_coupons = self.coupon_code.count_documents({"is_scanned": False})

            # Used coupons (scanned)
            used_coupons = self.coupon_code.count_documents({"is_scanned": True})

            # Total points from used coupons (sum of coupon_value where is_scanned = True)
            points_pipeline = [
                {"$match": {"is_scanned": True}},
                {"$group": {"_id": None, "total_points": {"$sum": "$coupon_value"}}}
            ]
            points_result = list(self.coupon_code.aggregate(points_pipeline))
            total_points = points_result[0]["total_points"] if points_result else 0

            # Total workers (only Active) from skilled_workers collection
            total_workers = self.skilled_workers.count_documents({"status": "Active"})

            return {
                "success": True,
                "message": "Analytics overview retrieved successfully",
                "data": {
                    "total_coupons": total_coupons,
                    "active_coupons": active_coupons,
                    "used_coupons": used_coupons,
                    "total_points": total_points,
                    "total_workers": total_workers
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get analytics overview: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_statewise_analytics(self, metric: str = "used_coupons") -> dict:
        """Get statewise analytics for selected metric: used_coupons | total_points | workers."""
        try:
            # Aggregate used coupons and total points by state using coupon_code joined to skilled_workers
            coupon_pipeline = [
                {"$match": {"is_scanned": True, "scanned_by": {"$ne": None}}},
                {"$addFields": {"scanned_by_obj": {"$toObjectId": "$scanned_by"}}},
                {
                    "$lookup": {
                        "from": "skilled_workers",
                        "localField": "scanned_by_obj",
                        "foreignField": "_id",
                        "as": "worker"
                    }
                },
                {"$unwind": "$worker"},
                {
                    "$group": {
                        "_id": "$worker.state",
                        "used_coupons": {"$sum": 1},
                        "total_points": {"$sum": "$coupon_value"}
                    }
                }
            ]
            coupon_stats = list(self.coupon_code.aggregate(coupon_pipeline))

            # Aggregate active workers by state
            workers_pipeline = [
                {"$match": {"status": "Active"}},
                {"$group": {"_id": "$state", "workers": {"$sum": 1}}}
            ]
            worker_stats = list(self.skilled_workers.aggregate(workers_pipeline))

            # Build maps for quick merge
            coupons_by_state = { (doc.get("_id") or "Unknown"): {
                "used_coupons": doc.get("used_coupons", 0),
                "total_points": doc.get("total_points", 0)
            } for doc in coupon_stats }

            workers_by_state = { (doc.get("_id") or "Unknown"): doc.get("workers", 0) for doc in worker_stats }

            # Union of states from both datasets
            all_states = set(coupons_by_state.keys()) | set(workers_by_state.keys())

            states_output = []
            totals_used = 0
            totals_points = 0
            totals_workers = 0

            for state in sorted(all_states, key=lambda s: (s is None, s)):
                state_key = state if state not in (None, "",) else "Unknown"
                used = coupons_by_state.get(state_key, {}).get("used_coupons", 0)
                points = coupons_by_state.get(state_key, {}).get("total_points", 0)
                workers = workers_by_state.get(state_key, 0)

                totals_used += used
                totals_points += points
                totals_workers += workers

                states_output.append({
                    "state": state_key or "Unknown",
                    "used_coupons": used,
                    "total_points": points,
                    "workers": workers
                })

            # Prepare response based on selected metric
            metric_map = {
                "used_coupons": ("used_coupons", totals_used),
                "total_points": ("total_points", totals_points),
                "workers": ("workers", totals_workers)
            }
            if metric not in metric_map:
                metric = "used_coupons"

            key_name, total_value = metric_map[metric]
            states_metric_only = [{"state": s["state"], "value": s[key_name]} for s in states_output]

            return {
                "success": True,
                "message": "Statewise analytics retrieved successfully",
                "data": {
                    "metric": metric,
                    "states": states_metric_only
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get statewise analytics: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_statewise_totals(self, metric: str = "used_coupons") -> dict:
        """Get overall totals.
        If metric == 'all', returns all three: used_coupons, total_points, workers.
        Otherwise returns a single metric total.
        """
        try:
            # Compute all totals
            used_total = self.coupon_code.count_documents({"is_scanned": True})

            points_pipeline = [
                {"$match": {"is_scanned": True}},
                {"$group": {"_id": None, "total_points": {"$sum": "$coupon_value"}}}
            ]
            points_result = list(self.coupon_code.aggregate(points_pipeline))
            points_total = points_result[0]["total_points"] if points_result else 0

            workers_total = self.skilled_workers.count_documents({"status": "Active"})

            metric_map = {
                "used_coupons": used_total,
                "total_points": points_total,
                "workers": workers_total
            }
            if metric == "all":
                return {
                    "success": True,
                    "message": "Totals retrieved successfully",
                    "data": {
                        "used_coupons": used_total,
                        "total_points": points_total,
                        "workers": workers_total
                    }
                }
            if metric not in metric_map:
                metric = "used_coupons"

            return {
                "success": True,
                "message": "Totals retrieved successfully",
                "data": {
                    "metric": metric,
                    "total": metric_map[metric]
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get totals: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
