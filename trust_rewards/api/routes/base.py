from fastapi import APIRouter, Request
# from app.workers.prediction import prediction_models  # Adjust import path as needed

router = APIRouter()

# @router.get("/income")
# async def salary():
#     instanceClass = prediction_models()
#     try: 
#         result = instanceClass.income_predict()
#         return result
#     except Exception as e:
#         return {"msg": str(e), "statuscode": 500, "output": []}