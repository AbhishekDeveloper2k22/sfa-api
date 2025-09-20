from fastapi import APIRouter, Request, HTTPException, Depends, Query
from trust_rewards.services.app_ai_agent_services import AppAIAgentService
from trust_rewards.utils.response import format_response
from trust_rewards.schemas.ai_agent_schema import GenerateRequest, GenerateResponse
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# JWT Configuration
SECRET_KEY = os.getenv('JWT_SECRET')
ALGORITHM = "HS256"

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

async def get_current_user(request: Request):
    """Get current authenticated user"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload

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
            return {
                "type": "structured",
                "summary": parsed.get("summary", ""),
                "details": parsed.get("details", {}),
                "data": parsed.get("data", {}),
                "message": parsed.get("message", ""),
                "raw_response": ai_response_text
            }
    except (json.JSONDecodeError, ValueError):
        pass
    
    # If not JSON or doesn't have expected structure, format as text
    return {
        "type": "text",
        "summary": _extract_summary(ai_response_text),
        "details": _extract_details(ai_response_text),
        "message": ai_response_text,
        "raw_response": ai_response_text
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

@router.post("/generate")
async def generate(request: Request, request_body: GenerateRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate AI response using Google Gemini with HRMS integration
    - **message**: User's natural language query
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
        
        # Get authorization header from the request
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return format_response(
                success=False, 
                msg="Authorization header is required", 
                statuscode=401, 
                data={"error": {"code": "AUTH_HEADER_MISSING", "details": "Authorization header is required"}}
            )
        
        service = AppAIAgentService(authorization_header=auth_header)
        result = service.generate_ai_response(user_message)
        
        if "error" in result:
            # Extract detailed error information
            error_details = {
                "code": "AI_GENERATION_FAILED",
                "details": result["error"],
                "full_error_response": result
            }
            
            # If there are additional error details, include them
            if "url" in result:
                error_details["api_url"] = result["url"]
            if "method" in result:
                error_details["api_method"] = result["method"]
            if "status_code" in result:
                error_details["api_status_code"] = result["status_code"]
            if "response_text" in result:
                error_details["api_response"] = result["response_text"]
            
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
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return format_response(
        success=True,
        msg="AI Agent service is healthy",
        statuscode=200,
        data={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "AI Agent"
        }
    )

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with HRMS API connectivity test"""
    try:
        # Test HRMS API connectivity
        service = AppAIAgentService()
        
        # Test a simple API call
        test_result = service._make_api_request_with_retry(
            f"{service.base_url}/app/sidebar/upcoming-celebrations",
            method="GET",
            max_retries=1  # Quick test
        )
        
        if "error" in test_result:
            return format_response(
                success=False,
                msg="HRMS API connectivity issue detected",
                statuscode=503,
                data={
                    "status": "degraded",
                    "timestamp": datetime.now().isoformat(),
                    "service": "AI Agent",
                    "hrms_api_status": "unreachable",
                    "error_details": test_result,
                    "environment": {
                        "is_production": service.is_production,
                        "is_render": service.is_render,
                        "default_timeout": service.default_timeout,
                        "max_retries": service.max_retries
                    }
                }
            )
        
        return format_response(
            success=True,
            msg="All services are healthy",
            statuscode=200,
            data={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "AI Agent",
                "hrms_api_status": "reachable",
                "hrms_api_response_time": "normal",
                "environment": {
                    "is_production": service.is_production,
                    "is_render": service.is_render,
                    "default_timeout": service.default_timeout,
                    "max_retries": service.max_retries
                }
            }
        )
        
    except Exception as e:
        return format_response(
            success=False,
            msg="Health check failed",
            statuscode=500,
            data={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "service": "AI Agent",
                "error": str(e)
            }
        )

@router.get("/tools")
async def get_available_tools():
    """Get list of available AI tools"""
    tools = [
        {"name": "get_leave_balance", "description": "Get leave balance from HRMS system", "category": "HR"},
        {"name": "get_leave_types", "description": "Get available leave types from HRMS system", "category": "HR"},
        {"name": "get_attendance_list", "description": "Get attendance list from HRMS system", "category": "HR"},
        {"name": "get_dashboard_overview", "description": "Get comprehensive dashboard overview including attendance status, work progress, celebrations, and notifications", "category": "HR"},
        {"name": "get_request_list", "description": "Get list of all requests (leave, regularisation, wfh, compensatory off, expense) with details and summary counts", "category": "HR"},
        {"name": "get_upcoming_celebrations", "description": "Get upcoming celebrations (birthdays and work anniversaries) for the next 30 days", "category": "HR"},
        {"name": "get_employee_directory", "description": "Get comprehensive employee directory with profiles, contact details, employment info, and organizational structure", "category": "HR"},
        {"name": "get_user_profile", "description": "Get comprehensive user profile including personal info, employment details, salary, deductions, bank details, addresses, emergency contacts, documents, and government IDs", "category": "HR"}
    ]
    return format_response(
        success=True, 
        msg="Available tools retrieved successfully", 
        statuscode=200, 
        data={"tools": tools}
    )

@router.post("/tool-call")
async def call_tool(
    request: Request,
    tool_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Call a specific HRMS tool directly
    - **tool_name**: Name of the tool to call
    - **parameters**: Optional parameters for the tool
    """
    try:
        user_id = current_user.get("user_id")
        
        if not tool_name:
            return format_response(
                success=False, 
                msg="Tool name is required", 
                statuscode=400, 
                data={"error": {"code": "TOOL_NAME_REQUIRED", "details": "Tool name cannot be empty"}}
            )
        
        # Get authorization header from the request
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return format_response(
                success=False, 
                msg="Authorization header is required", 
                statuscode=401, 
                data={"error": {"code": "AUTH_HEADER_MISSING", "details": "Authorization header is required"}}
            )
        
        service = AppAIAgentService(authorization_header=auth_header)
        
        # Map tool names to service methods
        tool_methods = {
            "get_leave_balance": service.get_leave_balance,
            "get_leave_types": service.get_leave_types,
            "get_attendance_list": service.get_attendance_list,
            "get_dashboard_overview": service.get_dashboard_overview,
            "get_request_list": service.get_request_list,
            "get_upcoming_celebrations": service.get_upcoming_celebrations,
            "get_employee_directory": service.get_employee_directory,
            "get_user_profile": service.get_user_profile
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
            data={"error": {"code": "SERVER_ERROR", "details": "An unexpected error occurred"}}
        )

@router.get("/test-upcoming-celebrations")
async def test_upcoming_celebrations(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Test endpoint to directly test the upcoming celebrations API
    This will help debug what's happening with the API call
    """
    try:
        # Get authorization header from the request
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return format_response(
                success=False, 
                msg="Authorization header is required", 
                statuscode=401, 
                data={"error": {"code": "AUTH_HEADER_MISSING", "details": "Authorization header is required"}}
            )
        
        service = AppAIAgentService(authorization_header=auth_header)
        
        print("=== Testing Upcoming Celebrations API ===")
        result = service.get_upcoming_celebrations()
        print(f"=== Test Result: {result} ===")
        
        if "error" in result:
            return format_response(
                success=False, 
                msg="Upcoming celebrations API test failed", 
                statuscode=400, 
                data={"error": result}
            )
        
        return format_response(
            success=True, 
            msg="Upcoming celebrations API test successful", 
            statuscode=200, 
            data={"test_result": result}
        )
        
    except Exception as e:
        return format_response(
            success=False, 
            msg="Internal server error during test", 
            statuscode=500, 
            data={"error": {"code": "SERVER_ERROR", "details": str(e)}}
        )