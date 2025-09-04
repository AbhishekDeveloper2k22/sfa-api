from bson import ObjectId
from sfa.database import client1
from datetime import datetime
import os
import uuid


class customer_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.customers = self.client_database["customers"]
        self.current_datetime = datetime.now()

    def _now_fields(self):
        return {
            "created_at": self.current_datetime.strftime("%Y-%m-%d"),
            "created_at_time": self.current_datetime.strftime("%H:%M:%S"),
        }

    def _unique_query(self, request_data: dict):
        or_conditions = []
        if request_data.get('email'):
            or_conditions.append({'email': request_data['email']})
        if request_data.get('phone'):
            or_conditions.append({'phone': request_data['phone']})
        if request_data.get('mobile'):
            or_conditions.append({'mobile': request_data['mobile']})
        if not or_conditions:
            return None
        return {'$or': or_conditions, 'type': 'non-lead', 'del': 0}

    def add_customer(self, request_data: dict) -> dict:
        # uniqueness check (email/phone/mobile)
        uq = self._unique_query(request_data)
        if uq:
            exist = self.customers.find_one(uq)
            if exist:
                return {
                    "success": False,
                    "message": "Customer already exists with same email/phone",
                    "existing_id": str(exist['_id'])
                }

        doc = request_data.copy()
        doc['type'] = 'non-lead'
        doc['del'] = doc.get('del', 0)
        doc['status'] = doc.get('status', 'active')
        doc.update(self._now_fields())
        doc['created_by'] = request_data.get('created_by', 1)

        res = self.customers.insert_one(doc)
        if res.inserted_id:
            return {"success": True, "message": "Customer added", "inserted_id": str(res.inserted_id)}
        return {"success": False, "message": "Failed to add customer"}

    def update_customer(self, request_data: dict) -> dict:
        cust_id = request_data.get('_id') or request_data.get('id')
        if not cust_id:
            return {"success": False, "message": "Customer ID is required"}

        uq = self._unique_query(request_data)
        if uq:
            exist = self.customers.find_one(uq)
            if exist and str(exist['_id']) != str(cust_id):
                return {
                    "success": False,
                    "message": "Another customer exists with same email/phone",
                    "existing_id": str(exist['_id'])
                }

        update_data = request_data.copy()
        if '_id' in update_data:
            del update_data['_id']
        if 'id' in update_data:
            del update_data['id']
        # always enforce type non-lead on updates if provided or ensure not removed
        update_data['type'] = 'non-lead'
        update_data['updated_at'] = self.current_datetime.strftime("%Y-%m-%d")
        update_data['updated_at_time'] = self.current_datetime.strftime("%H:%M:%S")

        res = self.customers.update_one({"_id": ObjectId(cust_id)}, {"$set": update_data})
        if res.matched_count > 0:
            return {"success": True, "message": "Customer updated", "matched_count": res.matched_count}
        return {"success": False, "message": "Customer not found"}

    def customers_list(self, request_data: dict) -> dict:
        limit = request_data.get('limit', 10)
        page = request_data.get('page', 1)
        skip = (page - 1) * limit

        query = request_data.copy()
        for k in ['limit', 'page']:
            if k in query:
                del query[k]
        query['type'] = 'non-lead'
        if 'del' not in query:
            query['del'] = 0

        total_count = self.customers.count_documents(query)
        items = list(self.customers.find(query).skip(skip).limit(limit))
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

    def customer_details(self, request_data: dict) -> dict:
        cust_id = request_data.get('_id') or request_data.get('id')
        if not cust_id:
            return {"success": False, "message": "Customer ID is required", "data": None}
        try:
            doc = self.customers.find_one({"_id": ObjectId(cust_id), "type": "non-lead"})
            if not doc:
                return {"success": False, "message": "Customer not found", "data": None}
            doc['_id'] = str(doc['_id'])
            return {"success": True, "message": "Customer details", "data": doc}
        except Exception as e:
            return {"success": False, "message": f"Invalid ID: {e}", "data": None}

    def update_customer_image(self, customer_id: str, upload_file) -> dict:
        if not customer_id:
            return {"success": False, "message": "Customer ID is required"}
        try:
            doc = self.customers.find_one({"_id": ObjectId(customer_id), "type": "non-lead"})
            if not doc:
                return {"success": False, "message": "Customer not found"}
        except Exception as e:
            return {"success": False, "message": f"Invalid customer ID: {e}"}

        base_dir = os.path.join("uploads", "sfa", "customers")
        os.makedirs(base_dir, exist_ok=True)

        original = upload_file.filename or "file"
        _, ext = os.path.splitext(original)
        unique_name = f"cust_{uuid.uuid4().hex}{ext.lower()}"
        file_path = os.path.join(base_dir, unique_name)

        with open(file_path, 'wb') as f:
            f.write(upload_file.file.read())

        res = self.customers.update_one({"_id": ObjectId(customer_id)}, {"$set": {
            "image": unique_name,
            "image_updated_at": self.current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        }})
        if res.matched_count > 0:
            return {"success": True, "message": "Customer image updated", "file_name": unique_name}
        return {"success": False, "message": "Failed to update image"}


