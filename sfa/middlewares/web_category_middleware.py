from fastapi import APIRouter, Request, Response, HTTPException
from sfa.services.web_category_service import category_tool
from sfa.database import client1
import traceback

class CategoryDataProcessor:
    def category_add(self, request_data):
        """
        Add new category or update existing category
        """
        processor = category_tool()
        if request_data.get('_id') and request_data['_id'] != "":
            result = processor.update_category(request_data)
        else:
            result = processor.add_category(request_data)
        return result
    
    def check_category_exists(self, request_data):
        """
        Check if category already exists based on name or code
        """
        processor = category_tool()
        result = processor.check_category_exists(request_data)
        return result
    
    def categories_list(self, request_data):
        """
        Get paginated list of categories with count
        """
        processor = category_tool()
        result = processor.categories_list(request_data)
        return result
    
    def category_details(self, request_data):
        """
        Get specific category details by ID
        """
        processor = category_tool()
        result = processor.category_details(request_data)
        return result
    