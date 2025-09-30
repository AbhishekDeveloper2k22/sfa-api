from sfa.database import client1


class beat_plan_tool:
    def __init__(self):
        self.main_database = client1['field_squad']
        self.beat_plan_collection = self.main_database['beat_plan']

    def beat_plan_list(self, request_data: dict):
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
            
            if request_data.get('beat_name'):
                filter_query['beat_name'] = {"$regex": request_data['beat_name'], "$options": "i"}
            
            if request_data.get('area'):
                filter_query['area'] = {"$regex": request_data['area'], "$options": "i"}
            
            # Add soft delete filter
            filter_query['del'] = 0

            # Get total count
            total_count = self.beat_plan_collection.count_documents(filter_query)
            
            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1

            # Fetch data with pagination
            beat_plans = list(self.beat_plan_collection.find(filter_query)
                            .skip(skip)
                            .limit(limit)
                            .sort('created_at', -1))

            # Convert ObjectId to string
            for beat_plan in beat_plans:
                if '_id' in beat_plan:
                    beat_plan['_id'] = str(beat_plan['_id'])
                if 'id' in beat_plan:
                    beat_plan['id'] = str(beat_plan['id'])

            return {
                "success": True,
                "message": "Beat plans fetched successfully",
                "data": beat_plans,
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
                "message": f"Error fetching beat plans: {str(e)}",
                "data": []
            }

    def beat_plan_details(self, request_data: dict):
        try:
            beat_plan_id = request_data.get('id') or request_data.get('_id')
            
            if not beat_plan_id:
                return {
                    "success": False,
                    "message": "Beat plan ID is required",
                    "data": None
                }

            # Find beat plan by ID
            beat_plan = self.beat_plan_collection.find_one({
                "$or": [
                    {"_id": beat_plan_id},
                    {"id": beat_plan_id}
                ],
                "del": 0
            })

            if not beat_plan:
                return {
                    "success": False,
                    "message": "Beat plan not found",
                    "data": None
                }

            # Convert ObjectId to string
            if '_id' in beat_plan:
                beat_plan['_id'] = str(beat_plan['_id'])
            if 'id' in beat_plan:
                beat_plan['id'] = str(beat_plan['id'])

            return {
                "success": True,
                "message": "Beat plan details fetched successfully",
                "data": beat_plan
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching beat plan details: {str(e)}",
                "data": None
            }
