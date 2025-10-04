from sfa.database import client1
from typing import Dict, Any, List
import traceback
import json
import pandas as pd


class AppCommonService:
    def __init__(self):
        self.client_database = client1['talbros']
        self.all_type = self.client_database["all_type"]

    def get_all_types(self, request_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Get all types data based on name parameter"""
        try:
            name = request_data.get('name')
            
            if not name:
                return {
                    "success": False,
                    "message": "name parameter is required",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": "name parameter is required in request body"
                    }
                }

            # Build query based on name parameter
            query = {}
            if name == "user":
                query = {"type": "user"}
            elif name == "lead":
                query = {"type": "lead"}
            elif name == "non-lead":
                query = {"type": "non-lead"}
            elif name == "allowance":
                query = {"customer_type": 0}
            elif name == "designation":
                customer_type = request_data.get('customer_type')
                if customer_type is not None:
                    query = {"customer_type": customer_type, "type": "designation"}
                else:
                    return {
                        "success": False,
                        "message": "customer_type is required for designation",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "details": "customer_type parameter is required when name is 'designation'"
                        }
                    }
            else:
                return {
                    "success": False,
                    "message": f"Invalid name parameter: {name}",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": f"name must be one of: user, lead, non-lead, allowance, designation"
                    }
                }

            # Query the database
            all_data = pd.DataFrame(list(self.all_type.find(query, {})))
            
            if all_data.empty:
                return {
                    "success": True,
                    "data": []
                }
            
            # Convert to JSON
            all_data_json = json.loads(
                all_data.to_json(orient="records", default_handler=str)
            )
            
            return {
                "success": True,
                "data": all_data_json
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get all types: {str(e)}",
                "error": {
                    "code": "SERVER_ERROR",
                    "details": str(e),
                    "traceback": traceback.format_exc()
                }
            }
