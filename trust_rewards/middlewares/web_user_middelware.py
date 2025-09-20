from fastapi import APIRouter, Request, Response, HTTPException
from trust_rewards.services.web_user_service import users_tool
from trust_rewards.database import client1
import traceback

class DataProcessor:
    def all_types_info(self, request_data):
        processor = users_tool()
        if request_data['name'] == "user":
            query = {"type":"user"}
        if request_data['name'] == "lead":
            query = {"type":"lead"}
        if request_data['name'] == "non-lead":
            query = {"type":"non-lead"}
        if request_data['name'] == "allowance":
            query = {"customer_type":0}
        if request_data['name'] == "designation":
            query = {"customer_type":request_data['customer_type'],"type":"designation"}
        result = processor.users_types(query)
        return result
        
    def users_add(self, request_data):
        processor = users_tool()
        if request_data.get('_id') and request_data['_id'] != "":
            result = processor.update_users(request_data)
        else:
            result = processor.add_users(request_data)
        return result
    
    def check_user_exists(self, request_data):
        """
        Check if user already exists based on email, phone, or other unique fields
        """
        processor = users_tool()
        result = processor.check_user_exists(request_data)
        return result
    
    def users_list(self, request_data):
        """
        Get paginated list of users with count
        """
        processor = users_tool()
        result = processor.users_list(request_data)
        return result
    
    def user_details(self, request_data):
        """
        Get specific user details by ID
        """
        processor = users_tool()
        result = processor.user_details(request_data)
        return result
    
 