import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from dotenv import load_dotenv
from trust_rewards.database import client1
from bson import ObjectId
from config import settings
import json

load_dotenv()

class WebTrustRewardsAIAgentService:
    def __init__(self):
        # Initialize the Gemini client
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=api_key)
        
        # MongoDB database connection
        print("settings.DB1_NAME ",settings.DB1_NAME)
        self.db = client1[settings.DB1_NAME]
        
        # Database Schema Information
        self.schema_info = {
            "category_master": {
                "description": "Product categories in the system",
                "fields": {
                    "_id": "ObjectId - Unique identifier",
                    "category_name": "string - Name of category",
                    "category_name_lower": "string - Lowercase name for search",
                    "description": "string - Category description",
                    "status": "string - active/inactive",
                    "created_at": "string - Date created (YYYY-MM-DD)",
                    "created_time": "string - Time created (HH:MM:SS)",
                    "created_by": "int - User ID who created",
                    "updated_at": "string - Date updated",
                    "updated_by": "int - User ID who updated",
                    "updated_time": "string - Time updated"
                },
                "example": {
                    "category_name": "Power Tools",
                    "status": "active",
                    "description": "Power tools including drills, grinders..."
                }
            },
            "coupon_code": {
                "description": "Individual coupon codes",
                "fields": {
                    "_id": "ObjectId - Unique coupon code ID",
                    "coupon_master_id": "string - Reference to coupon_master",
                    "coupon_value": "int - Points value",
                    "valid_from": "string - Start date",
                    "valid_to": "string - End date",
                    "status": "string - scanned/unscanned",
                    "is_scanned": "boolean - Scanned status",
                    "scanned_by": "string - Worker ID who scanned",
                    "scanned_at": "datetime - Scan timestamp",
                    "created_at": "string - Created date",
                    "coupon_code": "string - Actual coupon code"
                }
            },
            "coupon_master": {
                "description": "Coupon batch master data",
                "fields": {
                    "_id": "ObjectId - Batch ID",
                    "coupon_id": "string - Coupon identifier",
                    "batch_number": "string - Batch number (BATCH001)",
                    "points_value": "int - Points per coupon",
                    "number_of_coupons": "int - Total coupons in batch",
                    "valid_from": "string - Start date",
                    "valid_to": "string - End date",
                    "status": "string - active/inactive",
                    "created_at": "string - Created date"
                }
            },
            "coupon_scanned_history": {
                "description": "History of all coupon scans",
                "fields": {
                    "_id": "ObjectId",
                    "coupon_id": "string - Coupon code ID",
                    "worker_id": "string - Worker ID",
                    "worker_name": "string - Worker name",
                    "worker_mobile": "string - Worker phone",
                    "points_earned": "int - Points earned",
                    "scanned_at": "datetime - Scan timestamp",
                    "scanned_date": "string - Scan date",
                    "scanned_time": "string - Scan time",
                    "coupon_master_id": "string - Batch reference",
                    "batch_number": "string - Batch number"
                }
            },
            "gift_master": {
                "description": "Gift catalog for redemption",
                "fields": {
                    "_id": "ObjectId",
                    "gift_name": "string - Gift name",
                    "gift_name_lower": "string - Lowercase for search",
                    "description": "string - Gift description",
                    "points_required": "int - Points needed to redeem",
                    "status": "string - active/inactive",
                    "created_at": "string - Created date",
                    "images": "array - Array of image objects"
                }
            },
            "gift_redemptions": {
                "description": "Gift redemption requests and history",
                "fields": {
                    "_id": "ObjectId - Unique redemption ID",
                    "redemption_id": "string - Redemption identifier",
                    "worker_id": "string - Worker ID",
                    "worker_name": "string - Worker name",
                    "worker_mobile": "string - Worker phone",
                    "gift_id": "string - Gift master reference",
                    "gift_name": "string - Gift name",
                    "points_used": "int - Points deducted",
                    "status": "string - pending/approved/cancelled/completed",
                    "request_date": "string - Request date (YYYY-MM-DD)",
                    "request_time": "string - Request time (HH:MM:SS)",
                    "request_datetime": "datetime - Request timestamp",
                    "redemption_date": "string - Redemption date",
                    "redemption_time": "string - Redemption time",
                    "redemption_datetime": "datetime - Redemption timestamp",
                    "cancelled_at": "datetime - Cancellation timestamp",
                    "cancelled_date": "string - Cancellation date",
                    "cancelled_time": "string - Cancellation time",
                    "status_history": "array - Status change history",
                    "status_change_by_id": "string - User who changed status",
                    "status_change_date": "string - Status change date",
                    "status_changed_time": "string - Status change time",
                    "created_at": "string - Created date",
                    "created_time": "string - Created time",
                    "created_by": "string - Created by user",
                    "updated_at": "string - Updated date",
                    "updated_time": "string - Updated time",
                    "updated_by": "string - Updated by user"
                }
            },
            "location_master": {
                "description": "Indian postal location and pincode master data",
                "fields": {
                    "_id": "ObjectId - Unique location ID",
                    "pincode": "string - PIN code",
                    "officename": "string - Post office name",
                    "officetype": "string - Office type (BO/SO/HO)",
                    "delivery": "string - Delivery status",
                    "district": "string - District name",
                    "statename": "string - State name",
                    "circlename": "string - Circle name",
                    "regionname": "string - Region name",
                    "divisionname": "string - Division name",
                    "latitude": "string - Latitude coordinate",
                    "longitude": "string - Longitude coordinate"
                }
            },
            "points_master": {
                "description": "Points configuration and rules master",
                "fields": {
                    "_id": "ObjectId - Unique points rule ID",
                    "name": "string - Points rule name",
                    "name_lower": "string - Lowercase for search",
                    "description": "string - Rule description",
                    "category": "string - Points category",
                    "value": "int - Points value",
                    "valid_from": "string - Valid from date (YYYY-MM-DD)",
                    "valid_to": "string - Valid to date (YYYY-MM-DD)",
                    "status": "string - active/inactive",
                    "created_at": "string - Created date",
                    "created_time": "string - Created time",
                    "created_by": "int - User ID who created",
                    "updated_at": "string - Updated date",
                    "updated_time": "string - Updated time",
                    "updated_by": "int - User ID who updated"
                }
            },
            "product_master": {
                "description": "Product catalog master data",
                "fields": {
                    "_id": "ObjectId - Unique product ID",
                    "product_name": "string - Product name",
                    "product_name_lower": "string - Lowercase for search",
                    "description": "string - Product description",
                    "category_id": "string - Category reference",
                    "category_name": "string - Category name",
                    "sub_category_id": "string - Sub-category reference",
                    "sub_category_name": "string - Sub-category name",
                    "sku": "string - Stock Keeping Unit",
                    "mrp": "int - Maximum Retail Price",
                    "status": "string - active/inactive",
                    "images": "array - Array of product image objects",
                    "created_at": "string - Created date",
                    "created_time": "string - Created time",
                    "created_by": "int - User ID who created",
                    "updated_at": "string - Updated date",
                    "updated_time": "string - Updated time",
                    "updated_by": "int - User ID who updated"
                }
            },
            "recent_activity": {
                "description": "Recent activity feed for workers",
                "fields": {
                    "_id": "ObjectId - Unique activity ID",
                    "activity_id": "string - Activity identifier",
                    "worker_id": "string - Worker ID",
                    "activity_type": "string - Type of activity (scan/redemption/etc)",
                    "title": "string - Activity title",
                    "description": "string - Activity description",
                    "points_change": "int - Points added or deducted",
                    "reference_type": "string - Type of reference (coupon/redemption)",
                    "reference_id": "string - Reference ID",
                    "coupon_code": "string - Coupon code if applicable",
                    "batch_number": "string - Batch number if applicable",
                    "redemption_id": "string - Redemption ID if applicable",
                    "created_at": "string - Created timestamp",
                    "created_date": "string - Created date (YYYY-MM-DD)",
                    "created_time": "string - Created time (HH:MM:SS)",
                    "created_by": "string - Created by user"
                }
            },
            "skilled_workers": {
                "description": "Skilled workers master database",
                "fields": {
                    "_id": "ObjectId - Unique worker ID",
                    "worker_id": "string - Worker identifier",
                    "name": "string - Worker name",
                    "mobile": "string - Mobile number",
                    "worker_type": "string - Type of worker",
                    "status": "string - active/inactive/blocked",
                    "status_reason": "string - Reason for status",
                    "kyc_status": "string - KYC verification status",
                    "wallet_points": "int - Current wallet balance",
                    "coupons_scanned": "int - Total coupons scanned",
                    "redemption_count": "int - Total redemptions made",
                    "scheme_enrolled": "string - Enrolled scheme",
                    "pincode": "string - Pincode",
                    "city": "string - City name",
                    "district": "string - District name",
                    "state": "string - State name",
                    "last_activity": "string - Last activity timestamp",
                    "notes": "string - Additional notes",
                    "created_date": "string - Created date",
                    "created_time": "string - Created time",
                    "created_by_id": "int - Created by user ID"
                }
            },
            "sub_category_master": {
                "description": "Product sub-categories master",
                "fields": {
                    "_id": "ObjectId - Unique sub-category ID",
                    "sub_category_name": "string - Sub-category name",
                    "sub_category_name_lower": "string - Lowercase for search",
                    "description": "string - Sub-category description",
                    "category_id": "string - Parent category reference",
                    "category_name": "string - Parent category name",
                    "status": "string - active/inactive",
                    "created_at": "string - Created date",
                    "created_time": "string - Created time",
                    "created_by": "int - User ID who created",
                    "updated_at": "string - Updated date",
                    "updated_time": "string - Updated time",
                    "updated_by": "int - User ID who updated"
                }
            },
            "transaction_ledger": {
                "description": "Complete transaction ledger for all points movements",
                "fields": {
                    "_id": "ObjectId - Unique transaction ID",
                    "transaction_id": "string - Transaction identifier",
                    "worker_id": "string - Worker ID",
                    "transaction_type": "string - credit/debit",
                    "amount": "int - Transaction amount (points)",
                    "previous_balance": "int - Balance before transaction",
                    "new_balance": "int - Balance after transaction",
                    "reference_type": "string - Type of reference (coupon/redemption)",
                    "reference_id": "string - Reference ID",
                    "redemption_id": "string - Redemption ID if applicable",
                    "batch_number": "string - Batch number if applicable",
                    "description": "string - Transaction description",
                    "status": "string - Transaction status",
                    "transaction_date": "string - Transaction date (YYYY-MM-DD)",
                    "transaction_time": "string - Transaction time (HH:MM:SS)",
                    "transaction_datetime": "datetime - Transaction timestamp",
                    "created_at": "string - Created date",
                    "created_time": "string - Created time",
                    "created_by": "string - Created by user"
                }
            }
        }
        
        # System instruction for dynamic AI agent
        self.system_instruction = f"""
        You are an advanced AI Agent for Trust Rewards with DYNAMIC MongoDB query capabilities.
        
        🚨 ABSOLUTE RULES - FOLLOW THESE OR FAIL:
        
        1. YOU MUST CALL A TOOL FOR EVERY DATA REQUEST
        2. NEVER EVER create example data like "Category 1", "Category 2", "Description 1"
        3. If tool returns 0 results, say "No data found" - DO NOT create fake data
        4. If tool returns 1 result, show EXACTLY 1 result - NOT 2 or 3
        5. Copy EXACT field values from tool response - do not modify them
        6. The "data" field in your JSON response MUST be the EXACT tool result
        7. Tool result has 1 document? Show 1 document. Tool has 5? Show 5. Tool has 0? Show 0.
        
        🛑 STRICTLY FORBIDDEN:
        - Creating fake data when tool returns empty
        - Adding extra documents that tool didn't return
        - Modifying field values from tool response
        - Responding without calling any tool
        - Creating "example" or "sample" data
        
        📚 DATABASE SCHEMA:
        {json.dumps(self.schema_info, indent=2)}
        
        🔧 THREE MODES OF OPERATION:
        
        MODE 1: QUERY ANALYSIS ONLY
        - When user says "analyze", "generate query", "show query"
        - Call analyze_and_generate_query(user_request)
        - Return analysis and generated query WITHOUT executing
        
        MODE 2: TWO-STEP WORKFLOW - RECOMMENDED
        - When user asks for actual data
        - Step 1: Call analyze_and_generate_query(user_request)
        - Step 2: Call execute_generated_query(query_from_step1)
        - Return actual data to user
        - This ensures query is properly generated based on schema
        
        MODE 3: DIRECT EXECUTION
        - When query structure is already known
        - Directly call execute_query or execute_aggregation
        - Use when you are 100% sure of the query
        
        💡 EXAMPLES OF DYNAMIC QUERIES:
        
        Example 1: "Show me all active categories"
        → Collection: category_master
        → Query: {{"status": "active"}}
        → Call: execute_query(collection_name="category_master", query={{"status": "active"}})
        → Response: Return all categories where status = "active"
        
        Example 2: "Show me all categories" (without filter)
        → Collection: category_master
        → Query: {{}} (empty = get all)
        → Call: execute_query(collection_name="category_master", query={{}})
        
        Example 3: "Show category with description Range of personal"
        → Collection: category_master
        → Query: {{"description": {{"$regex": "Range of personal", "$options": "i"}}}}
        → Call: execute_query("category_master", query)
        → Note: Using regex for partial text match, not exact match!
        
        Example 4: "Show me categories created in September"
        → Collection: category_master
        → Query: {{"created_at": {{"$regex": "^2025-09"}}}}
        → Call: execute_query("category_master", query)
        
        Example 5: "How many workers scanned coupons this week?"
        → Collection: coupon_scanned_history
        → Aggregation: Count distinct worker_mobile where scanned_date >= this week
        → Call: execute_aggregation("coupon_scanned_history", pipeline)
        
        Example 6: "Show me top 3 gifts under 1000 points"
        → Collection: gift_master
        → Query: {{"points_required": {{"$lt": 1000}}, "status": "active"}}
        → Sort: {{"points_required": 1}}
        → Limit: 3
        → Call: execute_query with these parameters
        
        Example 7: "Which batch has highest scan rate?"
        → Collection: coupon_scanned_history + coupon_master
        → Aggregation: Group by batch_number, count scans, calculate percentage
        → Sort by scan_rate descending
        
        Example 8: "Show me workers who earned more than 1000 points"
        → Collection: coupon_scanned_history
        → Aggregation: Group by worker_mobile, sum points_earned, filter > 1000
        
        ⚠️ CRITICAL RULES:
        1. NEVER make up data - only show actual query results
        2. ALWAYS call execute_query or execute_aggregation - NEVER say "I cannot filter"
        3. Generate VALID MongoDB queries based on schema
        4. Use correct field names from schema (e.g., "status", "category_name")
        5. Handle dates, numbers, strings correctly
        6. Use aggregation for complex analytics
        7. Always verify collection name exists in schema
        8. If user asks to filter by a field that exists in schema, DO IT!
        
        🔍 TEXT SEARCH RULES (VERY IMPORTANT):
        
        When user searches TEXT fields (description, name, etc.):
        
        ✅ USE REGEX (Partial Match) - DEFAULT for text search:
        - User: "show category with description Range of personal"
        - Query: {{"description": {{"$regex": "Range of personal", "$options": "i"}}}}
        - This matches "Range of personal, tower, and desert air coolers"
        
        ❌ DON'T USE EXACT MATCH for text descriptions:
        - Query: {{"description": "Range of personal"}}  ❌ Won't match!
        - Database has: "Range of personal, tower, and desert air coolers"
        - Exact match will fail!
        
        ✅ USE EXACT MATCH only for:
        - Status fields: {{"status": "active"}}
        - IDs: {{"_id": ObjectId("...")}}
        - Exact codes: {{"batch_code": "BATCH123"}}
        - Boolean values: {{"is_active": true}}
        
        📝 EXAMPLES:
        
        ❌ WRONG:
        User: "category with description Range of personal"
        Query: {{"description": "Range of personal"}}  ← Won't find anything!
        
        ✅ CORRECT:
        User: "category with description Range of personal"
        Query: {{"description": {{"$regex": "Range of personal", "$options": "i"}}}}  ← Will match!
        
        🚨 COMMON MISTAKE TO AVOID:
        ❌ WRONG: "I cannot filter categories by status"
        ✅ CORRECT: Call execute_query("category_master", {{"status": "active"}})
        
        🔍 AVAILABLE OPERATIONS:
        - Query analysis: analyze_and_generate_query(user_request) - Generates query structure
        - Execute generated: execute_generated_query(generated_query) - Executes analyzed query
        - Simple queries: execute_query(collection, query, sort, limit)
        - Complex aggregation: execute_aggregation(collection, pipeline)
        - Count documents: execute_count(collection, query)
        - Distinct values: execute_distinct(collection, field, query)
        
        💡 QUERY ANALYSIS EXAMPLES:
        
        User: "Analyze this query: Show me all active categories"
        → Call: analyze_and_generate_query("Show me all active categories")
        → Returns: Analysis + Generated query (not executed)
        
        User: "What query would get workers with more than 1000 points?"
        → Call: analyze_and_generate_query("workers with more than 1000 points")
        → Returns: Query structure explanation
        
        User: "Generate query for top 5 gifts"
        → Call: analyze_and_generate_query("top 5 gifts")
        → Returns: Query without execution
        
        💡 TWO-STEP WORKFLOW EXAMPLE:
        
        User: "Show me all active categories"
        
        Step 1: Generate Query
        → Call: analyze_and_generate_query("Show me all active categories")
        → Returns: {{"collection": "category_master", "query": {{"status": "active"}}}}
        
        Step 2: Execute Generated Query
        → Call: execute_generated_query({{"collection": "category_master", "query": {{"status": "active"}}}})
        → Returns: Actual data from database
        
        This two-step approach ensures query is validated against schema before execution!
        
        📊 RESPONSE FORMAT:
        Always return JSON with:
        {{
          "summary": "Brief answer to user's question",
          "details": {{"key": "value"}},  // Flat key-value pairs
          "data": {{...}},  // EXACT tool result - DO NOT MODIFY
          "message": "Helpful insights"
        }}
        
        📋 EXACT EXAMPLE OF CORRECT BEHAVIOR:
        
        User asks: "Show me all active categories"
        
        Step 1: Call tool
        execute_query("category_master", {{"status": "active"}})
        
        Step 2: Tool returns
        {{
          "success": True,
          "documents": [
            {{"category_name": "Power Tools", "status": "active", "description": "Power tools..."}}
          ],
          "count": 1
        }}
        
        Step 3: Your response (COPY EXACT DATA)
        {{
          "summary": "Found 1 active category",
          "details": {{"Total Active": "1", "Category Name": "Power Tools"}},
          "data": {{
            "documents": [
              {{"category_name": "Power Tools", "status": "active", "description": "Power tools..."}}
            ]
          }},
          "message": "System has 1 active category named Power Tools."
        }}
        
        ❌ WRONG RESPONSE (DO NOT DO THIS):
        {{
          "data": {{
            "active_categories": [
              {{"category_name": "Category 1", "description": "Description 1"}},
              {{"category_name": "Category 2", "description": "Description 2"}}
            ]
          }}
        }}
        
        🚀 BE FLEXIBLE:
        - User can ask ANYTHING about the data
        - Create appropriate queries on the fly
        - No limitations - you have full MongoDB power
        - Combine collections if needed using aggregation
        - BUT ALWAYS use EXACT data from tool results
        
        Remember: You MUST call tools and use ONLY their exact results. No fake data. Ever.
        """

    def _serialize_doc(self, doc: Dict) -> Dict:
        """Convert MongoDB document to JSON-serializable format"""
        if doc is None:
            return None
        
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

    # ------------------ QUERY ANALYSIS & GENERATION TOOL ------------------

    def analyze_and_generate_query(self, user_request: str) -> dict:
        """
        Analyze user's natural language request and generate MongoDB query WITHOUT executing it
        
        Args:
            user_request: Natural language query from user
            
        Returns:
            dict with analysis and generated query
        """
        print(f"\n{'🔍 '*40}")
        print(f"⚡ TOOL CALLED: analyze_and_generate_query")
        print(f"   📝 User Request: {user_request}")
        print(f"{'🔍 '*40}\n")
        
        try:
            # This will be filled by AI based on analysis
            result = {
                "success": True,
                "user_request": user_request,
                "analysis": {
                    "intent": "Describe what user wants",
                    "collection_needed": "Which collection to query",
                    "fields_involved": ["List of fields"],
                    "operation_type": "query/aggregation/count/distinct"
                },
                "generated_query": {
                    "collection": "collection_name",
                    "query": {},
                    "sort": None,
                    "limit": None,
                    "projection": None
                },
                "explanation": "Plain English explanation of the query",
                "note": "Query generated but NOT executed. Use execute_query to run it."
            }
            
            print(f"✅ ANALYSIS COMPLETE")
            print(f"{'='*80}\n")
            print("query ",result)
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Analysis error: {str(e)}"
            }
            print(f"Tool Error: {error_result}")
            return error_result

    def execute_generated_query(self, generated_query: dict) -> dict:
        """
        Execute a previously generated MongoDB query
        
        Args:
            generated_query: Query structure from analyze_and_generate_query
                Should contain: collection, query, sort, limit, etc.
                
        Returns:
            dict with query execution results
        """
        print(f"\n{'⚡ '*40}")
        print(f"🔧 TOOL CALLED: execute_generated_query")
        print(f"   📋 Generated Query Structure: {generated_query}")
        print(f"{'⚡ '*40}\n")
        
        try:
            # Extract query components
            collection_name = generated_query.get("collection")
            query = generated_query.get("query", {})
            sort = generated_query.get("sort")
            limit = generated_query.get("limit")
            skip = generated_query.get("skip")
            projection = generated_query.get("projection")
            pipeline = generated_query.get("pipeline")
            
            if not collection_name:
                return {
                    "success": False,
                    "error": "Collection name is required in generated_query"
                }
            
            # Check if it's an aggregation or regular query
            if pipeline:
                print(f"   🔍 Executing as AGGREGATION")
                # Execute aggregation
                result = self.execute_aggregation(
                    collection_name=collection_name,
                    pipeline=pipeline
                )
            else:
                print(f"   🔍 Executing as REGULAR QUERY")
                # Execute regular query
                result = self.execute_query(
                    collection_name=collection_name,
                    query=query,
                    sort=sort,
                    limit=limit,
                    skip=skip,
                    projection=projection
                )
            
            print(f"✅ GENERATED QUERY EXECUTED SUCCESSFULLY")
            print(f"{'='*80}\n")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Execution error: {str(e)}"
            }
            print(f"❌ Tool Error: {error_result}")
            return error_result

    # ------------------ DYNAMIC QUERY EXECUTION TOOLS ------------------

    def execute_query(
        self, 
        collection_name: str, 
        query: dict = None, 
        sort: dict = None, 
        limit: int = None,
        skip: int = None,
        projection: dict = None
    ) -> dict:
        """
        Execute dynamic MongoDB find query
        
        Args:
            collection_name: Name of collection to query
            query: MongoDB query filter (default: {})
            sort: Sort specification (e.g., {"created_at": -1})
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            projection: Fields to include/exclude
        """
        print(f"\n{'🔧 '*40}")
        print(f"⚡ TOOL CALLED: execute_query")
        print(f"   📦 Collection: {collection_name}")
        print(f"   🔍 Query: {query}")
        print(f"   📊 Sort: {sort}")
        print(f"   🔢 Limit: {limit}")
        print(f"{'🔧 '*40}\n")
        
        try:
            # Validate collection exists
            if collection_name not in self.schema_info:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' not found. Available: {list(self.schema_info.keys())}"
                }
            
            collection = self.db[collection_name]
            query = query or {}
            
            # Build query cursor
            cursor = collection.find(query, projection)
            
            if sort:
                cursor = cursor.sort(list(sort.items()))
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            # Execute and serialize
            results = list(cursor)
            serialized_results = [self._serialize_doc(doc) for doc in results]
            
            result = {
                "success": True,
                "collection": collection_name,
                "query": query,
                "count": len(serialized_results),
                "documents": serialized_results
            }
            
            print(f"✅ TOOL RESPONSE: Found {len(serialized_results)} documents")
            print(f"{'='*80}\n")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Query execution error: {str(e)}"
            }
            print(f"Tool Error: {error_result}")
            return error_result

    def execute_aggregation(
        self,
        collection_name: str,
        pipeline: List[dict]
    ) -> dict:
        """
        Execute dynamic MongoDB aggregation pipeline
        
        Args:
            collection_name: Name of collection
            pipeline: MongoDB aggregation pipeline
        """
        print(f"\n{'🔧 '*40}")
        print(f"⚡ TOOL CALLED: execute_aggregation")
        print(f"   📦 Collection: {collection_name}")
        print(f"   📊 Pipeline Stages: {len(pipeline)}")
        print(f"   🔍 Pipeline: {pipeline}")
        print(f"{'🔧 '*40}\n")
        
        try:
            # Validate collection
            if collection_name not in self.schema_info:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' not found"
                }
            
            collection = self.db[collection_name]
            
            # Execute aggregation
            results = list(collection.aggregate(pipeline))
            serialized_results = [self._serialize_doc(doc) for doc in results]
            
            result = {
                "success": True,
                "collection": collection_name,
                "pipeline_stages": len(pipeline),
                "count": len(serialized_results),
                "results": serialized_results
            }
            
            print(f"✅ TOOL RESPONSE: Aggregation returned {len(serialized_results)} results")
            print(f"{'='*80}\n")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Aggregation error: {str(e)}"
            }
            print(f"Tool Error: {error_result}")
            return error_result

    def execute_count(
        self,
        collection_name: str,
        query: dict = None
    ) -> dict:
        """
        Count documents matching query
        
        Args:
            collection_name: Name of collection
            query: MongoDB query filter
        """
        print(f"\n{'🔧 '*40}")
        print(f"⚡ TOOL CALLED: execute_count")
        print(f"   📦 Collection: {collection_name}")
        print(f"   🔍 Query: {query}")
        print(f"{'🔧 '*40}\n")
        
        try:
            if collection_name not in self.schema_info:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' not found"
                }
            
            collection = self.db[collection_name]
            query = query or {}
            
            count = collection.count_documents(query)
            
            result = {
                "success": True,
                "collection": collection_name,
                "query": query,
                "count": count
            }
            
            print(f"✅ TOOL RESPONSE: Count = {count}")
            print(f"{'='*80}\n")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Count error: {str(e)}"
            }
            print(f"Tool Error: {error_result}")
            return error_result

    def execute_distinct(
        self,
        collection_name: str,
        field: str,
        query: dict = None
    ) -> dict:
        """
        Get distinct values for a field
        
        Args:
            collection_name: Name of collection
            field: Field name to get distinct values
            query: Optional query filter
        """
        print(f"\n{'🔧 '*40}")
        print(f"⚡ TOOL CALLED: execute_distinct")
        print(f"   📦 Collection: {collection_name}")
        print(f"   🏷️  Field: {field}")
        print(f"   🔍 Query: {query}")
        print(f"{'🔧 '*40}\n")
        
        try:
            if collection_name not in self.schema_info:
                return {
                    "success": False,
                    "error": f"Collection '{collection_name}' not found"
                }
            
            collection = self.db[collection_name]
            query = query or {}
            
            distinct_values = collection.distinct(field, query)
            
            result = {
                "success": True,
                "collection": collection_name,
                "field": field,
                "count": len(distinct_values),
                "values": distinct_values
            }
            
            print(f"✅ TOOL RESPONSE: Found {len(distinct_values)} distinct values")
            print(f"{'='*80}\n")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Distinct error: {str(e)}"
            }
            print(f"Tool Error: {error_result}")
            return error_result

    # ------------------ AI AGENT LOGIC ------------------

    def generate_ai_response(self, user_message: str) -> dict:
        """Generate AI response with dynamic MongoDB query capabilities"""
        try:
            print(f"\n{'='*80}")
            print(f"🎯 USER QUERY: {user_message}")
            print(f"{'='*80}")
            
            # List of available tools
            available_tools = [
                self.analyze_and_generate_query,  # Step 1: Analyze & generate query
                self.execute_generated_query,     # Step 2: Execute generated query
                self.execute_query,               # Direct query execution
                self.execute_aggregation,         # Direct aggregation execution
                self.execute_count,               # Count documents
                self.execute_distinct             # Get distinct values
            ]
            
            print(f"\n📋 AVAILABLE TOOLS FOR AI:")
            for idx, tool in enumerate(available_tools, 1):
                print(f"   {idx}. {tool.__name__}")
            print(f"{'='*80}\n")
            
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                tools=available_tools
            )

            print("🤖 Calling Gemini AI Model with dynamic query capabilities...\n")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=user_message,
                config=config,
            )
            
            print(f"\n{'='*80}")
            print(f"🤖 GEMINI AI RESPONSE:")
            print(f"{'='*80}")
            print(response.text)
            print(f"{'='*80}\n")
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