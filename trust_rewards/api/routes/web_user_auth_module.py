from fastapi import APIRouter, Request
from trust_rewards.services.user_auth_services import UserAuthService
from trust_rewards.utils.response import format_response

router = APIRouter()

@router.post("/login")
async def login(request: Request):
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        if not email or not password:
            return format_response(
                success=False,
                msg="Email and password are required.",
                statuscode=400,
                data={"user": None, "message": "Email and password are required."}
            )
        print("email",email)
        print("password",password)
        service = UserAuthService()
        result = service.login(email, password)
        if not result:
            return format_response(
                success=False,
                msg="Invalid email or password.",
                statuscode=401,
                data={"user": None, "message": "Invalid email or password."}
            )
        return format_response(
            success=True,
            msg="Login successful",
            statuscode=200,
            data=result
        )
    except Exception as e:
        return format_response(
            success=False,
            msg="Something went wrong.",
            statuscode=500,
            data={"user": None, "message": "Something went wrong."}
        ) 