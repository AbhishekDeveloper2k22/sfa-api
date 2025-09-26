from fastapi import APIRouter, Request, Response, HTTPException
from sfa.services.web_user_service import users_tool
from sfa.database import client1
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
        
    def users_data(self, request_data):
        processor = users_tool()
        if request_data['type'] == "Office":
            query = {"user_type":4}
        if request_data['type'] == "Market":
            query = {"user_type":5}
        if request_data['type'] == "":
            query = {}
        result = processor.users_data(query)
        return result
