from bson import ObjectId
from sfa.database import client1


class order_tool:
    def __init__(self):
        self.main_database = client1['talbros']
        self.orders = self.main_database['orders']
        self.field_squad_database = client1["field_squad"]
        self.users_collection = self.field_squad_database["users"]

    def order_list(self, request_data: dict):
        try:
            limit = int(request_data.get('limit', 10))
            page = int(request_data.get('page', 1))
            skip = (page - 1) * limit

            query = request_data.copy() if request_data else {}
            for k in ['limit', 'page']:
                if k in query:
                    del query[k]

            total_count = self.orders.count_documents(query)
            items = list(self.orders.find(query).skip(skip).limit(limit).sort('created_at', -1))
            for it in items:
                if '_id' in it:
                    it['_id'] = str(it['_id'])
                created_by_id = it.get('created_by')
                if created_by_id:
                    try:
                        created_user = self.users_collection.find_one({"_id": ObjectId(created_by_id)})
                        it['created_by_name'] = created_user.get('name', 'Unknown') if created_user else 'Unknown'
                    except Exception:
                        it['created_by_name'] = 'Unknown'
                else:
                    it['created_by_name'] = 'Unknown'
                updated_by_id = it.get('updated_by')
                if updated_by_id:
                    try:
                        updated_user = self.users_collection.find_one({"_id": ObjectId(updated_by_id)})
                        it['updated_by_name'] = updated_user.get('name', 'Unknown') if updated_user else 'Unknown'
                    except Exception:
                        it['updated_by_name'] = 'Unknown'
                else:
                    it['updated_by_name'] = 'Unknown'

            total_pages = (total_count + limit - 1) // limit
            return {
                "success": True,
                "message": "Orders fetched successfully",
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
        except Exception as e:
            return {"success": False, "message": str(e), "data": []}

    def order_details(self, request_data: dict):
        try:
            oid = request_data.get('id') or request_data.get('_id')
            if not oid:
                return {"success": False, "message": "Order ID is required", "data": None}
            # Try match by ObjectId then as plain id field
            doc = None
            try:
                doc = self.orders.find_one({"_id": ObjectId(oid)})
            except Exception:
                doc = None
            if not doc:
                doc = self.orders.find_one({"id": oid})
            if not doc:
                return {"success": False, "message": "Order not found", "data": None}
            doc['_id'] = str(doc['_id'])
            created_by_id = doc.get('created_by')
            if created_by_id:
                try:
                    created_user = self.users_collection.find_one({"_id": ObjectId(created_by_id)})
                    doc['created_by_name'] = created_user.get('name', 'Unknown') if created_user else 'Unknown'
                except Exception:
                    doc['created_by_name'] = 'Unknown'
            else:
                doc['created_by_name'] = 'Unknown'
            updated_by_id = doc.get('updated_by')
            if updated_by_id:
                try:
                    updated_user = self.users_collection.find_one({"_id": ObjectId(updated_by_id)})
                    doc['updated_by_name'] = updated_user.get('name', 'Unknown') if updated_user else 'Unknown'
                except Exception:
                    doc['updated_by_name'] = 'Unknown'
            else:
                doc['updated_by_name'] = 'Unknown'
            return {"success": True, "message": "Order details fetched successfully", "data": doc}
        except Exception as e:
            return {"success": False, "message": str(e), "data": None}

    def order_update(self, request_data: dict):
        try:
            oid = request_data.get('_id') or request_data.get('id')
            if not oid:
                return {"success": False, "message": "Order ID is required"}

            update_data = request_data.copy()
            if '_id' in update_data:
                del update_data['_id']
            if 'id' in update_data:
                del update_data['id']

            # Attempt update by _id first
            matched = 0
            try:
                res = self.orders.update_one({"_id": ObjectId(oid)}, {"$set": update_data})
                matched = res.matched_count
            except Exception:
                matched = 0
            if matched == 0:
                res = self.orders.update_one({"id": oid}, {"$set": update_data})
                matched = res.matched_count
            if matched == 0:
                return {"success": False, "message": "Order not found"}
            return {
                "success": True,
                "message": "Order updated successfully",
                "matched_count": matched
            }
        except Exception as e:
            return {"success": False, "message": str(e)}


