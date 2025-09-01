from fastapi import APIRouter, Request, HTTPException, Depends
from sfa.services.app_user_auth_services import AppUserAuthService
from sfa.utils.response import format_response
from datetime import datetime

router = APIRouter()

# JWT Configuration
import os

def verify_token(token: str):
    """Verify JWT token using service layer"""
    try:
        service = AppUserAuthService()
        return service.verify_token(token)
    except Exception:
        return None

async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload

@router.post("/login")
async def sfa_mobile_login(request: Request):
    """SFA mobile app login endpoint - supports both employees and sales users"""
    try:
        body = await request.json()
        employee_id = body.get("employeeId")
        password = body.get("password")
        device_info = body.get("deviceInfo", {})
        remember_me = body.get("rememberMe", False)
        
        # Validation
        if not employee_id or not password:
            return format_response(
                success=False,
                msg="User ID and password are required.",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "User ID (Employee ID/Email/Mobile) and password are required"
                    }
                }
            )
        
        # Validate employee ID length
        if len(employee_id) < 3 or len(employee_id) > 50:
            return format_response(
                success=False,
                msg="Validation failed",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "User ID must be between 3 and 50 characters"
                    }
                }
            )
        
        # Validate password length
        if len(password) < 6 or len(password) > 100:
            return format_response(
                success=False,
                msg="Validation failed",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "Password must be between 6 and 100 characters"
                    }
                }
            )
        
        service = AppUserAuthService()
        result = service.login(employee_id, password, device_info, remember_me)
        
        if not result:
            return format_response(
                success=False,
                msg="Invalid User ID or Password",
                statuscode=401,
                data={
                    "error": {
                        "code": "INVALID_CREDENTIALS",
                        "details": "The provided User ID or password is incorrect"
                    }
                }
            )
        
        # Check for error in result
        if result and result.get("error"):
            error_data = result.get("error", {})
            return format_response(
                success=False,
                msg=error_data.get("details", "Login failed"),
                statuscode=401,
                data={"error": error_data}
            )
        
        # Add timestamp to response
        result["timestamp"] = datetime.utcnow().isoformat()
        
        return format_response(
            success=True,
            msg="Login successful",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": "An unexpected error occurred"
                }
            }
        )





@router.post("/logout")
async def app_logout(current_user: dict = Depends(get_current_user)):
    """Mobile app logout endpoint"""
    try:
        # In a real implementation, you might want to blacklist the token
        return format_response(
            success=True,
            msg="Logout successful",
            statuscode=200,
            data={"message": "Successfully logged out"}
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"message": str(e)}
        )

@router.get("/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    try:
        service = AppUserAuthService()
        user_profile = service.get_user_profile(current_user.get("sub"))
        
        if not user_profile:
            return format_response(
                success=False,
                msg="User profile not found",
                statuscode=404,
                data={"user": None, "message": "User profile not found"}
            )
        
        return format_response(
            success=True,
            msg="Profile retrieved successfully",
            statuscode=200,
            data={"user": user_profile}
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"user": None, "message": str(e)}
        )

@router.put("/profile-update")
async def update_user_profile(request: Request, current_user: dict = Depends(get_current_user)):
    """Update current user profile"""
    try:
        body = await request.json()
        service = AppUserAuthService()
        result = service.update_user_profile(current_user.get("sub"), body)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Profile update failed"),
                statuscode=400,
                data={"user": None, "message": result.get("message", "Profile update failed")}
            )
        
        return format_response(
            success=True,
            msg="Profile updated successfully",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"user": None, "message": str(e)}
        )

@router.post("/change-password")
async def change_password(request: Request, current_user: dict = Depends(get_current_user)):
    """Change user password"""
    try:
        body = await request.json()
        current_password = body.get("current_password")
        new_password = body.get("new_password")
        
        if not current_password or not new_password:
            return format_response(
                success=False,
                msg="Current password and new password are required.",
                statuscode=400,
                data={"message": "Current password and new password are required."}
            )
        
        service = AppUserAuthService()
        result = service.change_password(current_user.get("sub"), current_password, new_password)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Password change failed"),
                statuscode=400,
                data={"message": result.get("message", "Password change failed")}
            )
        
        return format_response(
            success=True,
            msg="Password changed successfully",
            statuscode=200,
            data={"message": "Password changed successfully"}
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/forgot-password")
async def forgot_password(request: Request):
    """Forgot password endpoint"""
    try:
        body = await request.json()
        email = body.get("email")
        
        if not email:
            return format_response(
                success=False,
                msg="Email is required.",
                statuscode=400,
                data={"message": "Email is required."}
            )
        
        service = AppUserAuthService()
        result = service.forgot_password(email)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Password reset failed"),
                statuscode=400,
                data={"message": result.get("message", "Password reset failed")}
            )
        
        return format_response(
            success=True,
            msg="Password reset email sent",
            statuscode=200,
            data={"message": "Password reset email sent successfully"}
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/reset-password")
async def reset_password(request: Request):
    """Reset password with token"""
    try:
        body = await request.json()
        token = body.get("token")
        new_password = body.get("new_password")
        
        if not token or not new_password:
            return format_response(
                success=False,
                msg="Token and new password are required.",
                statuscode=400,
                data={"message": "Token and new password are required."}
            )
        
        service = AppUserAuthService()
        result = service.reset_password(token, new_password)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Password reset failed"),
                statuscode=400,
                data={"message": result.get("message", "Password reset failed")}
            )
        
        return format_response(
            success=True,
            msg="Password reset successfully",
            statuscode=200,
            data={"message": "Password reset successfully"}
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"message": str(e)}
        )

@router.post("/refresh-token")
async def refresh_token(request: Request):
    """Refresh access token"""
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        
        if not refresh_token:
            return format_response(
                success=False,
                msg="Refresh token is required.",
                statuscode=400,
                data={"message": "Refresh token is required."}
            )
        
        service = AppUserAuthService()
        
        # Verify refresh token
        payload = service.verify_token(refresh_token)
        if payload is None:
            return format_response(
                success=False,
                msg="Invalid refresh token",
                statuscode=401,
                data={"message": "Invalid refresh token"}
            )
        
        # Create new access token using service
        user_data = {
            "sub": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "employee_id": payload.get("employee_id"),
            "full_name": payload.get("full_name", ""),
            "role": payload.get("role", "Employee")
        }
        
        access_token = service.create_access_token(user_data)
        
        return format_response(
            success=True,
            msg="Token refreshed successfully",
            statuscode=200,
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 30 * 60  # 30 minutes in seconds
            }
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"message": str(e)}
        )

@router.get("/verify-token")
async def verify_access_token(current_user: dict = Depends(get_current_user)):
    """Verify if the current token is valid"""
    try:
        return format_response(
            success=True,
            msg="Token is valid",
            statuscode=200,
            data={"user": current_user, "message": "Token is valid"}
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Invalid token",
            statuscode=401,
            data={"message": str(e)}
        ) 