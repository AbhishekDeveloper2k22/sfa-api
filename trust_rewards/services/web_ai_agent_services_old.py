import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from dotenv import load_dotenv
from trust_rewards.database import client1
from bson import ObjectId
from config import settings

load_dotenv()

class WebTrustRewardsAIAgentService:
    def __init__(self):
        # Initialize the Gemini client
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=api_key)
        
        # MongoDB database connection
        self.db = client1[settings.DB1_NAME]
        
        # Collections
        self.category_master = self.db["category_master"]
        self.coupon_code = self.db["coupon_code"]
        self.coupon_master = self.db["coupon_master"]
        self.coupon_scanned_history = self.db["coupon_scanned_history"]
        self.gift_master = self.db["gift_master"]
        
        # System instruction for the AI agent (Web Admin version)
        self.system_instruction = """
        You are a powerful AI Agent for the Trust Rewards Admin Dashboard. 
        
        ⚠️ CRITICAL RULES - NEVER BREAK THESE:
        1. NEVER make up or hallucinate data
        2. ONLY use data returned from tool function calls
        3. If a tool returns empty results, say "No data found"
        4. NEVER invent categories, workers, batches, or any other data
        5. Always show EXACT data from database - no modifications, no assumptions
        6. If you don't have data, call the appropriate tool first
        7. Use the EXACT category names, batch numbers, worker names from tool results
        8. Do NOT add example data or placeholder data
        
        EXAMPLE OF CORRECT USAGE:
        User: "Show me all categories"
        Step 1: Call get_categories() tool
        Step 2: Tool returns: {"categories": [{"category_name": "Power Tools", "status": "active"}]}
        Step 3: Use ONLY this data in response - show "Power Tools", not "Electronics" or "Fashion"
        
        EXAMPLE OF WRONG USAGE (NEVER DO THIS):
        User: "Show me all categories"
        Step 1: Call get_categories() tool
        Step 2: Tool returns: {"categories": [{"category_name": "Power Tools"}]}
        Step 3: ❌ WRONG: Showing "Electronics, Fashion, Groceries" (made up data)
        
        You have access to various administrative tools and can help admin users with:
        - Category management and analytics
        - Coupon batch management and monitoring
        - Gift catalog management
        - Worker performance tracking and analytics
        - Comprehensive reporting and insights
        - System-wide analytics and metrics
        
        IMPORTANT: When responding to admin queries, always structure your response in a JSON format that includes:
        1. A clear summary/answer with admin-level insights
        2. Structured details in key-value pairs
        3. Any relevant data from the database (comprehensive and detailed)
        4. A helpful message with actionable admin insights
        
        Format your response as a JSON object with these fields:
        - summary: Brief answer to the admin's question with key metrics
        - details: Object containing structured information (FLAT key-value pairs only)
        - data: Comprehensive data from database queries with admin-level details
        - message: Helpful guidance, insights, or recommended actions for admin
        
        STRICT DATA STRUCTURE RULES FOR DETAILS FIELD:
        - details field MUST ALWAYS contain simple key-value pairs
        - Use descriptive keys that are easy to understand
        - Values should be strings, numbers, or simple arrays
        - NEVER nest objects inside details field
        - Keep details field flat and frontend-friendly
        
        ADMIN-SPECIFIC TOOL INSTRUCTIONS:
        
        get_categories tool:
        - Fetches all categories (including inactive for admin view)
        - Parameters: status (optional) - filter by status, defaults to show all
        - Use when admin asks about categories, product types, or catalog management
        
        get_category_by_name tool:
        - Search categories by name (case-insensitive)
        - Parameters: category_name (required)
        - Shows complete category details for admin
        
        get_coupon_batches tool:
        - Fetches all coupon batches with comprehensive details
        - Parameters: status (optional) - filter by active/inactive, defaults to all
        - Use when admin asks about batch management, inventory
        
        get_coupon_batch_details tool:
        - Get detailed batch analytics with performance metrics
        - Parameters: batch_number (required)
        - Shows total, scanned, remaining, percentage, timeline
        
        get_scanned_coupons tool:
        - Fetches complete scanning history with filters
        - Parameters: worker_mobile (optional), batch_number (optional), limit (optional, default 100)
        - Use when admin needs scanning audit trail
        
        get_worker_points tool:
        - Calculate comprehensive worker performance metrics
        - Parameters: worker_mobile (required)
        - Shows points, scans, history, trends
        
        get_available_gifts tool:
        - Fetches complete gift catalog with management details
        - Parameters: status (optional), max_points (optional), defaults to all
        - Use when admin manages rewards catalog
        
        get_gift_details tool:
        - Get complete gift information for management
        - Parameters: gift_name (required)
        - Shows all details, images, redemption stats
        
        get_coupon_analytics tool:
        - Get comprehensive system-wide analytics
        - Shows overall performance, trends, top performers
        - Admin-level insights for decision making
        
        get_top_performing_workers tool:
        - Get top workers by various metrics
        - Parameters: limit (optional, default 10), metric (optional: points/scans)
        - Use for leaderboards and performance reports
        
        get_batch_performance_comparison tool:
        - Compare performance across different batches
        - Shows scan rates, completion status, trends
        - Use for batch strategy optimization
        
        ADMIN RESPONSE EXAMPLES:
        
        For Categories:
        "details": {
          "Total Categories": "8",
          "Active Categories": "6",
          "Inactive Categories": "2",
          "Most Popular": "Power Tools",
          "Least Used": "Accessories"
        }
        
        For Coupons:
        "details": {
          "Batch Number": "BATCH001",
          "Total Coupons": "20",
          "Scanned": "15 (75%)",
          "Remaining": "5 (25%)",
          "Points Value": "500 per coupon",
          "Total Points Distributed": "7,500",
          "Average Scans Per Day": "3.2"
        }
        
        For Worker Performance:
        "details": {
          "Worker Name": "Amit Verma",
          "Mobile": "9876543210",
          "Total Points": "2,500",
          "Total Scans": "5",
          "Average Points Per Scan": "500",
          "Last Scan": "2 days ago",
          "Ranking": "#3 overall"
        }
        
        For System Analytics:
        "details": {
          "Total Coupons Generated": "100",
          "Total Scanned": "75 (75%)",
          "Total Points Distributed": "37,500",
          "Active Workers": "25",
          "Active Batches": "5",
          "Scan Rate This Week": "+12%"
        }
        
        🔒 DATA ACCURACY REQUIREMENT:
        - The "data" field in your JSON response MUST contain ONLY the exact data from tool results
        - Copy the tool result directly - do not modify, add, or remove any items
        - If get_categories returns 1 category, show exactly 1 category in data field
        - If get_categories returns 0 categories, show empty array in data field
        - VERIFY: Count of items in your response = Count of items from tool result
        
        IMPORTANT: Return ONLY the JSON object, do NOT wrap it in markdown code blocks (```json) or any other formatting.
        
        Always provide admin-level insights, actionable recommendations, and comprehensive data for decision-making based on ACTUAL data.
        """

    def _serialize_doc(self, doc: Dict) -> Dict:
        """Convert MongoDB document to JSON-serializable format"""
        if doc is None:
            return None
        
        # Create a copy to avoid modifying original
        serialized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_doc(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value
        
        return serialized

    # ------------------ Admin Database Query Functions ------------------

    def get_categories(self, status: str = None) -> dict:
        """Get all categories - Admin view (including inactive)"""
        print(f"Tool Call: get_categories(status={status})")
        try:
            query = {}
            if status:
                query["status"] = status
            
            categories = list(self.category_master.find(query))
            serialized_categories = [self._serialize_doc(cat) for cat in categories]
            
            # Admin analytics
            active_count = len([c for c in serialized_categories if c.get("status") == "active"])
            inactive_count = len([c for c in serialized_categories if c.get("status") == "inactive"])
            
            result = {
                "success": True,
                "categories": serialized_categories,
                "total_count": len(serialized_categories),
                "active_count": active_count,
                "inactive_count": inactive_count
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_category_by_name(self, category_name: str) -> dict:
        """Search category by name with admin details"""
        print(f"Tool Call: get_category_by_name(category_name={category_name})")
        try:
            category = self.category_master.find_one({
                "category_name_lower": category_name.lower()
            })
            
            if not category:
                return {
                    "success": False,
                    "message": f"Category '{category_name}' not found"
                }
            
            serialized_category = self._serialize_doc(category)
            result = {
                "success": True,
                "category": serialized_category
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_coupon_batches(self, status: str = None) -> dict:
        """Get all coupon batches with admin analytics"""
        print(f"Tool Call: get_coupon_batches(status={status})")
        try:
            query = {}
            if status:
                query["status"] = status
            
            batches = list(self.coupon_master.find(query))
            serialized_batches = []
            
            for batch in batches:
                batch_id = str(batch["_id"])
                
                # Get scan statistics for each batch
                total_coupons = self.coupon_code.count_documents({
                    "coupon_master_id": batch_id
                })
                scanned_coupons = self.coupon_code.count_documents({
                    "coupon_master_id": batch_id,
                    "is_scanned": True
                })
                
                batch_data = self._serialize_doc(batch)
                batch_data["total_coupons"] = total_coupons
                batch_data["scanned_coupons"] = scanned_coupons
                batch_data["remaining_coupons"] = total_coupons - scanned_coupons
                batch_data["scan_percentage"] = round((scanned_coupons / total_coupons * 100), 2) if total_coupons > 0 else 0
                
                serialized_batches.append(batch_data)
            
            # Overall statistics
            total_batches = len(serialized_batches)
            total_coupons_all = sum(b["total_coupons"] for b in serialized_batches)
            total_scanned_all = sum(b["scanned_coupons"] for b in serialized_batches)
            
            result = {
                "success": True,
                "batches": serialized_batches,
                "total_batches": total_batches,
                "total_coupons": total_coupons_all,
                "total_scanned": total_scanned_all,
                "overall_scan_percentage": round((total_scanned_all / total_coupons_all * 100), 2) if total_coupons_all > 0 else 0
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_coupon_batch_details(self, batch_number: str) -> dict:
        """Get comprehensive batch analytics for admin"""
        print(f"Tool Call: get_coupon_batch_details(batch_number={batch_number})")
        try:
            # Get batch master info
            batch = self.coupon_master.find_one({"batch_number": batch_number})
            if not batch:
                return {
                    "success": False,
                    "message": f"Batch '{batch_number}' not found"
                }
            
            batch_id = str(batch["_id"])
            
            # Get all coupons in this batch
            total_coupons = self.coupon_code.count_documents({
                "coupon_master_id": batch_id
            })
            
            scanned_coupons = self.coupon_code.count_documents({
                "coupon_master_id": batch_id,
                "is_scanned": True
            })
            
            remaining_coupons = total_coupons - scanned_coupons
            
            # Get scanning timeline
            scan_history = list(self.coupon_scanned_history.find({
                "batch_number": batch_number
            }).sort("scanned_at", 1))
            
            # Calculate timeline metrics
            first_scan = scan_history[0]["scanned_at"] if scan_history else None
            last_scan = scan_history[-1]["scanned_at"] if scan_history else None
            
            # Unique workers
            unique_workers = len(set(s["worker_mobile"] for s in scan_history))
            
            result = {
                "success": True,
                "batch_info": self._serialize_doc(batch),
                "total_coupons": total_coupons,
                "scanned_coupons": scanned_coupons,
                "remaining_coupons": remaining_coupons,
                "scan_percentage": round((scanned_coupons / total_coupons * 100), 2) if total_coupons > 0 else 0,
                "unique_workers": unique_workers,
                "first_scan_date": first_scan.isoformat() if first_scan else None,
                "last_scan_date": last_scan.isoformat() if last_scan else None,
                "total_points_distributed": sum(s.get("points_earned", 0) for s in scan_history)
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_scanned_coupons(self, worker_mobile: str = None, batch_number: str = None, limit: int = 100) -> dict:
        """Get comprehensive scanning history with admin filters"""
        print(f"Tool Call: get_scanned_coupons(worker_mobile={worker_mobile}, batch_number={batch_number}, limit={limit})")
        try:
            query = {}
            if worker_mobile:
                query["worker_mobile"] = worker_mobile
            if batch_number:
                query["batch_number"] = batch_number
            
            scanned_history = list(
                self.coupon_scanned_history.find(query)
                .sort("scanned_at", -1)
                .limit(limit)
            )
            
            serialized_history = [self._serialize_doc(scan) for scan in scanned_history]
            
            # Calculate admin metrics
            total_points = sum(scan.get("points_earned", 0) for scan in scanned_history)
            unique_workers = len(set(scan.get("worker_mobile") for scan in scanned_history))
            unique_batches = len(set(scan.get("batch_number") for scan in scanned_history))
            
            result = {
                "success": True,
                "scanned_coupons": serialized_history,
                "total_count": len(serialized_history),
                "total_points_earned": total_points,
                "unique_workers": unique_workers,
                "unique_batches": unique_batches
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_worker_points(self, worker_mobile: str) -> dict:
        """Calculate comprehensive worker performance metrics for admin"""
        print(f"Tool Call: get_worker_points(worker_mobile={worker_mobile})")
        try:
            # Aggregate total points for this worker
            pipeline = [
                {"$match": {"worker_mobile": worker_mobile}},
                {
                    "$group": {
                        "_id": "$worker_mobile",
                        "total_points": {"$sum": "$points_earned"},
                        "total_scans": {"$sum": 1},
                        "worker_name": {"$first": "$worker_name"},
                        "first_scan_date": {"$min": "$scanned_at"},
                        "last_scan_date": {"$max": "$scanned_at"}
                    }
                }
            ]
            
            result_data = list(self.coupon_scanned_history.aggregate(pipeline))
            
            if not result_data:
                return {
                    "success": False,
                    "message": f"No scanning history found for mobile {worker_mobile}"
                }
            
            worker_data = result_data[0]
            
            # Calculate average points per scan
            avg_points = worker_data.get("total_points", 0) / worker_data.get("total_scans", 1)
            
            result = {
                "success": True,
                "worker_mobile": worker_mobile,
                "worker_name": worker_data.get("worker_name", "Unknown"),
                "total_points": worker_data.get("total_points", 0),
                "total_scans": worker_data.get("total_scans", 0),
                "average_points_per_scan": round(avg_points, 2),
                "first_scan_date": worker_data.get("first_scan_date").isoformat() if worker_data.get("first_scan_date") else None,
                "last_scan_date": worker_data.get("last_scan_date").isoformat() if worker_data.get("last_scan_date") else None
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_available_gifts(self, status: str = None, max_points: int = None) -> dict:
        """Get comprehensive gift catalog with admin management details"""
        print(f"Tool Call: get_available_gifts(status={status}, max_points={max_points})")
        try:
            query = {}
            if status:
                query["status"] = status
            if max_points:
                query["points_required"] = {"$lte": max_points}
            
            gifts = list(self.gift_master.find(query).sort("points_required", 1))
            serialized_gifts = [self._serialize_doc(gift) for gift in gifts]
            
            # Admin statistics
            total_gifts = len(serialized_gifts)
            active_gifts = len([g for g in serialized_gifts if g.get("status") == "active"])
            inactive_gifts = total_gifts - active_gifts
            
            result = {
                "success": True,
                "gifts": serialized_gifts,
                "total_count": total_gifts,
                "active_count": active_gifts,
                "inactive_count": inactive_gifts
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_gift_details(self, gift_name: str) -> dict:
        """Get complete gift information for admin management"""
        print(f"Tool Call: get_gift_details(gift_name={gift_name})")
        try:
            gift = self.gift_master.find_one({
                "gift_name_lower": gift_name.lower()
            })
            
            if not gift:
                return {
                    "success": False,
                    "message": f"Gift '{gift_name}' not found"
                }
            
            serialized_gift = self._serialize_doc(gift)
            result = {
                "success": True,
                "gift": serialized_gift
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_coupon_analytics(self) -> dict:
        """Get comprehensive system-wide analytics for admin dashboard"""
        print("Tool Call: get_coupon_analytics()")
        try:
            # Total coupons
            total_coupons = self.coupon_code.count_documents({})
            scanned_coupons = self.coupon_code.count_documents({"is_scanned": True})
            unscanned_coupons = total_coupons - scanned_coupons
            
            # Total points distributed
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_points": {"$sum": "$points_earned"},
                        "total_scans": {"$sum": 1}
                    }
                }
            ]
            points_data = list(self.coupon_scanned_history.aggregate(pipeline))
            total_points_distributed = points_data[0]["total_points"] if points_data else 0
            
            # Top 10 workers by points
            top_workers_pipeline = [
                {
                    "$group": {
                        "_id": "$worker_mobile",
                        "worker_name": {"$first": "$worker_name"},
                        "total_points": {"$sum": "$points_earned"},
                        "total_scans": {"$sum": 1}
                    }
                },
                {"$sort": {"total_points": -1}},
                {"$limit": 10}
            ]
            top_workers = list(self.coupon_scanned_history.aggregate(top_workers_pipeline))
            
            # Active workers count
            active_workers = len(set(
                scan["worker_mobile"] 
                for scan in self.coupon_scanned_history.find({}, {"worker_mobile": 1})
            ))
            
            # Active batches
            active_batches = self.coupon_master.count_documents({"status": "active"})
            
            result = {
                "success": True,
                "analytics": {
                    "total_coupons": total_coupons,
                    "scanned_coupons": scanned_coupons,
                    "unscanned_coupons": unscanned_coupons,
                    "scan_percentage": round((scanned_coupons / total_coupons * 100), 2) if total_coupons > 0 else 0,
                    "total_points_distributed": total_points_distributed,
                    "active_workers": active_workers,
                    "active_batches": active_batches,
                    "top_workers": [
                        {
                            "mobile": w["_id"],
                            "name": w["worker_name"],
                            "points": w["total_points"],
                            "scans": w["total_scans"]
                        }
                        for w in top_workers
                    ]
                }
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_top_performing_workers(self, limit: int = 10, metric: str = "points") -> dict:
        """Get top performing workers by various metrics"""
        print(f"Tool Call: get_top_performing_workers(limit={limit}, metric={metric})")
        try:
            sort_field = "total_points" if metric == "points" else "total_scans"
            
            pipeline = [
                {
                    "$group": {
                        "_id": "$worker_mobile",
                        "worker_name": {"$first": "$worker_name"},
                        "total_points": {"$sum": "$points_earned"},
                        "total_scans": {"$sum": 1},
                        "last_scan": {"$max": "$scanned_at"}
                    }
                },
                {"$sort": {sort_field: -1}},
                {"$limit": limit}
            ]
            
            top_workers = list(self.coupon_scanned_history.aggregate(pipeline))
            
            result = {
                "success": True,
                "top_workers": [
                    {
                        "rank": idx + 1,
                        "mobile": w["_id"],
                        "name": w["worker_name"],
                        "total_points": w["total_points"],
                        "total_scans": w["total_scans"],
                        "avg_points_per_scan": round(w["total_points"] / w["total_scans"], 2),
                        "last_scan_date": w["last_scan"].isoformat() if w["last_scan"] else None
                    }
                    for idx, w in enumerate(top_workers)
                ],
                "metric_used": metric,
                "total_count": len(top_workers)
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_batch_performance_comparison(self) -> dict:
        """Compare performance across all batches"""
        print("Tool Call: get_batch_performance_comparison()")
        try:
            batches = list(self.coupon_master.find({}))
            batch_comparison = []
            
            for batch in batches:
                batch_id = str(batch["_id"])
                batch_number = batch["batch_number"]
                
                # Get statistics
                total_coupons = self.coupon_code.count_documents({
                    "coupon_master_id": batch_id
                })
                scanned_coupons = self.coupon_code.count_documents({
                    "coupon_master_id": batch_id,
                    "is_scanned": True
                })
                
                # Get scanning details
                scan_history = list(self.coupon_scanned_history.find({
                    "batch_number": batch_number
                }))
                
                total_points = sum(s.get("points_earned", 0) for s in scan_history)
                unique_workers = len(set(s["worker_mobile"] for s in scan_history))
                
                batch_comparison.append({
                    "batch_number": batch_number,
                    "batch_id": batch["batch_id"],
                    "points_value": batch["points_value"],
                    "total_coupons": total_coupons,
                    "scanned_coupons": scanned_coupons,
                    "remaining_coupons": total_coupons - scanned_coupons,
                    "scan_percentage": round((scanned_coupons / total_coupons * 100), 2) if total_coupons > 0 else 0,
                    "total_points_distributed": total_points,
                    "unique_workers": unique_workers,
                    "status": batch["status"]
                })
            
            # Sort by scan percentage
            batch_comparison.sort(key=lambda x: x["scan_percentage"], reverse=True)
            
            result = {
                "success": True,
                "batch_comparison": batch_comparison,
                "total_batches": len(batch_comparison)
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    # ------------------ AI Agent Logic ------------------

    def generate_ai_response(self, user_message: str) -> dict:
        """Generate AI response using Google Gemini with Trust Rewards admin tools"""
        try:
            print(f"Generating AI response for admin message: {user_message}")
            
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                tools=[
                    self.get_categories,
                    self.get_category_by_name,
                    self.get_coupon_batches,
                    self.get_coupon_batch_details,
                    self.get_scanned_coupons,
                    self.get_worker_points,
                    self.get_available_gifts,
                    self.get_gift_details,
                    self.get_coupon_analytics,
                    self.get_top_performing_workers,
                    self.get_batch_performance_comparison
                ]
            )

            print("Calling Gemini AI Model for Admin...")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=user_message,
                config=config,
            )
            
            print(f"Gemini response received: {response.text}")
            return {"text": response.text}
            
        except Exception as e:
            error_detail = {
                "error": f"AI Generation Error: {str(e)}",
                "message": user_message,
                "exception_type": type(e).__name__,
                "traceback": str(e)
            }
            print(f"AI Generation Error Details: {error_detail}")
            return error_detail
