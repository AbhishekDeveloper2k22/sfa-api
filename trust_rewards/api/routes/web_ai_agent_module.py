from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.web_ai_agent_services import WebTrustRewardsAIAgentService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
from trust_rewards.schemas.ai_agent_schema import GenerateRequest, GenerateResponse
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

router = APIRouter()

# Helper function to detect fake data
def _detect_fake_data(data: dict) -> bool:
    """
    Detect if response contains fake/example data patterns
    Returns True if fake data detected, False otherwise
    """
    if not data:
        return False
    
    # Convert to string for pattern matching
    data_str = str(data).lower()
    
    # Fake data patterns to check
    fake_patterns = [
        "category 1", "category 2", "category 3",
        "description 1", "description 2", "description 3",
        "description of category",
        "worker 1", "worker 2",
        "batch 1", "batch 2",
        "gift 1", "gift 2",
        "example", "sample data",
        "placeholder"
    ]
    
    for pattern in fake_patterns:
        if pattern in data_str:
            print(f"⚠️ WARNING: Fake data pattern detected: '{pattern}'")
            return True
    
    return False

# Helper functions for parsing AI responses
def _parse_ai_response(ai_response_text: str) -> dict:
    """
    Parse AI response and convert it to UNIVERSAL CHATBOT FORMAT
    
    Returns a standardized format suitable for any chatbot UI:
    - response_type: Type of response (data, text, error)
    - message: Main conversational message to display
    - data: Structured data (if any)
    - metadata: Additional info (count, timestamp, etc.)
    """
    # Clean the response text - remove markdown code blocks
    cleaned_text = ai_response_text.strip()
    
    # Remove markdown code blocks if present
    if cleaned_text.startswith('```json'):
        cleaned_text = cleaned_text[7:]  # Remove ```json
    if cleaned_text.startswith('```'):
        cleaned_text = cleaned_text[3:]   # Remove ```
    if cleaned_text.endswith('```'):
        cleaned_text = cleaned_text[:-3]  # Remove trailing ```
    
    cleaned_text = cleaned_text.strip()
    
    try:
        # Try to parse as JSON first
        import json
        parsed = json.loads(cleaned_text)
        
        # If it's valid JSON with our expected structure
        if isinstance(parsed, dict):
            summary = parsed.get("summary", "")
            details = parsed.get("details", {})
            data = parsed.get("data", {})
            message = parsed.get("message", "")
            
            # Determine response type
            has_documents = data and "documents" in data and len(data.get("documents", [])) > 0
            response_type = "data" if has_documents else "text"
            
            # Build conversational message (what chatbot will say)
            conversation_parts = []
            if summary:
                conversation_parts.append(summary)
            if message:
                conversation_parts.append(message)
            
            conversation_message = " ".join(conversation_parts) if conversation_parts else "Here's what I found."
            
            # Extract actual data items
            items = []
            if has_documents:
                items = data.get("documents", [])
            
            # Build metadata
            metadata = {
                "count": len(items),
                "has_data": has_documents,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add details to metadata if available
            if details:
                metadata["details"] = details
            
            # Return UNIVERSAL FORMAT for chatbot
            return {
                "response_type": response_type,
                "message": conversation_message,
                "data": {
                    "items": items,
                    "count": len(items)
                } if has_documents else None,
                "metadata": metadata
            }
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If not JSON or doesn't have expected structure, format as text
    return {
        "response_type": "text",
        "message": ai_response_text,
        "data": None,
        "metadata": {
            "count": 0,
            "has_data": False,
            "timestamp": datetime.now().isoformat()
        }
    }

def _extract_summary(text: str) -> str:
    """Extract a summary from the AI response text"""
    # Look for common patterns in the text
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('*') and not line.startswith('-'):
            return line
    return text[:100] + "..." if len(text) > 100 else text

def _extract_details(text: str) -> dict:
    """Extract structured details from the AI response text"""
    details = {}
    
    # Look for markdown list items
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('*') or line.startswith('-'):
            # Parse markdown list items
            line = line.lstrip('* -').strip()
            if ':' in line:
                key, value = line.split(':', 1)
                details[key.strip()] = value.strip()
            else:
                details[f"detail_{len(details)}"] = line
    
    return details

@router.post("/generate", response_model=None)
async def generate(request_body: GenerateRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate AI response using Google Gemini with Trust Rewards Admin integration
    - **message**: Admin's natural language query about rewards management, analytics, etc.
    """
    try:
        user_message = request_body.message
        
        # Input validation
        if not user_message or len(user_message.strip()) == 0:
            return format_response(
                success=False, 
                msg="Message is required and cannot be empty", 
                statuscode=400, 
                data={"error": {"code": "MESSAGE_REQUIRED", "details": "Message cannot be empty"}}
            )
        
        if len(user_message) > 1000:
            return format_response(
                success=False, 
                msg="Message too long", 
                statuscode=400, 
                data={"error": {"code": "MESSAGE_TOO_LONG", "details": "Message cannot exceed 1000 characters"}}
            )
        
        service = WebTrustRewardsAIAgentService()
        result = service.generate_ai_response(user_message)
        
        if "error" in result:
            # Extract detailed error information
            error_details = {
                "code": "AI_GENERATION_FAILED",
                "details": result["error"],
                "full_error_response": result
            }
            
            return format_response(
                success=False, 
                msg="Failed to generate AI response", 
                statuscode=400, 
                data={"error": error_details}
            )
        
        # Try to parse the AI response as JSON for structured data
        ai_response_text = result.get("text", "")
        structured_response = _parse_ai_response(ai_response_text)
        
        # Validate for fake data
        if _detect_fake_data(structured_response):
            print("="*80)
            print("🚨 FAKE DATA DETECTED IN AI RESPONSE!")
            print("AI generated example/fake data instead of using real database results")
            print("Check console logs to see if tools were called")
            print("="*80)
        
        return format_response(
            success=True, 
            msg="AI response generated successfully", 
            statuscode=200, 
            data=structured_response
        )
        
    except Exception as e:
        return format_response(
            success=False, 
            msg="Internal server error", 
            statuscode=500, 
            data={"error": {"code": "SERVER_ERROR", "details": str(e)}}
        )

@router.get("/health")
async def health_check():
    """Health check endpoint for admin AI agent"""
    return format_response(
        success=True,
        msg="Trust Rewards Admin AI Agent service is healthy",
        statuscode=200,
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Trust Rewards Admin AI Agent"
        }
    )

@router.get("/tools")
async def get_available_tools():
    """Get list of available admin AI tools"""
    tools = [
        {"name": "get_categories", "description": "Get all product categories (including inactive)", "category": "Catalog Management"},
        {"name": "get_category_by_name", "description": "Search for a specific category by name", "category": "Catalog Management"},
        {"name": "get_coupon_batches", "description": "Get all coupon batches with analytics", "category": "Coupon Management"},
        {"name": "get_coupon_batch_details", "description": "Get comprehensive batch analytics", "category": "Coupon Management"},
        {"name": "get_scanned_coupons", "description": "Get detailed scanning history with filters", "category": "Coupon Tracking"},
        {"name": "get_worker_points", "description": "Calculate comprehensive worker performance", "category": "Worker Management"},
        {"name": "get_available_gifts", "description": "Get complete gift catalog with management details", "category": "Gift Management"},
        {"name": "get_gift_details", "description": "Get complete gift information", "category": "Gift Management"},
        {"name": "get_coupon_analytics", "description": "Get system-wide analytics and insights", "category": "Analytics"},
        {"name": "get_top_performing_workers", "description": "Get top workers by points or scans", "category": "Analytics"},
        {"name": "get_batch_performance_comparison", "description": "Compare performance across batches", "category": "Analytics"}
    ]
    return format_response(
        success=True, 
        msg="Available admin tools retrieved successfully", 
        statuscode=200, 
        data={"tools": tools}
    )

@router.post("/tool-call")
async def call_tool(
    tool_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Call a specific Trust Rewards admin tool directly
    - **tool_name**: Name of the tool to call
    - **parameters**: Optional parameters for the tool
    """
    try:
        if not tool_name:
            return format_response(
                success=False, 
                msg="Tool name is required", 
                statuscode=400, 
                data={"error": {"code": "TOOL_NAME_REQUIRED", "details": "Tool name cannot be empty"}}
            )
        
        service = WebTrustRewardsAIAgentService()
        
        # Map tool names to service methods (now using dynamic query methods)
        tool_methods = {
            "execute_query": service.execute_query,
            "execute_aggregation": service.execute_aggregation,
            "execute_count": service.execute_count,
            "execute_distinct": service.execute_distinct
        }
        
        if tool_name not in tool_methods:
            return format_response(
                success=False, 
                msg=f"Tool '{tool_name}' not found", 
                statuscode=400, 
                data={"error": {"code": "TOOL_NOT_FOUND", "details": f"Tool '{tool_name}' is not available"}}
            )
        
        # Call the tool method
        tool_method = tool_methods[tool_name]
        if parameters:
            result = tool_method(**parameters)
        else:
            result = tool_method()
        
        if "error" in result:
            return format_response(
                success=False, 
                msg=f"Tool execution failed: {result['error']}", 
                statuscode=400, 
                data={"error": {"code": "TOOL_EXECUTION_FAILED", "details": result['error']}}
            )
        
        return format_response(
            success=True, 
            msg=f"Tool '{tool_name}' executed successfully", 
            statuscode=200, 
            data={"tool_name": tool_name, "result": result}
        )
        
    except Exception as e:
        return format_response(
            success=False, 
            msg="Internal server error", 
            statuscode=500, 
            data={"error": {"code": "SERVER_ERROR", "details": str(e)}}
        )

# Admin-specific debug and management endpoints
@router.get("/debug/categories")
async def debug_categories(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to test category fetching with analytics"""
    try:
        service = WebTrustRewardsAIAgentService()
        result = service.execute_query(collection_name="category_master", query={})
        return format_response(
            success=True,
            msg="Categories fetched successfully",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Failed to fetch categories",
            statuscode=500,
            data={"error": str(e)}
        )

@router.get("/debug/batch-comparison")
async def debug_batch_comparison(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to test batch performance comparison"""
    try:
        service = WebTrustRewardsAIAgentService()
        result = service.execute_query(collection_name="coupon_master", query={})
        return format_response(
            success=True,
            msg="Batch comparison fetched successfully",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Failed to fetch batch comparison",
            statuscode=500,
            data={"error": str(e)}
        )

@router.get("/debug/top-workers")
async def debug_top_workers(
    limit: int = 10,
    metric: str = "points",
    current_user: dict = Depends(get_current_user)
):
    """Debug endpoint to test top workers leaderboard"""
    try:
        service = WebTrustRewardsAIAgentService()
        # Use aggregation to get top workers
        pipeline = [
            {"$group": {
                "_id": "$worker_mobile",
                "worker_name": {"$first": "$worker_name"},
                "total_points": {"$sum": "$points_earned"},
                "total_scans": {"$sum": 1}
            }},
            {"$sort": {"total_points" if metric == "points" else "total_scans": -1}},
            {"$limit": limit}
        ]
        result = service.execute_aggregation(collection_name="coupon_scanned_history", pipeline=pipeline)
        return format_response(
            success=True,
            msg="Top workers fetched successfully",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Failed to fetch top workers",
            statuscode=500,
            data={"error": str(e)}
        )

@router.get("/debug/analytics")
async def debug_analytics(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to test comprehensive analytics"""
    try:
        service = WebTrustRewardsAIAgentService()
        # Get count of all coupons
        result = service.execute_count(collection_name="coupon_code", query={})
        return format_response(
            success=True,
            msg="Analytics fetched successfully",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Failed to fetch analytics",
            statuscode=500,
            data={"error": str(e)}
        )

@router.get("/dashboard-summary")
async def dashboard_summary(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive dashboard summary for admin
    Combines multiple metrics into one response
    """
    try:
        service = WebTrustRewardsAIAgentService()
        
        # Get all key metrics using dynamic queries
        analytics = service.execute_count(collection_name="coupon_code", query={})
        batches = service.execute_query(collection_name="coupon_master", query={})
        categories = service.execute_query(collection_name="category_master", query={})
        gifts = service.execute_query(collection_name="gift_master", query={})
        top_workers_pipeline = [
            {"$group": {"_id": "$worker_mobile", "total_points": {"$sum": "$points_earned"}}},
            {"$sort": {"total_points": -1}},
            {"$limit": 5}
        ]
        top_workers = service.execute_aggregation(collection_name="coupon_scanned_history", pipeline=top_workers_pipeline)
        
        summary = {
            "overview": analytics.get("analytics", {}),
            "batch_summary": {
                "total_batches": batches.get("total_batches", 0),
                "total_coupons": batches.get("total_coupons", 0),
                "overall_scan_percentage": batches.get("overall_scan_percentage", 0)
            },
            "catalog_summary": {
                "total_categories": categories.get("total_count", 0),
                "active_categories": categories.get("active_count", 0),
                "total_gifts": gifts.get("total_count", 0),
                "active_gifts": gifts.get("active_count", 0)
            },
            "top_performers": top_workers.get("top_workers", [])
        }
        
        return format_response(
            success=True,
            msg="Dashboard summary fetched successfully",
            statuscode=200,
            data=summary
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Failed to fetch dashboard summary",
            statuscode=500,
            data={"error": str(e)}
        )
