from fastapi import APIRouter, Request, Response, HTTPException
from sfa.middlewares.web_user_middelware import DataProcessor
import traceback

router = APIRouter()

@router.post("/all_types")
async def all_types(request: Request):
    request_data = await request.json()
    instanceClass = DataProcessor()
    try:
        result = instanceClass.all_types_info(request_data)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})

# @router.post("/add_user")
# async def data_visualization_chatbot_endpoint(request: Request):
#     request_data = await request.json()
#     instanceClass = DataProcessor()
#     try:
#         result = instanceClass.data_visualization_chatbot(request_data)
#         return result
#     except Exception as e:
#         tb = traceback.format_exc()
#         raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
    
# @router.post("/user_list")
# async def data_visualization_chatbot_endpoint(request: Request):
#     request_data = await request.json()
#     instanceClass = DataProcessor()
#     try:
#         result = instanceClass.data_visualization_chatbot(request_data)
#         return result
#     except Exception as e:
#         tb = traceback.format_exc()
#         raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
    
# @router.post("/user_details")
# async def data_visualization_chatbot_endpoint(request: Request):
#     request_data = await request.json()
#     instanceClass = DataProcessor()
#     try:
#         result = instanceClass.data_visualization_chatbot(request_data)
#         return result
#     except Exception as e:
#         tb = traceback.format_exc()
#         raise HTTPException(status_code=500, detail={"error": str(e), "traceback": tb})
