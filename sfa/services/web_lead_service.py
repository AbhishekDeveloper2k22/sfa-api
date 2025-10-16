from bson import ObjectId
from sfa.database import client1
from datetime import datetime
import re
import os
import uuid


class lead_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.leads_collection = self.client_database["leads"]  # Use leads collection like app services
        self.current_datetime = datetime.now()

    def _now_fields(self):
        return {
            "created_at": self.current_datetime.strftime("%Y-%m-%d"),
            "created_at_time": self.current_datetime.strftime("%H:%M:%S"),
        }

    def _normalize_lead(self, request_data: dict) -> dict:
        doc = {
            "name": request_data.get('name'),
            "mobile": request_data.get('mobile'),
            "email": request_data.get('email'),
            "company": request_data.get('company'),
            "source": request_data.get('source'),
            "status": request_data.get('status', 'new'),
            "notes": request_data.get('notes', ''),
            "address": request_data.get('address'),
            "pincode": request_data.get('pincode'),
            "city": request_data.get('city'),
            "state": request_data.get('state'),
            "country": request_data.get('country', 'India'),
            "del": 0,
        }
        return doc

    def _unique_query(self, request_data: dict):
        # Simple mobile check like app service
        if request_data.get('mobile'):
            return {'mobile': request_data['mobile'], 'del': {'$ne': 1}}
        return None

    def add_lead(self, request_data: dict) -> dict:
        # uniqueness check (mobile)
        uq = self._unique_query(request_data)
        if uq:
            exist = self.leads_collection.find_one(uq)
            if exist:
                return {
                    "success": False,
                    "message": "Lead already exists",
                    "existing_id": str(exist['_id'])
                }

        doc = self._normalize_lead(request_data)
        doc.update(self._now_fields())
        doc['created_by'] = request_data.get('created_by', 1)

        res = self.leads_collection.insert_one(doc)
        if res.inserted_id:
            return {"success": True, "message": "Lead added", "inserted_id": str(res.inserted_id)}
        return {"success": False, "message": "Failed to add lead"}

    def update_lead(self, request_data: dict) -> dict:
        lead_id = request_data.get('_id') or request_data.get('id')
        if not lead_id:
            return {"success": False, "message": "Lead ID is required"}

        uq = self._unique_query(request_data)
        if uq:
            exist = self.leads_collection.find_one(uq)
            if exist and str(exist['_id']) != str(lead_id):
                return {
                    "success": False,
                    "message": "Another lead exists with same mobile",
                    "existing_id": str(exist['_id'])
                }

        # Update exactly the fields provided (like users update), allow new fields
        update_data = request_data.copy()
        if '_id' in update_data:
            del update_data['_id']

        # Always set/update timestamps
        update_data['updated_at'] = self.current_datetime.strftime("%Y-%m-%d")
        update_data['updated_at_time'] = self.current_datetime.strftime("%H:%M:%S")

        res = self.leads_collection.update_one({"_id": ObjectId(lead_id)}, {"$set": update_data})
        if res.matched_count > 0:
            return {"success": True, "message": "Lead updated", "matched_count": res.matched_count}
        return {"success": False, "message": "Lead not found"}


    def lead_details(self, request_data: dict) -> dict:
        lead_id = request_data.get('_id') or request_data.get('id')
        if not lead_id:
            return {"success": False, "message": "Lead ID is required", "data": None}
        try:
            doc = self.leads_collection.find_one({"_id": ObjectId(lead_id), "del": {"$ne": 1}})
            if not doc:
                return {"success": False, "message": "Lead not found", "data": None}
            doc['_id'] = str(doc['_id'])
            return {"success": True, "message": "Lead details", "data": doc}
        except Exception as e:
            return {"success": False, "message": f"Invalid ID: {e}", "data": None}

    def leads_list(self, request_data: dict) -> dict:
        limit = request_data.get('limit', 10)
        page = request_data.get('page', 1)
        skip = (page - 1) * limit

        query = request_data.copy()
        for k in ['limit', 'page']:
            if k in query:
                del query[k]
        # enforce non-deleted by default like app service
        if 'del' not in query:
            query['del'] = {'$ne': 1}
        
        print("query", query)

        total_count = self.leads_collection.count_documents(query)
        items = list(self.leads_collection.find(query).skip(skip).limit(limit))
        print("items", items)
        for it in items:
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

    def update_lead_image(self, lead_id: str, upload_file) -> dict:
        if not lead_id:
            return {"success": False, "message": "Lead ID is required"}
        try:
            doc = self.leads_collection.find_one({"_id": ObjectId(lead_id), "del": {"$ne": 1}})
            if not doc:
                return {"success": False, "message": "Lead not found"}
        except Exception as e:
            return {"success": False, "message": f"Invalid lead ID: {e}"}

        base_dir = os.path.join("uploads", "sfa_uploads", "leads")
        os.makedirs(base_dir, exist_ok=True)

        original = upload_file.filename or "file"
        _, ext = os.path.splitext(original)
        unique_name = f"lead_{uuid.uuid4().hex}{ext.lower()}"
        file_path = os.path.join(base_dir, unique_name)

        with open(file_path, 'wb') as f:
            f.write(upload_file.file.read())

        res = self.leads_collection.update_one({"_id": ObjectId(lead_id)}, {"$set": {
            "image": unique_name,
            "image_updated_at": self.current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        }})
        if res.matched_count > 0:
            return {"success": True, "message": "Lead image updated", "file_name": unique_name}
        return {"success": False, "message": "Failed to update image"}


