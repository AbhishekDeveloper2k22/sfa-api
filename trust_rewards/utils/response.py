from typing import Any, Dict, Optional
from bson import ObjectId

def format_response(
    success: bool = True,
    msg: str = "Operation completed successfully",
    statuscode: int = 200,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format API response in a consistent structure.
    
    Args:
        success (bool): Whether the operation was successful
        msg (str): Message describing the operation result
        statuscode (int): HTTP status code
        data (Optional[Dict[str, Any]]): Additional data to include in response
        
    Returns:
        Dict[str, Any]: Formatted response dictionary
    """
    response = {
        "success": success,
        "msg": msg,
        "statuscode": statuscode,
    }
    
    if data is not None:
        response["data"] = data
        
    return response 

def convert_objectid_to_str(data):
    if isinstance(data, dict):
        return {k: convert_objectid_to_str(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data 

def extract_steps_from_user_data(user_data):
    steps = {}
    max_step = -1
    for k, v in user_data.items():
        if k.startswith("step") and k[4:].isdigit():
            steps[k] = v
            step_num = int(k[4:])
            if step_num > max_step:
                max_step = step_num
    if max_step >= 0:
        steps["lastCompletedStep"] = max_step
    return steps 