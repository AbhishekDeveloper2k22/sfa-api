from fastapi import APIRouter, Request, HTTPException, Depends
from trust_rewards.services.web_skilled_worker_services import SkilledWorkerService
from trust_rewards.services.web_transaction_ledger_services import TransactionLedgerService
from trust_rewards.utils.auth import get_current_user
from trust_rewards.utils.response import format_response
import traceback

router = APIRouter()

@router.post("/skilled_workers_list")
async def get_skilled_workers_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of skilled workers with optional filters"""
    try:
        request_data = await request.json()
        
        # Validate mandatory status filter
        filters = request_data.get('filters', {})
        status = filters.get('status')
        
        if not status:
            return format_response(
                success=False,
                msg="Status filter is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "filters.status is mandatory"
                    }
                }
            )
        
        # Validate status values
        valid_statuses = ['All', 'Active', 'Inactive', 'KYC Pending']
        if status not in valid_statuses:
            return format_response(
                success=False,
                msg="Invalid status value",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"Status must be one of: {', '.join(valid_statuses)}"
                    }
                }
            )
        
        service = SkilledWorkerService()
        result = service.get_skilled_workers_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get skilled workers list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Skilled workers list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/skilled_worker_details")
async def get_skilled_worker_details(request: Request, current_user: dict = Depends(get_current_user)):
    """Get details of a specific skilled worker"""
    try:
        request_data = await request.json()
        service = SkilledWorkerService()
        result = service.get_skilled_worker_details(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get worker details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Worker details retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/transaction_ledger_list")
async def get_transaction_ledger_list(request: Request, current_user: dict = Depends(get_current_user)):
    """Get paginated list of transaction ledger with optional filters"""
    try:
        request_data = await request.json()
        
        # Validate mandatory status filter
        filters = request_data.get('filters', {})
        status = filters.get('status')
        
        if not status:
            return format_response(
                success=False,
                msg="Status filter is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "filters.status is mandatory"
                    }
                }
            )
        
        # Validate status values
        valid_statuses = ['All', 'completed', 'pending', 'failed', 'cancelled']
        if status not in valid_statuses:
            return format_response(
                success=False,
                msg="Invalid status value",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"Status must be one of: {', '.join(valid_statuses)}"
                    }
                }
            )
        
        service = TransactionLedgerService()
        result = service.get_transaction_ledger_list(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get transaction ledger list"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Transaction ledger list retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/transaction_details")
async def get_transaction_details(request: Request, current_user: dict = Depends(get_current_user)):
    """Get details of a specific transaction"""
    try:
        request_data = await request.json()
        service = TransactionLedgerService()
        result = service.get_transaction_details(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get transaction details"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Transaction details retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/worker_transaction_history")
async def get_worker_transaction_history(request: Request, current_user: dict = Depends(get_current_user)):
    """Get transaction history for a specific worker"""
    try:
        request_data = await request.json()
        
        service = TransactionLedgerService()
        result = service.get_worker_transaction_history(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get worker transaction history"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Worker transaction history retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )

@router.post("/worker_redeem_history")
async def get_worker_redeem_history(request: Request, current_user: dict = Depends(get_current_user)):
    """Get redeem history for a specific worker"""
    try:
        request_data = await request.json()
        
        # Validate mandatory worker_id
        worker_id = request_data.get('_id')
        if not worker_id:
            return format_response(
                success=False,
                msg="Worker ID is required",
                statuscode=400,
                data={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "worker_id is mandatory"
                    }
                }
            )
        
        service = TransactionLedgerService()
        result = service.get_worker_redeem_history(request_data)
        
        if not result.get("success"):
            return format_response(
                success=False,
                msg=result.get("message", "Failed to get worker redeem history"),
                statuscode=400,
                data={"error": result.get("error", {})}
            )
        
        return format_response(
            success=True,
            msg="Worker redeem history retrieved successfully",
            statuscode=200,
            data=result.get("data", {})
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        return format_response(
            success=False,
            msg="Internal server error",
            statuscode=500,
            data={
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": tb
                }
            }
        )