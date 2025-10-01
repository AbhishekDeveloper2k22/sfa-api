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
                        "latitude": user_lat,
                        "longitude": user_lng,
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
                "user_latitude": user_lat,
                "user_longitude": user_lng,
                "customer_latitude": cust_lat,
                "customer_longitude": cust_lng,
                "distance_m": round(distance_m, 2),
                "radius_m": radius_m,
                "beat_plan_id": beat_plan_id,
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
                    else:
                        customer['distance'] = format_distance(0.0)
                        customer['distance_km'] = 0.0
                    
                    # UI-specific fields
                    customer['distance_formatted'] = format_distance(distance_meters if 'distance_meters' in locals() else 0)
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

            # Build UI-shaped response
            ui_customers = []
            for cust in all_customers:
                ui_customers.append({
                    "id": cust.get('customer_id'),
                    "name": cust.get('name') or cust.get('company_name'),
                    "address": cust.get('address') or cust.get('city') or cust.get('state'),
                    "phone": cust.get('phone', ''),
                    "distance": cust.get('distance') if 'distance' in cust else cust.get('distance_formatted', '0 m'),
                    "distance_km": cust.get('distance_km', 0),
                    "routeOrder": cust.get('route_order')
                })

            return {
                "success": True,
                "data": {
                    "coverage": {
                        "percent": percent,
                        "completed": coverage_completed,
                        "total": total_for_day
                    },
                    "customers": ui_customers,
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
    
