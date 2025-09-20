from bson import ObjectId
from field_squad.database import client1
from datetime import datetime
import re
import os
import uuid


class lead_tool:
    def __init__(self):
        self.client_database = client1['talbros']
        self.customers = self.client_database["customers"]
        self.current_datetime = datetime.now()

    def _now_fields(self):
        return {
            "created_at": self.current_datetime.strftime("%Y-%m-%d"),
            "created_at_time": self.current_datetime.strftime("%H:%M:%S"),
        }

    def _normalize_lead(self, request_data: dict) -> dict:
        doc = {
            "type": "lead",
            "customer_type": request_data.get('customer_type'),  # 1 Distributor, 2 Dealer, 3 Retailer
            "name": request_data.get('name'),
            "company_name": request_data.get('company_name'),
            "email": request_data.get('email'),
            "phone": request_data.get('phone'),
            "mobile": request_data.get('mobile'),
            "alternate_phone": request_data.get('alternate_phone'),
            "whatsapp": request_data.get('whatsapp'),
            "gst_number": request_data.get('gst_number'),
            "pan_number": request_data.get('pan_number'),
            "credit_limit": request_data.get('credit_limit'),
            "billing_address": request_data.get('billing_address'),
            "shipping_address": request_data.get('shipping_address'),
            "state": request_data.get('state'),
            "district": request_data.get('district'),
            "city": request_data.get('city'),
            "pincode": request_data.get('pincode'),
            "latitude": request_data.get('latitude'),
            "longitude": request_data.get('longitude'),
            "contact_person": request_data.get('contact_person'),
            "designation": request_data.get('designation'),
            "status": request_data.get('status', 'active'),
            "del": 0,
        }
        return doc

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
        return {'$or': or_conditions, 'type': 'lead', 'del': 0}

    def add_lead(self, request_data: dict) -> dict:
        # uniqueness check (email/phone/mobile)
        uq = self._unique_query(request_data)
        if uq:
            exist = self.customers.find_one(uq)
            if exist:
                return {
                    "success": False,
                    "message": "Lead already exists with same email/phone",
                    "existing_id": str(exist['_id'])
                }

        doc = self._normalize_lead(request_data)
        doc.update(self._now_fields())
        doc['created_by'] = request_data.get('created_by', 1)

        res = self.customers.insert_one(doc)
        if res.inserted_id:
            return {"success": True, "message": "Lead added", "inserted_id": str(res.inserted_id)}
        return {"success": False, "message": "Failed to add lead"}

    def update_lead(self, request_data: dict) -> dict:
        lead_id = request_data.get('_id') or request_data.get('id')
        if not lead_id:
            return {"success": False, "message": "Lead ID is required"}

        uq = self._unique_query(request_data)
        if uq:
            exist = self.customers.find_one(uq)
            if exist and str(exist['_id']) != str(lead_id):
                return {
                    "success": False,
                    "message": "Another lead exists with same email/phone",
                    "existing_id": str(exist['_id'])
                }

        # Update exactly the fields provided (like users update), allow new fields
        update_data = request_data.copy()
        if '_id' in update_data:
            del update_data['_id']

        # Always set/update timestamps
        update_data['updated_at'] = self.current_datetime.strftime("%Y-%m-%d")
        update_data['updated_at_time'] = self.current_datetime.strftime("%H:%M:%S")

        res = self.customers.update_one({"_id": ObjectId(lead_id)}, {"$set": update_data})
        if res.matched_count > 0:
            return {"success": True, "message": "Lead updated", "matched_count": res.matched_count}
        return {"success": False, "message": "Lead not found"}


    def lead_details(self, request_data: dict) -> dict:
        lead_id = request_data.get('_id') or request_data.get('id')
        if not lead_id:
            return {"success": False, "message": "Lead ID is required", "data": None}
        try:
            doc = self.customers.find_one({"_id": ObjectId(lead_id), "type": "lead"})
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
        # enforce lead type and non-deleted by default
        query['type'] = 'lead'
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

    def update_lead_image(self, lead_id: str, upload_file) -> dict:
        if not lead_id:
            return {"success": False, "message": "Lead ID is required"}
        try:
            doc = self.customers.find_one({"_id": ObjectId(lead_id), "type": "lead"})
            if not doc:
                return {"success": False, "message": "Lead not found"}
        except Exception as e:
            return {"success": False, "message": f"Invalid lead ID: {e}"}

        base_dir = os.path.join("uploads", "sfa", "leads")
        os.makedirs(base_dir, exist_ok=True)

        original = upload_file.filename or "file"
        _, ext = os.path.splitext(original)
        unique_name = f"lead_{uuid.uuid4().hex}{ext.lower()}"
        file_path = os.path.join(base_dir, unique_name)

        with open(file_path, 'wb') as f:
            f.write(upload_file.file.read())

        res = self.customers.update_one({"_id": ObjectId(lead_id)}, {"$set": {
            "image": unique_name,
            "image_updated_at": self.current_datetime.strftime("%Y-%m-%d %H:%M:%S")
        }})
        if res.matched_count > 0:
            return {"success": True, "message": "Lead image updated", "file_name": unique_name}
        return {"success": False, "message": "Failed to update image"}


