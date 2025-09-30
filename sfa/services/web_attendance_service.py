from bson import ObjectId
from sfa.database import client1
from datetime import datetime


class attendance_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.attendance = self.client_database['attendance']
        self.current_datetime = datetime.now()

    def attendance_list(self, request_data: dict) -> dict:
        # pagination
        limit = request_data.get('limit', 10)
        page = request_data.get('page', 1)
        skip = (page - 1) * limit

        # build query by removing pagination keys
        query = request_data.copy()
        if 'limit' in query:
            del query['limit']
        if 'page' in query:
            del query['page']

        total_count = self.attendance.count_documents(query)
        items = list(self.attendance.find(query).skip(skip).limit(limit))
        for it in items:
            if '_id' in it:
                it['_id'] = str(it['_id'])

        total_pages = (total_count + limit - 1) // limit
        return {
            "data": items,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "limit": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }


