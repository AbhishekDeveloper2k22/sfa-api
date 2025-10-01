from sfa.database import client1


class followup_tool:
    def __init__(self):
        self.main_database = client1['field_squad']
        self.followup_collection = self.main_database['followup']

    def followup_list(self, request_data: dict):
        try:
            # Pagination parameters
            limit = int(request_data.get('limit', 10))
            page = int(request_data.get('page', 1))
            skip = (page - 1) * limit

            # Build filter query
            filter_query = {}
            
            # Add filters if provided
            if request_data.get('status'):
                filter_query['status'] = request_data['status']
            
            if request_data.get('employee_id'):
                filter_query['employee_id'] = request_data['employee_id']
            
            if request_data.get('customer_id'):
                filter_query['customer_id'] = request_data['customer_id']
            
            if request_data.get('followup_type'):
                filter_query['followup_type'] = request_data['followup_type']
            
            if request_data.get('priority'):
                filter_query['priority'] = request_data['priority']
            
            if request_data.get('followup_date'):
                filter_query['followup_date'] = request_data['followup_date']
            
            # Add soft delete filter
            filter_query['del'] = 0

            # Get total count
            total_count = self.followup_collection.count_documents(filter_query)
            
            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Fetch data with pagination
            followups = list(self.followup_collection.find(filter_query)
                            .skip(skip)
                            .limit(limit)
                            .sort('created_at', -1))

            # Convert ObjectId to string
            for followup in followups:
                if '_id' in followup:
                    followup['_id'] = str(followup['_id'])
                if 'id' in followup:
                    followup['id'] = str(followup['id'])

            return {
                "success": True,
                "message": "Followups fetched successfully",
                "data": followups,
                "pagination": {
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "current_page": page,
                    "limit": limit,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching followups: {str(e)}",
                "data": []
            }

    def followup_details(self, request_data: dict):
        try:
            followup_id = request_data.get('id') or request_data.get('_id')
            
            if not followup_id:
                return {
                    "success": False,
                    "message": "Followup ID is required",
                    "data": None
                }

            # Find followup by ID
            followup = self.followup_collection.find_one({
                "$or": [
                    {"_id": followup_id},
                    {"id": followup_id}
                ],
                "del": 0
            })

            if not followup:
                return {
                    "success": False,
                    "message": "Followup not found",
                    "data": None
                }

            # Convert ObjectId to string
            if '_id' in followup:
                followup['_id'] = str(followup['_id'])
            if 'id' in followup:
                followup['id'] = str(followup['id'])

            return {
                "success": True,
                "message": "Followup details fetched successfully",
                "data": followup
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching followup details: {str(e)}",
                "data": None
            }
