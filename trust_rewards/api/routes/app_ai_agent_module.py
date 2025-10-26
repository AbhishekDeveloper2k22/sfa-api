from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.app_ai_agent_services import TrustRewardsAIAgentService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
from trust_rewards.schemas.ai_agent_schema import GenerateRequest, GenerateResponse
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

router = APIRouter()

# Helper functions for parsing AI responses
def _parse_ai_response(ai_response_text: str) -> dict:
    """
    Parse AI response and convert it to a frontend-friendly format
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
            # Format for chatbot UI
            details = parsed.get("details", {})
            data = parsed.get("data", {})
            
            # Create chatbot-friendly message
            chatbot_message = parsed.get("summary", "")
            
            # Add details as bullet points if available
            if details:
                chatbot_message += "\n\n📊 **Key Information:**\n"
                for key, value in details.items():
                    chatbot_message += f"• **{key}**: {value}\n"
            
            # Add helpful message at the end
            if parsed.get("message"):
                chatbot_message += f"\n💡 {parsed.get('message')}"
            
            return {
                "type": "structured",
                "message": chatbot_message,
                "details": details,
                "data": data if data else None
            }
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If not JSON or doesn't have expected structure, format as text
    return {
        "type": "text",
        "message": ai_response_text,
        "details": None,
        "data": None
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
    Generate AI response using Google Gemini with Trust Rewards integration
    - **message**: User's natural language query about rewards, coupons, gifts, etc.
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
        
        service = TrustRewardsAIAgentService()
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
    """Health check endpoint"""
    return format_response(
        success=True,
        msg="Trust Rewards AI Agent service is healthy",
        statuscode=200,
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Trust Rewards AI Agent"
        }
    )

@router.get("/tools")
async def get_available_tools():
    """Get list of available AI tools"""
    tools = [
        {"name": "get_categories", "description": "Get all product categories (Power Tools, etc.)", "category": "Catalog"},
        {"name": "get_category_by_name", "description": "Search for a specific category by name", "category": "Catalog"},
        {"name": "get_coupon_batches", "description": "Get all coupon batches with details", "category": "Coupons"},
        {"name": "get_coupon_batch_details", "description": "Get detailed information about a specific batch", "category": "Coupons"},
        {"name": "get_scanned_coupons", "description": "Get coupon scanning history with filters", "category": "Coupons"},
        {"name": "get_worker_points", "description": "Calculate total points earned by a worker", "category": "Workers"},
        {"name": "get_available_gifts", "description": "Get all available gifts for redemption", "category": "Gifts"},
        {"name": "get_gift_details", "description": "Get detailed information about a specific gift", "category": "Gifts"},
        {"name": "get_coupon_analytics", "description": "Get overall coupon usage analytics", "category": "Analytics"}
    ]
    return format_response(
        success=True, 
        msg="Available tools retrieved successfully", 
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
    Call a specific Trust Rewards tool directly
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
        
        service = TrustRewardsAIAgentService()
        
        # Map tool names to service methods
        tool_methods = {
            "get_categories": service.get_categories,
            "get_category_by_name": service.get_category_by_name,
            "get_coupon_batches": service.get_coupon_batches,
            "get_coupon_batch_details": service.get_coupon_batch_details,
            "get_scanned_coupons": service.get_scanned_coupons,
            "get_worker_points": service.get_worker_points,
            "get_available_gifts": service.get_available_gifts,
            "get_gift_details": service.get_gift_details,
            "get_coupon_analytics": service.get_coupon_analytics
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

# Debug endpoints for testing
@router.get("/debug/categories")
async def debug_categories(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to directly test category fetching"""
    try:
        service = TrustRewardsAIAgentService()
        result = service.get_categories()
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

@router.get("/debug/worker-points/{mobile}")
async def debug_worker_points(mobile: str, current_user: dict = Depends(get_current_user)):
    """Debug endpoint to test worker points calculation"""
    try:
        service = TrustRewardsAIAgentService()
        result = service.get_worker_points(mobile)
        return format_response(
            success=True,
            msg="Worker points fetched successfully",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Failed to fetch worker points",
            statuscode=500,
            data={"error": str(e)}
        )

@router.get("/debug/analytics")
async def debug_analytics(current_user: dict = Depends(get_current_user)):
    """Debug endpoint to test coupon analytics"""
    try:
        service = TrustRewardsAIAgentService()
        result = service.get_coupon_analytics()
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
