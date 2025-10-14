import os
from datetime import datetime, timedelta
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz
from typing import List, Dict, Any, Optional
from sfa.utils.date_utils import build_audit_fields
from sfa.utils.geo_utils import calculate_distance, format_distance, optimize_route, calculate_route_stats

load_dotenv()

class AppBeatPlanService:
    def __init__(self):
        self.talbros_db = client1['talbros']
        self.field_squad_db = client1['field_squad']
        self.beat_plans_collection = self.talbros_db['beat_plan']
        self.customers_collection = self.talbros_db['customers']
        self.users_collection = self.field_squad_db['users']
        self.customer_checkins_collection = self.talbros_db['customer_checkins']
        self.timezone = pytz.timezone('Asia/Kolkata')

    def get_areas(self, user_id: str) -> Dict[str, Any]:
        """Get available areas (cities) from assigned customers for beat plan creation"""
        try:
            # Get user info from field_squad.users
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get unique cities from assigned customers
            pipeline = [
                {
                    "$match": {
                        "assign_user_id": user_id,
                        "status": "active",
                        "del": {"$ne": 1},
                        "city": {"$ne": "", "$exists": True}
                    }
                },
                {
                    "$group": {
                        "_id": "$city",
                        "city_name": {"$first": "$city"},
                        "customer_count": {"$sum": 1}
                    }
                },
                {
                    "$sort": {"city_name": 1}
                }
            ]
            
            cities = list(self.customers_collection.aggregate(pipeline))
            
            # Format areas data
            areas = []
            for city in cities:
                areas.append({
                    "_id": city["_id"],
                    "name": city["city_name"],
                    "description": f"{city['customer_count']} customers",
                    "customer_count": city["customer_count"]
                })

            return {
                "success": True,
                "data": {
                    "areas": areas
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get areas: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_customers_by_area(self, area_id: str, user_id: str, user_lat: float = None, user_lng: float = None) -> Dict[str, Any]:
        """Get customers assigned to the user in a specific city for beat plan creation"""
        try:
            # Get user location if not provided
            if user_lat is None or user_lng is None:
                user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
                if user:
                    user_lat = user.get('latitude')
                    user_lng = user.get('longitude')
            
            # Convert coordinates to float if they are strings
            if user_lat is not None:
                try:
                    user_lat = float(user_lat)
                except (ValueError, TypeError):
                    user_lat = None
            
            if user_lng is not None:
                try:
                    user_lng = float(user_lng)
                except (ValueError, TypeError):
                    user_lng = None
            
            # Get customers assigned to the user in the specific city
            customers = list(self.customers_collection.find({
                "assign_user_id": user_id,
                "city": area_id,  # area_id is actually city name
                "status": "active",
                "del": {"$ne": 1}
            }).sort("name", 1))

            # Convert ObjectId to string and format customer data
            for customer in customers:
                customer['_id'] = str(customer['_id'])
                # Format customer data for beat plan
                customer['customer_id'] = str(customer['_id'])
                customer['name'] = customer.get('name', '')
                customer['company_name'] = customer.get('company_name', '')
                customer['address'] = customer.get('billing_address', '')
                customer['phone'] = customer.get('mobile') or customer.get('phone', '')
                customer['email'] = customer.get('email', '')
                customer['city'] = customer.get('city', '')
                customer['state'] = customer.get('state', '')
                customer['pincode'] = customer.get('pincode', '')
                
                # Calculate real distance from user to customer
                customer_lat = customer.get('latitude')
                customer_lng = customer.get('longitude')
                
                # Convert customer coordinates to float
                if customer_lat is not None:
                    try:
                        customer_lat = float(customer_lat)
                    except (ValueError, TypeError):
                        customer_lat = None
                
                if customer_lng is not None:
                    try:
                        customer_lng = float(customer_lng)
                    except (ValueError, TypeError):
                        customer_lng = None
                
                if (user_lat and user_lng and customer_lat and customer_lng):
                    distance_meters = calculate_distance(user_lat, user_lng, customer_lat, customer_lng)
                    distance_km = distance_meters / 1000
                    customer['distance'] = format_distance(distance_meters)
                    customer['distance_km'] = round(distance_km, 1)
                else:
                    customer['distance'] = format_distance(0.0)
                    customer['distance_km'] = 0.0

            # Optimize route if user coordinates are available
            optimized_customers = customers
            route_stats = None
            
            if user_lat and user_lng:
                optimized_customers = optimize_route(customers, user_lat, user_lng)
                route_stats = calculate_route_stats(optimized_customers, user_lat, user_lng)
                
                # Add route order to customers
                for i, customer in enumerate(optimized_customers):
                    customer['route_order'] = i + 1

            return {
                "success": True,
                "data": {
                    "area": {
                        "id": area_id,
                        "name": area_id,  # city name
                        "description": f"Customers in {area_id}"
                    },
                    "customers": optimized_customers,
                    "total_customers": len(customers),
                    "route_optimization": {
                        "optimized": user_lat is not None and user_lng is not None,
                        "stats": route_stats
                    }
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get customers: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def create_beat_plan(self, user_id: str, area_id: str, customer_ids: List[str], 
                        plan_date: str = None, plan_name: str = None, notes: str = None) -> Dict[str, Any]:
        """Create a new beat plan"""
        try:
            # Validate customers exist and are assigned to the user
            customers = list(self.customers_collection.find({
                "_id": {"$in": [ObjectId(cid) for cid in customer_ids]},
                "assign_user_id": user_id,
                "status": "active",
                "del": {"$ne": 1}
            }))

            if len(customers) != len(customer_ids):
                return {
                    "success": False,
                    "message": "Some customers not found or not assigned to you",
                    "error": {"code": "INVALID_CUSTOMERS", "details": "Invalid customer selection"}
                }

            # Get date and day information
            now = datetime.now(self.timezone)
            
            # Use provided plan_date or current date
            if plan_date:
                try:
                    # Validate the provided date format
                    parsed_date = datetime.strptime(plan_date, '%Y-%m-%d')
                    current_date = plan_date
                    current_day = parsed_date.strftime('%A')
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid date format. Use YYYY-MM-DD format",
                        "error": {"code": "INVALID_DATE_FORMAT", "details": "Date must be in YYYY-MM-DD format"}
                    }
            else:
                current_date = now.strftime('%Y-%m-%d')
                current_day = now.strftime('%A')
            
            # Generate plan name if not provided
            if not plan_name:
                plan_name = f"Beat Plan - {current_day} ({current_date})"

            # Create beat plan document
            created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            
            beat_plan = {
                "user_id": user_id,
                "area_id": area_id,
                "area_name": area_id,  # city name
                "plan_name": plan_name,
                "customer_ids": customer_ids,
                "notes": notes or "",
                "status": "active",  # active, completed, cancelled
                "plan_date": current_date,
                "plan_day": current_day,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "total_customers": len(customers),
                "is_active": True,
                **created_fields,
                **updated_fields
            }

            # Insert beat plan
            result = self.beat_plans_collection.insert_one(beat_plan)

            if result.inserted_id:
                return {
                    "success": True,
                    "message": "Beat plan created successfully",
                    "data": {
                        "beat_plan_id": str(result.inserted_id),
                        "plan_name": plan_name,
                        "area_name": area_id,
                        "total_customers": len(customers),
                        "status": "active",
                        "created_at": now.isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to create beat plan",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not save beat plan"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Beat plan creation failed: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def start_checkin(self, user_id: str, customer_id: str, latitude: float, longitude: float,
                      plan_date: str = None, beat_plan_id: str = None, radius_m: int = 100) -> Dict[str, Any]:
        """Start a customer check-in if within allowed radius (default 100 meters)."""
        try:
            # Validate customer
            try:
                customer = self.customers_collection.find_one({"_id": ObjectId(customer_id), "del": {"$ne": 1}})
            except Exception:
                customer = None
            if not customer:
                return {
                    "success": False,
                    "message": "Customer not found",
                    "error": {"code": "CUSTOMER_NOT_FOUND", "details": "Invalid customer_id"}
                }

            # Validate customer coordinates; if missing, set on first-time check-in
            cust_lat = customer.get('latitude')
            cust_lng = customer.get('longitude')
            first_time_location_saved = False
            try:
                cust_lat = float(cust_lat) if cust_lat not in (None, "") else None
                cust_lng = float(cust_lng) if cust_lng not in (None, "") else None
            except Exception:
                cust_lat, cust_lng = None, None

            # Coerce user coordinates
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)
            except Exception:
                return {
                    "success": False,
                    "message": "Invalid user coordinates",
                    "error": {"code": "VALIDATION_ERROR", "details": "latitude/longitude must be numbers"}
                }

            # Distance check (or first-time save)
            if cust_lat is None or cust_lng is None:
                # First time check-in: persist this location to customer
                self.customers_collection.update_one(
                    {"_id": ObjectId(customer_id)},
                    {"$set": {
                        "latitude": str(user_lat),
                        "longitude": str(user_lng),
                        "updated_at": datetime.now(self.timezone).isoformat()
                    }}
                )
                cust_lat, cust_lng = user_lat, user_lng
                distance_m = 0.0
                first_time_location_saved = True
            else:
                distance_m = calculate_distance(user_lat, user_lng, cust_lat, cust_lng)
                if distance_m > radius_m:
                    return {
                        "success": False,
                        "message": "You are too far from the customer location",
                        "error": {
                            "code": "OUT_OF_RADIUS",
                            "details": f"Required within {radius_m} m, current distance {format_distance(distance_m)}"
                        }
                    }

            # Plan date (default today)
            now = datetime.now(self.timezone)
            if plan_date:
                try:
                    datetime.strptime(plan_date, '%Y-%m-%d')
                    plan_date_str = plan_date
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid plan_date format. Use YYYY-MM-DD",
                        "error": {"code": "INVALID_DATE_FORMAT", "details": "plan_date must be YYYY-MM-DD"}
                    }
            else:
                plan_date_str = now.strftime('%Y-%m-%d')

            # Prevent any other active check-in for the user on the same day
            existing_any = self.customer_checkins_collection.find_one({
                "user_id": user_id,
                "plan_date": plan_date_str,
                "status": "in",
                "del": {"$ne": 1}
            })
            if existing_any:
                # If it's same customer, treat as duplicate for same customer; else block due to active elsewhere
                if existing_any.get("customer_id") == customer_id:
                    return {
                        "success": False,
                        "message": "Already checked in for this customer today",
                        "error": {"code": "ALREADY_CHECKED_IN", "details": str(existing_any.get('_id'))}
                    }
                else:
                    return {
                        "success": False,
                        "message": "You already have an active check-in. Please end it before starting a new one.",
                        "error": {
                            "code": "ACTIVE_CHECKIN_EXISTS",
                            "details": {
                                "active_checkin_id": str(existing_any.get('_id')),
                                "customer_id": existing_any.get('customer_id')
                            }
                        }
                    }

            # Build record with audit fields
            created_fields = build_audit_fields(prefix="created", by=user_id, timezone="Asia/Kolkata")
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")

            checkin = {
                "user_id": user_id,
                "customer_id": customer_id,
                "plan_date": plan_date_str,
                "status": "in",
                "checkin_time": now.isoformat(),
                "user_latitude": str(user_lat),
                "user_longitude": str(user_lng),
                "customer_latitude": str(cust_lat),
                "customer_longitude": str(cust_lng),
                "distance_m": round(distance_m, 2),
                "radius_m": radius_m,
                "beat_plan_id": beat_plan_id,
                "first_time_location_saved": first_time_location_saved,
                **created_fields,
                **updated_fields
            }

            ins = self.customer_checkins_collection.insert_one(checkin)
            return {
                "success": True,
                "message": "Check-in started successfully",
                "data": {
                    "checkin_id": str(ins.inserted_id),
                    "distance": format_distance(distance_m),
                    "within_radius": True,
                    "first_time_location_saved": first_time_location_saved
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Start check-in failed: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def end_checkin(self, user_id: str, customer_id: str, plan_date: str = None, 
                    notes: str = None, rating: int = None) -> Dict[str, Any]:
        """End a customer check-in and mark it as completed."""
        try:
            # Plan date (default today)
            now = datetime.now(self.timezone)
            if plan_date:
                try:
                    datetime.strptime(plan_date, '%Y-%m-%d')
                    plan_date_str = plan_date
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid plan_date format. Use YYYY-MM-DD",
                        "error": {"code": "INVALID_DATE_FORMAT", "details": "plan_date must be YYYY-MM-DD"}
                    }
            else:
                plan_date_str = now.strftime('%Y-%m-%d')

            # Find active check-in for this customer
            active_checkin = self.customer_checkins_collection.find_one({
                "user_id": user_id,
                "customer_id": customer_id,
                "plan_date": plan_date_str,
                "status": "in",
                "del": {"$ne": 1}
            })

            if not active_checkin:
                return {
                    "success": False,
                    "message": "No active check-in found for this customer",
                    "error": {"code": "NO_ACTIVE_CHECKIN", "details": "Customer must be checked in first"}
                }

            # Build update fields with audit
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            checkout_fields = build_audit_fields(prefix="checkout", by=user_id, timezone="Asia/Kolkata")
            
            update_data = {
                "status": "out",
                "checkout_time": now.isoformat(),
                **updated_fields,
                **checkout_fields
            }

            # Add optional fields if provided
            if notes:
                update_data["notes"] = notes
            if rating and 1 <= rating <= 5:
                update_data["rating"] = rating

            # Update the check-in record
            result = self.customer_checkins_collection.update_one(
                {"_id": active_checkin["_id"]},
                {"$set": update_data}
            )

            if result.modified_count == 0:
                return {
                    "success": False,
                    "message": "Failed to end check-in",
                    "error": {"code": "UPDATE_FAILED", "details": "Check-in record could not be updated"}
                }

            # Calculate visit duration
            checkin_time = active_checkin.get("checkin_time")
            duration_minutes = 0
            if checkin_time:
                try:
                    checkin_dt = datetime.fromisoformat(checkin_time.replace('Z', '+00:00'))
                    duration = now - checkin_dt.replace(tzinfo=None)
                    duration_minutes = int(duration.total_seconds() / 60)
                except Exception:
                    pass

            return {
                "success": True,
                "message": "Check-in ended successfully",
                "data": {
                    "checkin_id": str(active_checkin["_id"]),
                    "customer_id": customer_id,
                    "checkout_time": now.isoformat(),
                    "duration_minutes": duration_minutes,
                    "notes": notes,
                    "rating": rating
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"End check-in failed: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_beat_plan_list(self, user_id: str, status: str = None, active_tab: str = "today", limit: int = 50, 
                          user_lat: float = None, user_lng: float = None) -> Dict[str, Any]:
        """Get beat plan list for the UI: returns coverage and flat customers list for the given date."""
        try:
            query = {"user_id": user_id, "is_active": True, "del": {"$ne": 1}}
            if status:
                query["status"] = status
            # Coerce location
            try:
                user_lat = float(user_lat) if user_lat is not None else None
                user_lng = float(user_lng) if user_lng is not None else None
            except Exception:
                user_lat, user_lng = None, None

            # Date tab filter
            from datetime import datetime as _dt
            today_str = _dt.now(self.timezone).strftime('%Y-%m-%d')
            if active_tab == "today":
                query["plan_date"] = today_str
            elif active_tab == "upcoming":
                query["plan_date"] = {"$gt": today_str}

            beat_plans = list(self.beat_plans_collection.find(query)
                            .sort("created_at", -1)
                            .limit(limit))

            # Convert ObjectId to string and enhance with route optimization
            enhanced_plans = []
            all_customers: List[Dict[str, Any]] = []
            for plan in beat_plans:
                plan['_id'] = str(plan['_id'])
                
                # Get customer details for route optimization
                customer_ids = plan.get('customer_ids', [])
                customers = list(self.customers_collection.find({
                    "_id": {"$in": [ObjectId(cid) for cid in customer_ids]},
                    "status": "active",
                    "del": {"$ne": 1}
                }))
                
                # Format customer data with distance calculation
                formatted_customers = []
                for customer in customers:
                    customer['_id'] = str(customer['_id'])
                    customer['customer_id'] = str(customer['_id'])
                    customer['beat_plan_id'] = plan['_id']  # Add beat plan ID
                    customer['name'] = customer.get('name', '')
                    customer['company_name'] = customer.get('company_name', '')
                    customer['address'] = customer.get('billing_address', '') or customer.get('state', '')
                    customer['phone'] = customer.get('mobile') or customer.get('phone', '')
                    customer['email'] = customer.get('email', '')
                    customer['city'] = customer.get('city', '')
                    customer['state'] = customer.get('state', '')
                    customer['pincode'] = customer.get('pincode', '')                    
                    # Calculate distance from user to customer
                    customer_lat = customer.get('latitude')
                    customer_lng = customer.get('longitude')
                    
                    # Convert customer coordinates to float
                    if customer_lat is not None:
                        try:
                            customer_lat = float(customer_lat)
                        except (ValueError, TypeError):
                            customer_lat = None
                    
                    if customer_lng is not None:
                        try:
                            customer_lng = float(customer_lng)
                        except (ValueError, TypeError):
                            customer_lng = None
                    
                    if (user_lat and user_lng and customer_lat and customer_lng):
                        distance_meters = calculate_distance(user_lat, user_lng, customer_lat, customer_lng)
                        distance_km = distance_meters / 1000
                        customer['distance'] = format_distance(distance_meters)
                        customer['distance_km'] = round(distance_km, 1)
                        customer['distance_formatted'] = format_distance(distance_meters)
                    else:
                        customer['distance'] = format_distance(0.0)
                        customer['distance_km'] = 0.0
                        customer['distance_formatted'] = format_distance(0.0)
                    formatted_customers.append(customer)
                
                # Optimize route if user coordinates are available
                optimized_customers = formatted_customers
                route_stats = None
                
                if user_lat and user_lng and len(formatted_customers) > 0:
                    optimized_customers = optimize_route(formatted_customers, user_lat, user_lng)
                    route_stats = calculate_route_stats(optimized_customers, user_lat, user_lng)
                    
                    # Add route order to customers
                    for i, customer in enumerate(optimized_customers):
                        customer['route_order'] = i + 1
                
                # Add enhanced data to plan
                plan['customers'] = optimized_customers
                plan['route_optimization'] = {
                    "optimized": user_lat is not None and user_lng is not None,
                    "stats": route_stats
                }
                plan['total_customers'] = len(formatted_customers)
                
                enhanced_plans.append(plan)
                all_customers.extend(optimized_customers)
            # Compute coverage for the day from check-ins (only for 'today' tab)
            coverage_completed = 0
            total_for_day = len(all_customers)
            coverage_date = today_str if active_tab == "today" else None
            if coverage_date and total_for_day > 0:
                # unique customers checked-in for the date
                checked = self.customer_checkins_collection.find({
                    "user_id": user_id,
                    "plan_date": coverage_date,
                    "status": {"$in": ["in", "out", "completed"]}
                })
                checked_ids = {str(doc.get('customer_id')) for doc in checked}
                coverage_completed = len(checked_ids)
            percent = round((coverage_completed / total_for_day) * 100) if total_for_day else 0

            # Build UI-shaped response with checkin status
            ui_customers = []
            for cust in all_customers:
                customer_id = cust.get('customer_id')
                
                # Get checkin status for this customer on the coverage date
                checkin_status = "pending"  # Default status
                if coverage_date:
                    checkin_record = self.customer_checkins_collection.find_one({
                        "user_id": user_id,
                        "customer_id": customer_id,
                        "plan_date": coverage_date,
                        "del": {"$ne": 1}
                    })
                    
                    if checkin_record:
                        if checkin_record.get("status") == "in":
                            checkin_status = "in_progress"
                        elif checkin_record.get("status") in ["out", "completed"]:
                            checkin_status = "completed"
                
                ui_customers.append({
                    "id": customer_id,
                    "name": cust.get('name') or cust.get('company_name'),
                    "address": cust.get('address') or cust.get('city') or cust.get('state'),
                    "phone": cust.get('phone', ''),
                    "distance": cust.get('distance') if 'distance' in cust else cust.get('distance_formatted', '0 m'),
                    "distance_km": cust.get('distance_km', 0),
                    "routeOrder": cust.get('route_order'),
                    "checkin_status": checkin_status,
                    "type": cust.get('type', ''),
                    "beat_plan_id": cust.get('beat_plan_id')
                })

            return {
                "success": True,
                "data": {
                    "coverage": {
                        "percent": percent,
                        "completed": coverage_completed,
                        "total": total_for_day
                    },
                    "beat_plan_id": ui_customers[0].get('beat_plan_id') if ui_customers else None,
                    "customers": ui_customers,
                    "plans": enhanced_plans,
                    "route_optimization_enabled": user_lat is not None and user_lng is not None
                }
            }
         
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get beat plans: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
    
    def get_beat_plans_by_day(self, user_id: str, day_name: str, limit: int = 50, 
                             user_lat: float = None, user_lng: float = None) -> Dict[str, Any]:
        """Get beat plans for a specific day name (e.g., 'Monday', 'Tuesday')"""
        try:
            # Validate day name
            valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            if day_name not in valid_days:
                return {
                    "success": False,
                    "message": f"Invalid day name. Must be one of: {', '.join(valid_days)}",
                    "error": {"code": "INVALID_DAY_NAME", "details": "Day name must be a valid weekday"}
                }
            
            # Query beat plans by day name
            query = {
                "user_id": user_id, 
                "plan_day": day_name,
                "is_active": True,
                "del": {"$ne": 1}
            }
            
            beat_plans = list(self.beat_plans_collection.find(query)
                            .sort("plan_date", -1)  # Sort by date, newest first
                            .limit(limit))
            
            # Convert ObjectId to string and enhance with route optimization
            enhanced_plans = []
            for plan in beat_plans:
                plan['_id'] = str(plan['_id'])
                
                # Get customer details for route optimization
                customer_ids = plan.get('customer_ids', [])
                customers = list(self.customers_collection.find({
                    "_id": {"$in": [ObjectId(cid) for cid in customer_ids]},
                    "status": "active",
                    "del": {"$ne": 1}
                }))
                
                # Format customer data with distance calculation
                formatted_customers = []
                for customer in customers:
                    customer['_id'] = str(customer['_id'])
                    customer['customer_id'] = str(customer['_id'])
                    customer['name'] = customer.get('name', '')
                    customer['company_name'] = customer.get('company_name', '')
                    customer['address'] = customer.get('billing_address', '')
                    customer['phone'] = customer.get('mobile') or customer.get('phone', '')
                    customer['email'] = customer.get('email', '')
                    customer['city'] = customer.get('city', '')
                    customer['state'] = customer.get('state', '')
                    customer['pincode'] = customer.get('pincode', '')
                    
                    # Calculate distance from user to customer
                    customer_lat = customer.get('latitude')
                    customer_lng = customer.get('longitude')
                    
                    # Convert customer coordinates to float
                    if customer_lat is not None:
                        try:
                            customer_lat = float(customer_lat)
                        except (ValueError, TypeError):
                            customer_lat = None
                    
                    if customer_lng is not None:
                        try:
                            customer_lng = float(customer_lng)
                        except (ValueError, TypeError):
                            customer_lng = None
                    
                    if (user_lat and user_lng and customer_lat and customer_lng):
                        distance_meters = calculate_distance(user_lat, user_lng, customer_lat, customer_lng)
                        distance_km = distance_meters / 1000
                        customer['distance'] = format_distance(distance_meters)
                        customer['distance_km'] = round(distance_km, 1)
                    else:
                        customer['distance'] = format_distance(0.0)
                        customer['distance_km'] = 0.0
                    
                    formatted_customers.append(customer)
                
                # Optimize route if user coordinates are available
                optimized_customers = formatted_customers
                route_stats = None
                
                if user_lat and user_lng and len(formatted_customers) > 0:
                    optimized_customers = optimize_route(formatted_customers, user_lat, user_lng)
                    route_stats = calculate_route_stats(optimized_customers, user_lat, user_lng)
                    
                    # Add route order to customers
                    for i, customer in enumerate(optimized_customers):
                        customer['route_order'] = i + 1
                
                # Add enhanced data to plan
                plan['customers'] = optimized_customers
                plan['route_optimization'] = {
                    "optimized": user_lat is not None and user_lng is not None,
                    "stats": route_stats
                }
                plan['total_customers'] = len(formatted_customers)
                
                enhanced_plans.append(plan)
            
            return {
                "success": True,
                "data": {
                    "beat_plans": enhanced_plans,
                    "total": len(enhanced_plans),
                    "day_name": day_name,
                    "route_optimization_enabled": user_lat is not None and user_lng is not None
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get beat plans by day: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_beat_plan_history(self, user_id: str, period: str = "this_month") -> Dict[str, Any]:
        """Get beat plan history with statistics for last month or this month"""
        try:
            from datetime import datetime as _dt
            from calendar import monthrange
            
            now = _dt.now(self.timezone)
            
            # Calculate date range based on period
            if period == "last_month":
                # Last month
                if now.month == 1:
                    target_month = 12
                    target_year = now.year - 1
                else:
                    target_month = now.month - 1
                    target_year = now.year
            else:  # this_month
                target_month = now.month
                target_year = now.year
            
            # Get first and last day of the target month
            first_day = _dt(target_year, target_month, 1).strftime('%Y-%m-%d')
            last_day_num = monthrange(target_year, target_month)[1]
            last_day = _dt(target_year, target_month, last_day_num).strftime('%Y-%m-%d')
            
            # Query beat plans for the period
            query = {
                "user_id": user_id,
                "is_active": True,
                "del": {"$ne": 1},
                "plan_date": {"$gte": first_day, "$lte": last_day}
            }
            
            beat_plans = list(self.beat_plans_collection.find(query).sort("plan_date", -1))
            
            # Initialize statistics
            total_beat_days = len(beat_plans)
            total_planned = 0
            total_completed = 0
            total_missed = 0
            total_visit_duration_minutes = 0
            visit_count = 0
            
            # Process each beat plan
            history_list = []
            for plan in beat_plans:
                plan_id = str(plan.get("_id"))
                plan_date = plan.get("plan_date")
                customer_ids = plan.get("customer_ids", [])
                planned_count = len(customer_ids)
                total_planned += planned_count
                
                # Get check-ins for this beat plan date
                checkins = list(self.customer_checkins_collection.find({
                    "user_id": user_id,
                    "plan_date": plan_date,
                    "del": {"$ne": 1}
                }))
                
                # Calculate completed and missed
                completed_customer_ids = set()
                for checkin in checkins:
                    if checkin.get("status") in ["out", "completed"]:
                        completed_customer_ids.add(checkin.get("customer_id"))
                        
                        # Calculate visit duration
                        checkin_time = checkin.get("checkin_time")
                        checkout_time = checkin.get("checkout_time")
                        if checkin_time and checkout_time:
                            try:
                                checkin_dt = _dt.fromisoformat(checkin_time.replace('Z', '+00:00'))
                                checkout_dt = _dt.fromisoformat(checkout_time.replace('Z', '+00:00'))
                                duration = checkout_dt - checkin_dt.replace(tzinfo=None)
                                total_visit_duration_minutes += int(duration.total_seconds() / 60)
                                visit_count += 1
                            except Exception:
                                pass
                
                completed_count = len(completed_customer_ids)
                missed_count = planned_count - completed_count
                
                total_completed += completed_count
                total_missed += missed_count
                
                # Determine status
                if completed_count == planned_count:
                    status = "completed"
                    status_label = "Completed"
                elif completed_count > 0:
                    status = "partial"
                    status_label = "Partial"
                else:
                    status = "missed"
                    status_label = "Missed"
                
                # Parse date for display
                try:
                    date_obj = _dt.strptime(plan_date, '%Y-%m-%d')
                    month_abbr = date_obj.strftime('%b').upper()
                    day_num = date_obj.strftime('%d')
                except Exception:
                    month_abbr = "JAN"
                    day_num = "01"
                
                history_list.append({
                    "beat_plan_id": plan_id,
                    "plan_name": plan.get("plan_name", "Beat Plan"),
                    "area_name": plan.get("area_name", ""),
                    "plan_date": plan_date,
                    "month": month_abbr,
                    "day": day_num,
                    "status": status,
                    "status_label": status_label,
                    "planned": planned_count,
                    "completed": completed_count,
                    "missed": missed_count
                })
            
            # Calculate average visit duration
            avg_visit_duration_minutes = 0
            avg_visit_duration_formatted = "0h 0m"
            if visit_count > 0:
                avg_visit_duration_minutes = total_visit_duration_minutes // visit_count
                hours = avg_visit_duration_minutes // 60
                minutes = avg_visit_duration_minutes % 60
                avg_visit_duration_formatted = f"{hours}h {minutes}m"
            
            return {
                "success": True,
                "data": {
                    "period": period,
                    "statistics": {
                        "completed_visits": total_completed,
                        "missed_visits": total_missed,
                        "total_beat_days": total_beat_days,
                        "avg_visit_duration": avg_visit_duration_formatted,
                        "avg_visit_duration_minutes": avg_visit_duration_minutes
                    },
                    "history": history_list
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get beat plan history: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_beat_plan_detail(self, user_id: str, beat_plan_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific beat plan with timeline of visits"""
        try:
            from datetime import datetime as _dt
            
            # Validate and fetch beat plan
            try:
                plan = self.beat_plans_collection.find_one({
                    "_id": ObjectId(beat_plan_id),
                    "user_id": user_id,
                    "del": {"$ne": 1}
                })
            except Exception:
                return {
                    "success": False,
                    "message": "Invalid beat_plan_id",
                    "error": {"code": "INVALID_ID", "details": "beat_plan_id must be a valid ObjectId"}
                }
            
            if not plan:
                return {
                    "success": False,
                    "message": "Beat plan not found",
                    "error": {"code": "NOT_FOUND", "details": "Beat plan does not exist or not assigned to you"}
                }
            
            # Get plan details
            plan_date = plan.get("plan_date")
            plan_name = plan.get("plan_name", "Beat Plan")
            area_name = plan.get("area_name", "")
            customer_ids = plan.get("customer_ids", [])
            planned_count = len(customer_ids)
            
            # Parse date for display
            try:
                date_obj = _dt.strptime(plan_date, '%Y-%m-%d')
                month_abbr = date_obj.strftime('%b').upper()
                day_num = date_obj.strftime('%d')
                year = date_obj.strftime('%Y')
                formatted_date = f"{month_abbr} {day_num}, {year}"
            except Exception:
                formatted_date = plan_date
                month_abbr = "JAN"
                day_num = "01"
                year = "2024"
            
            # Get all check-ins for this beat plan date
            checkins = list(self.customer_checkins_collection.find({
                "user_id": user_id,
                "plan_date": plan_date,
                "del": {"$ne": 1}
            }).sort("checkin_time", 1))
            
            # Calculate statistics
            completed_customer_ids = set()
            total_distance_km = 0
            total_duration_minutes = 0
            
            # Build timeline of visits
            timeline = []
            for customer_id in customer_ids:
                # Get customer details
                try:
                    customer = self.customers_collection.find_one({"_id": ObjectId(customer_id)})
                except Exception:
                    customer = None
                
                if not customer:
                    continue
                
                customer_name = customer.get("company_name") or customer.get("name", "Unknown")
                
                # Find check-in for this customer
                checkin = next((c for c in checkins if c.get("customer_id") == customer_id), None)
                
                visit_status = "pending"
                visit_time = None
                visit_time_formatted = None
                duration_minutes = 0
                distance_km = 0
                
                if checkin:
                    checkin_time = checkin.get("checkin_time")
                    checkout_time = checkin.get("checkout_time")
                    
                    # Format visit time
                    if checkin_time:
                        try:
                            checkin_dt = _dt.fromisoformat(checkin_time.replace('Z', '+00:00'))
                            visit_time_formatted = checkin_dt.strftime('%I:%M %p')
                            visit_time = checkin_time
                        except Exception:
                            visit_time_formatted = "N/A"
                    
                    # Calculate duration
                    if checkin_time and checkout_time:
                        try:
                            checkin_dt = _dt.fromisoformat(checkin_time.replace('Z', '+00:00'))
                            checkout_dt = _dt.fromisoformat(checkout_time.replace('Z', '+00:00'))
                            duration = checkout_dt - checkin_dt.replace(tzinfo=None)
                            duration_minutes = int(duration.total_seconds() / 60)
                            total_duration_minutes += duration_minutes
                        except Exception:
                            pass
                    
                    # Get distance
                    distance_m = checkin.get("distance_m", 0)
                    distance_km = round(distance_m / 1000, 2) if distance_m else 0
                    total_distance_km += distance_km
                    
                    # Determine status
                    if checkin.get("status") in ["out", "completed"]:
                        visit_status = "completed"
                        completed_customer_ids.add(customer_id)
                    elif checkin.get("status") == "in":
                        visit_status = "in_progress"
                
                timeline.append({
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "visit_time": visit_time,
                    "visit_time_formatted": visit_time_formatted or "Not visited",
                    "status": visit_status,
                    "duration_minutes": duration_minutes,
                    "distance_km": distance_km
                })
            
            # Calculate final statistics
            completed_count = len(completed_customer_ids)
            missed_count = planned_count - completed_count
            
            # Determine overall status
            if completed_count == planned_count:
                overall_status = "completed"
                status_label = "Completed"
            elif completed_count > 0:
                overall_status = "partial"
                status_label = "Partial"
            else:
                overall_status = "missed"
                status_label = "Missed"
            
            # Format total duration
            hours = total_duration_minutes // 60
            minutes = total_duration_minutes % 60
            total_duration_formatted = f"{hours}h {minutes}m"
            
            return {
                "success": True,
                "data": {
                    "beat_plan_id": beat_plan_id,
                    "plan_date": plan_date,
                    "formatted_date": formatted_date,
                    "month": month_abbr,
                    "day": day_num,
                    "year": year,
                    "plan_name": plan_name,
                    "area_name": area_name,
                    "status": overall_status,
                    "status_label": status_label,
                    "statistics": {
                        "planned": planned_count,
                        "completed": completed_count,
                        "missed": missed_count,
                        "total_distance_km": round(total_distance_km, 1),
                        "total_duration": total_duration_formatted,
                        "total_duration_minutes": total_duration_minutes
                    },
                    "timeline": timeline
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get beat plan detail: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }
    
