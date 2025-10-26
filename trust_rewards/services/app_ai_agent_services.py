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

class TrustRewardsAIAgentService:
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
        
        # System instruction for the AI agent
        self.system_instruction = """
        You are a helpful AI Agent for the Trust Rewards System. 
        
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
        
        You have access to various rewards-related tools and can help users with:
        - Category information (Power tools, etc.)
        - Coupon management and tracking
        - Gift catalog and redemption requirements
        - Worker scanning history and points
        - Batch and coupon analytics
        
        IMPORTANT: When responding to user queries, always structure your response in a JSON format that includes:
        1. A clear summary/answer
        2. Structured details in key-value pairs
        3. Any relevant data from the database (simplified and clean)
        4. A helpful message for the user
        
        Format your response as a JSON object with these fields:
        - summary: Brief answer to the user's question
        - details: Object containing structured information (FLAT key-value pairs only)
        - data: Clean, simplified data from database queries
        - message: Helpful guidance or next steps
        
        STRICT DATA STRUCTURE RULES FOR DETAILS FIELD:
        - details field MUST ALWAYS contain simple key-value pairs
        - Use descriptive keys that are easy to understand
        - Values should be strings, numbers, or simple arrays
        - NEVER nest objects inside details field
        - Keep details field flat and frontend-friendly
        
        TOOL-SPECIFIC INSTRUCTIONS:
        
        get_categories tool:
        - Fetches all active product categories
        - Parameters: status (optional) - filter by status
        - Use when user asks about categories, product types, or catalog
        
        get_category_by_name tool:
        - Search categories by name (case-insensitive)
        - Parameters: category_name (required)
        - Use when user asks about specific category
        
        get_coupon_batches tool:
        - Fetches all coupon batches with details
        - Parameters: status (optional) - filter by active/inactive
        - Use when user asks about coupon batches, batch info
        
        get_coupon_batch_details tool:
        - Get detailed information about a specific batch
        - Parameters: batch_number (required)
        - Shows total coupons, scanned count, remaining
        
        get_scanned_coupons tool:
        - Fetches coupon scanning history
        - Parameters: worker_mobile (optional), batch_number (optional), limit (optional)
        - Use when user asks about scanned coupons, worker history
        
        get_worker_points tool:
        - Calculate total points earned by a worker
        - Parameters: worker_mobile (required)
        - Use when user asks about points, earnings, worker status
        
        get_available_gifts tool:
        - Fetches all available gifts for redemption
        - Parameters: status (optional), max_points (optional)
        - Use when user asks about gifts, rewards, redemption catalog
        
        get_gift_details tool:
        - Get detailed information about a specific gift
        - Parameters: gift_name (required)
        - Shows description, points required, images
        
        get_coupon_analytics tool:
        - Get analytics on coupon usage
        - Shows total coupons, scanned vs unscanned, top workers
        
        RESPONSE EXAMPLES:
        
        For Categories:
        "details": {
          "Total Categories": "5",
          "Active Categories": "4",
          "Top Category": "Power Tools"
        }
        
        For Coupons:
        "details": {
          "Batch Number": "BATCH001",
          "Total Coupons": "20",
          "Scanned": "15",
          "Remaining": "5",
          "Points Value": "500"
        }
        
        For Worker Points:
        "details": {
          "Worker Name": "Amit Verma",
          "Mobile": "9876543210",
          "Total Points": "2500",
          "Total Scans": "5",
          "Last Scan": "2025-10-06"
        }
        
        For Gifts:
        "details": {
          "Gift Name": "iPhone 12",
          "Points Required": "2000",
          "Status": "Active",
          "Available": "Yes"
        }
        
        🔒 DATA ACCURACY REQUIREMENT:
        - The "data" field in your JSON response MUST contain ONLY the exact data from tool results
        - Copy the tool result directly - do not modify, add, or remove any items
        - If get_categories returns 1 category, show exactly 1 category in data field
        - If get_categories returns 0 categories, show empty array in data field
        - VERIFY: Count of items in your response = Count of items from tool result
        
        IMPORTANT: Return ONLY the JSON object, do NOT wrap it in markdown code blocks (```json) or any other formatting.
        
        Always be helpful, professional, and provide clear, actionable responses with clean, simplified data structures based on ACTUAL data.
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

    # ------------------ Database Query Functions ------------------

    def get_categories(self, status: str = "active") -> dict:
        """Get all categories from category_master collection"""
        print(f"Tool Call: get_categories(status={status})")
        try:
            query = {}
            if status:
                query["status"] = status
            
            categories = list(self.category_master.find(query))
            serialized_categories = [self._serialize_doc(cat) for cat in categories]
            
            result = {
                "success": True,
                "categories": serialized_categories,
                "total_count": len(serialized_categories)
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_category_by_name(self, category_name: str) -> dict:
        """Search category by name (case-insensitive)"""
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
        """Get all coupon batches from coupon_master collection"""
        print(f"Tool Call: get_coupon_batches(status={status})")
        try:
            query = {}
            if status:
                query["status"] = status
            
            batches = list(self.coupon_master.find(query))
            serialized_batches = [self._serialize_doc(batch) for batch in batches]
            
            result = {
                "success": True,
                "batches": serialized_batches,
                "total_count": len(serialized_batches)
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_coupon_batch_details(self, batch_number: str) -> dict:
        """Get detailed information about a specific coupon batch"""
        print(f"Tool Call: get_coupon_batch_details(batch_number={batch_number})")
        try:
            # Get batch master info
            batch = self.coupon_master.find_one({"batch_number": batch_number})
            if not batch:
                return {
                    "success": False,
                    "message": f"Batch '{batch_number}' not found"
                }
            
            # Get all coupons in this batch
            total_coupons = self.coupon_code.count_documents({
                "coupon_master_id": str(batch["_id"])
            })
            
            scanned_coupons = self.coupon_code.count_documents({
                "coupon_master_id": str(batch["_id"]),
                "is_scanned": True
            })
            
            remaining_coupons = total_coupons - scanned_coupons
            
            result = {
                "success": True,
                "batch_info": self._serialize_doc(batch),
                "total_coupons": total_coupons,
                "scanned_coupons": scanned_coupons,
                "remaining_coupons": remaining_coupons,
                "scan_percentage": round((scanned_coupons / total_coupons * 100), 2) if total_coupons > 0 else 0
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_scanned_coupons(self, worker_mobile: str = None, batch_number: str = None, limit: int = 50) -> dict:
        """Get coupon scanning history with optional filters"""
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
            
            # Calculate total points
            total_points = sum(scan.get("points_earned", 0) for scan in scanned_history)
            
            result = {
                "success": True,
                "scanned_coupons": serialized_history,
                "total_count": len(serialized_history),
                "total_points_earned": total_points
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_worker_points(self, worker_mobile: str) -> dict:
        """Calculate total points earned by a worker"""
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
            result = {
                "success": True,
                "worker_mobile": worker_mobile,
                "worker_name": worker_data.get("worker_name", "Unknown"),
                "total_points": worker_data.get("total_points", 0),
                "total_scans": worker_data.get("total_scans", 0),
                "last_scan_date": worker_data.get("last_scan_date").isoformat() if worker_data.get("last_scan_date") else None
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_available_gifts(self, status: str = "active", max_points: int = None) -> dict:
        """Get all available gifts for redemption"""
        print(f"Tool Call: get_available_gifts(status={status}, max_points={max_points})")
        try:
            query = {}
            if status:
                query["status"] = status
            if max_points:
                query["points_required"] = {"$lte": max_points}
            
            gifts = list(self.gift_master.find(query).sort("points_required", 1))
            serialized_gifts = [self._serialize_doc(gift) for gift in gifts]
            
            result = {
                "success": True,
                "gifts": serialized_gifts,
                "total_count": len(serialized_gifts)
            }
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            error_result = {"error": f"Database error: {str(e)}"}
            print(f"Tool Error: {error_result}")
            return error_result

    def get_gift_details(self, gift_name: str) -> dict:
        """Get detailed information about a specific gift"""
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
        """Get overall coupon analytics"""
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
            
            # Top 5 workers by points
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
                {"$limit": 5}
            ]
            top_workers = list(self.coupon_scanned_history.aggregate(top_workers_pipeline))
            
            result = {
                "success": True,
                "analytics": {
                    "total_coupons": total_coupons,
                    "scanned_coupons": scanned_coupons,
                    "unscanned_coupons": unscanned_coupons,
                    "scan_percentage": round((scanned_coupons / total_coupons * 100), 2) if total_coupons > 0 else 0,
                    "total_points_distributed": total_points_distributed,
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

    # ------------------ AI Agent Logic ------------------

    def generate_ai_response(self, user_message: str) -> dict:
        """Generate AI response using Google Gemini with Trust Rewards tools"""
        try:
            print(f"Generating AI response for message: {user_message}")
            
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
                    self.get_coupon_analytics
                ]
            )

            print("Calling Gemini AI Model...")
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
