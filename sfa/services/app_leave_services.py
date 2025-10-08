import os
import requests
from datetime import datetime, timedelta, date
from sfa.database import client1
from dotenv import load_dotenv
from bson import ObjectId
import pytz
import uuid
import shutil
from sfa.utils.date_utils import build_audit_fields

load_dotenv()

class AppLeaveService:
    def __init__(self):
        self.client_database = client1['talbros']
        self.field_squad_database = client1['field_squad']
        self.leave_collection = self.client_database['leave_applications']
        self.users_collection = self.field_squad_database['users']
        self.leave_balance_collection = self.client_database['leave_balances']
        self.timezone = pytz.timezone('Asia/Kolkata')  # Default to IST

    def _format_date(self, date_str):
        """Format date string to readable format"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d %b %Y")
        except:
            return date_str

    def _calculate_leave_days(self, start_date, end_date):
        """Calculate number of leave days between start and end date"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start > end:
                return 0
            
            # Calculate working days (excluding weekends)
            current = start
            working_days = 0
            
            while current <= end:
                # Monday = 0, Sunday = 6
                if current.weekday() < 5:  # Monday to Friday
                    working_days += 1
                current += timedelta(days=1)
            
            return working_days
        except:
            return 0

    def _get_leave_type_display_name(self, leave_type):
        """Get display name for leave type"""
        leave_type_names = {
            "casual": "Casual Leave",
            "sick": "Sick Leave",
            "other": "Other Leave"
        }
        return leave_type_names.get(leave_type, leave_type.title())

    def apply_leave(self, user_id, leave_type, start_date, end_date, reason=""):
        """Apply for leave"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Fetch valid leave types from leave_balances
            balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
            if not balance_record:
                # Create default balance if not exists
                default_balance = {
                    "user_id": user_id,
                    "casual": {"total": 12, "used": 0, "remaining": 12},
                    "sick": {"total": 15, "used": 0, "remaining": 15},
                    "other": {"total": 10, "used": 0, "remaining": 10},
                    "created_at": datetime.now(self.timezone).isoformat(),
                    "updated_at": datetime.now(self.timezone).isoformat()
                }
                self.leave_balance_collection.insert_one(default_balance)
                balance_record = default_balance
            valid_leave_types = [k for k in balance_record.keys() if k not in ["user_id", "_id", "created_at", "updated_at"]]
            if leave_type not in valid_leave_types:
                return {
                    "success": False,
                    "message": f"Invalid leave type: {leave_type}",
                    "error": {"code": "VALIDATION_ERROR", "details": f"Leave type must be one of: {', '.join(valid_leave_types)}"}
                }
            # Block if no remaining leave
            leave_balance = balance_record.get(leave_type, {})
            if leave_balance.get("remaining", 0) <= 0:
                return {
                    "success": False,
                    "message": f"No remaining leave for {leave_type}",
                    "error": {"code": "INSUFFICIENT_BALANCE", "details": f"No remaining leave for {leave_type}"}
                }

            # Validate dates
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                today = datetime.now(self.timezone).date()
                if start < today:
                    return {
                        "success": False,
                        "message": "Cannot apply leave for past dates",
                        "error": {"code": "VALIDATION_ERROR", "details": "Start date cannot be in the past"}
                    }
                if end < start:
                    return {
                        "success": False,
                        "message": "End date cannot be before start date",
                        "error": {"code": "VALIDATION_ERROR", "details": "End date must be after start date"}
                    }
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format",
                    "error": {"code": "VALIDATION_ERROR", "details": "Date must be in YYYY-MM-DD format"}
                }

            # Calculate leave days
            leave_days = self._calculate_leave_days(start_date, end_date)
            if leave_days <= 0:
                return {
                    "success": False,
                    "message": "Invalid leave duration",
                    "error": {"code": "VALIDATION_ERROR", "details": "Leave duration must be at least 0.5 days"}
                }
            # Check leave balance (including requested days)
            if leave_balance.get("remaining", 0) < leave_days:
                return {
                    "success": False,
                    "message": f"Insufficient {leave_type} leave balance",
                    "error": {"code": "INSUFFICIENT_BALANCE", "details": f"You have {leave_balance.get('remaining', 0)} days remaining, but requested {leave_days} days"}
                }
            # Check for overlapping leave applications
            overlap_query = {
                "user_id": user_id,
                "status": {"$in": ["pending", "approved"]},
                "$or": [
                    {
                        "start_date": {"$lte": end_date},
                        "end_date": {"$gte": start_date}
                    }
                ]
            }
            existing_leave = self.leave_collection.find_one(overlap_query)
            if existing_leave:
                return {
                    "success": False,
                    "message": "Leave application overlaps with existing leave",
                    "error": {"code": "OVERLAP_ERROR", "details": "You already have a leave application for these dates"}
                }
            # Create leave application
            created_fields = build_audit_fields(prefix="applied", by=user_id, timezone="Asia/Kolkata")
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            
            # Create status history
            status_history = [{
                "status": "pending",
                "changed_by": user_id,
                "changed_at": created_fields.get("applied_at"),
                "changed_time": created_fields.get("applied_time"),
                "remarks": "Leave application submitted"
            }]
            
            leave_data = {
                "user_id": user_id,
                "employee_id": user_id,
                "leave_type": leave_type,
                "start_date": start_date,
                "end_date": end_date,
                "leave_days": leave_days,
                "reason": reason,
                "status": "pending",
                "status_history": status_history,
                **created_fields,
                **updated_fields
            }
            result = self.leave_collection.insert_one(leave_data)
            if result.inserted_id:
                # Deduct leave from leave_balances
                self.leave_balance_collection.update_one(
                    {"user_id": user_id},
                    {"$inc": {f"{leave_type}.used": leave_days, f"{leave_type}.remaining": -leave_days}, "$set": {"updated_at": datetime.now(self.timezone).isoformat()}}
                )
                return {
                    "success": True,
                    "message": "Leave application submitted successfully",
                    "data": {
                        "leave_id": str(result.inserted_id),
                        "leave_type": leave_type,
                        "start_date": start_date,
                        "end_date": end_date,
                        "leave_days": leave_days,
                        "status": "pending"
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to submit leave application",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not save leave application"}
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to apply leave: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def _check_leave_balance(self, user_id, leave_type, requested_days):
        """Check if user has sufficient leave balance (dynamic types)"""
        try:
            balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
            if not balance_record:
                return {
                    "success": False,
                    "message": "No leave balance record found",
                    "error": {"code": "NO_BALANCE_RECORD", "details": "No leave balance record found for user"}
                }
            valid_leave_types = [k for k in balance_record.keys() if k not in ["user_id", "_id", "created_at", "updated_at"]]
            if leave_type not in valid_leave_types:
                return {
                    "success": False,
                    "message": f"Invalid leave type: {leave_type}",
                    "error": {"code": "VALIDATION_ERROR", "details": f"Leave type must be one of: {', '.join(valid_leave_types)}"}
                }
            leave_balance = balance_record.get(leave_type, {})
            remaining_days = leave_balance.get("remaining", 0)
            if remaining_days <= 0:
                return {
                    "success": False,
                    "message": f"No remaining leave for {leave_type}",
                    "error": {"code": "INSUFFICIENT_BALANCE", "details": f"No remaining leave for {leave_type}"}
                }
            if remaining_days < requested_days:
                return {
                    "success": False,
                    "message": f"Insufficient {leave_type} leave balance",
                    "error": {
                        "code": "INSUFFICIENT_BALANCE",
                        "details": f"You have {remaining_days} days remaining, but requested {requested_days} days"
                    }
                }
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to check leave balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_leave_list(self, user_id, page=1, limit=20, status="all", leave_type=None, year=None):
        """Get user's leave history with pagination and filtering"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Build query
            query = {"user_id": user_id}
            
            if status != "all":
                query["status"] = status
            
            if leave_type:
                query["leave_type"] = leave_type
            
            if year:
                query["start_date"] = {"$regex": f"^{year}-"}

            # Get total count
            total_records = self.leave_collection.count_documents(query)
            
            # Apply pagination
            skip = (page - 1) * limit
            leave_records = list(self.leave_collection.find(query).sort("applied_at", -1).skip(skip).limit(limit))

            # Process records for UI
            leave_list = []
            for record in leave_records:
                # Get user name from users collection
                user = self.users_collection.find_one({"_id": ObjectId(record["user_id"])})
                user_name = user.get("name", "Unknown") if user else "Unknown"
                
                # Format dates for display
                from_date_obj = datetime.strptime(record["start_date"], "%Y-%m-%d")
                to_date_obj = datetime.strptime(record["end_date"], "%Y-%m-%d")
                applied_date_obj = datetime.strptime(record.get("applied_at", ""), "%Y-%m-%d") if record.get("applied_at") else None
                
                leave_data = {
                    "_id": str(record["_id"]),
                    "leave_type": record["leave_type"],
                    "leave_type_display": self._get_leave_type_display_name(record["leave_type"]),
                    "user_name": user_name,
                    "from_date": record["start_date"],
                    "from_date_formatted": from_date_obj.strftime("%b %d, %Y"),
                    "to_date": record["end_date"],
                    "to_date_formatted": to_date_obj.strftime("%b %d, %Y"),
                    "days": record["leave_days"],
                    "reason": record.get("reason", ""),
                    "status": record["status"],
                    "applied_date": record.get("applied_at"),
                    "applied_date_formatted": applied_date_obj.strftime("%b %d, %Y") if applied_date_obj else "",
                    "applied_time": record.get("applied_time"),
                    "status_history": record.get("status_history", [])
                }
                leave_list.append(leave_data)

            # Calculate pagination
            total_pages = (total_records + limit - 1) // limit
            
            pagination = {
                "page": page,
                "limit": limit,
                "total": total_records,
                "totalPages": total_pages,
                "hasNext": page < total_pages,
                "hasPrev": page > 1
            }

            # Calculate status counts for tabs
            base_query = {"user_id": user_id}
            if leave_type:
                base_query["leave_type"] = leave_type
            if year:
                base_query["start_date"] = {"$regex": f"^{year}-"}
            
            status_counts = {
                "all": self.leave_collection.count_documents(base_query),
                "pending": self.leave_collection.count_documents({**base_query, "status": "pending"}),
                "approved": self.leave_collection.count_documents({**base_query, "status": "approved"}),
                "rejected": self.leave_collection.count_documents({**base_query, "status": "rejected"}),
                "cancelled": self.leave_collection.count_documents({**base_query, "status": "cancelled"})
            }

            return {
                "success": True,
                "data": {
                    "leaves": leave_list,
                    "pagination": pagination,
                    "status_counts": status_counts
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get leave list: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_leave_balance(self, user_id):
        """Get user's leave balance for different leave types"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get leave balance
            balance_record = self.leave_balance_collection.find_one({"user_id": user_id})
            
            if not balance_record:
                # Create default balance if not exists
                default_balance = {
                    "user_id": user_id,
                    "casual": {"total": 12, "used": 0, "remaining": 12},
                    "sick": {"total": 15, "used": 0, "remaining": 15},
                    "other": {"total": 10, "used": 0, "remaining": 10},
                    "created_at": datetime.now(self.timezone).isoformat(),
                    "updated_at": datetime.now(self.timezone).isoformat()
                }
                self.leave_balance_collection.insert_one(default_balance)
                balance_record = default_balance

            # Format balance data
            balance_data = []
            for leave_type, balance in balance_record.items():
                if leave_type not in ["user_id", "_id", "created_at", "updated_at"]:
                    balance_data.append({
                        "leaveType": leave_type,
                        "leaveTypeDisplay": self._get_leave_type_display_name(leave_type),
                        "total": balance.get("total", 0),
                        "used": balance.get("used", 0),
                        "remaining": balance.get("remaining", 0)
                    })

            return {
                "success": True,
                "data": {
                    "balances": balance_data
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get leave balance: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def get_leave_details(self, user_id, leave_id):
        """Get detailed information for a specific leave application"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get leave record
            leave_record = self.leave_collection.find_one({
                "_id": ObjectId(leave_id),
                "user_id": user_id
            })

            if not leave_record:
                return {
                    "success": False,
                    "message": "Leave application not found",
                    "error": {"code": "LEAVE_NOT_FOUND", "details": "Leave application does not exist"}
                }

            # Format dates for UI
            from_date_obj = datetime.strptime(leave_record["start_date"], "%Y-%m-%d")
            to_date_obj = datetime.strptime(leave_record["end_date"], "%Y-%m-%d")
            
            # Format date range display
            date_range = f"{from_date_obj.strftime('%a %b %d %Y')} - {to_date_obj.strftime('%a %b %d %Y')}"
            date_range_formatted = f"{from_date_obj.strftime('%a %b %d %Y')} - {to_date_obj.strftime('%a %b %d %Y')}"
            
            # Format requested date
            applied_date_obj = datetime.strptime(leave_record.get("applied_at", ""), "%Y-%m-%d") if leave_record.get("applied_at") else None
            requested_on = applied_date_obj.strftime("%A, %B %d, %Y") if applied_date_obj else ""
            
            # Format timeline from status_history
            timeline = []
            status_history = leave_record.get("status_history", [])
            for history in status_history:
                status_text = ""
                if history["status"] == "pending":
                    status_text = "Request Submitted"
                elif history["status"] == "approved":
                    status_text = "Request Approved"
                elif history["status"] == "rejected":
                    status_text = "Request Rejected"
                elif history["status"] == "cancelled":
                    status_text = "Request Cancelled"
                
                # Format timeline date and time
                timeline_date = history.get("changed_at", "")
                timeline_time = history.get("changed_time", "")
                if timeline_date and timeline_time:
                    dt_obj = datetime.strptime(f"{timeline_date} {timeline_time}", "%Y-%m-%d %H:%M:%S")
                    timeline_datetime = dt_obj.strftime("%b %d, %Y, %I:%M %p")
                else:
                    timeline_datetime = ""
                
                timeline.append({
                    "status": history["status"],
                    "status_text": status_text,
                    "datetime": timeline_datetime,
                    "changed_by": history.get("changed_by"),
                    "remarks": history.get("remarks", "")
                })
            
            # Format leave details for UI
            leave_details = {
                "_id": str(leave_record["_id"]),
                "status": leave_record["status"],
                "status_display": leave_record["status"].upper(),
                "days": leave_record["leave_days"],
                "date_range": date_range,
                "date_range_formatted": date_range_formatted,
                "leave_type": leave_record["leave_type"],
                "leave_type_display": self._get_leave_type_display_name(leave_record["leave_type"]),
                "from_date": leave_record["start_date"],
                "from_date_formatted": from_date_obj.strftime("%a %b %d %Y"),
                "to_date": leave_record["end_date"],
                "to_date_formatted": to_date_obj.strftime("%a %b %d %Y"),
                "reason": leave_record.get("reason", ""),
                "requested_on": requested_on,
                "timeline": timeline
            }

            return {
                "success": True,
                "data": leave_details
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get leave details: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def cancel_leave(self, user_id, leave_id, reason=""):
        """Cancel a leave application"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Get leave record
            leave_record = self.leave_collection.find_one({
                "_id": ObjectId(leave_id),
                "user_id": user_id
            })

            if not leave_record:
                return {
                    "success": False,
                    "message": "Leave application not found",
                    "error": {"code": "LEAVE_NOT_FOUND", "details": "Leave application does not exist"}
                }

            # Check if leave can be cancelled - only pending status allowed
            if leave_record["status"] != "pending":
                return {
                    "success": False,
                    "message": "Leave cannot be cancelled",
                    "error": {"code": "INVALID_STATUS", "details": "Only pending leaves can be cancelled"}
                }

            # Get leave details for balance restoration
            leave_type = leave_record["leave_type"]
            leave_days = leave_record["leave_days"]

            # Update leave record with status history
            from sfa.utils.date_utils import build_audit_fields
            updated_fields = build_audit_fields(prefix="updated", by=user_id, timezone="Asia/Kolkata")
            cancelled_fields = build_audit_fields(prefix="cancelled", by=user_id, timezone="Asia/Kolkata")
            
            # Add to status history
            status_history_entry = {
                "status": "cancelled",
                "changed_by": user_id,
                "changed_at": cancelled_fields.get("cancelled_at"),
                "changed_time": cancelled_fields.get("cancelled_time"),
                "remarks": reason if reason else "Leave cancelled by user"
            }

            result = self.leave_collection.update_one(
                {"_id": ObjectId(leave_id)},
                {
                    "$set": {
                        "status": "cancelled",
                        "cancellation_reason": reason,
                        **cancelled_fields,
                        **updated_fields
                    },
                    "$push": {"status_history": status_history_entry}
                }
            )

            if result.modified_count > 0:
                # Return leave days back to balance
                self.leave_balance_collection.update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {
                            f"{leave_type}.used": -leave_days,
                            f"{leave_type}.remaining": leave_days
                        },
                        "$set": {"updated_at": datetime.now(self.timezone).isoformat()}
                    }
                )
                
                return {
                    "success": True,
                    "message": "Leave cancelled successfully and balance restored",
                    "data": {
                        "leave_id": leave_id,
                        "status": "cancelled",
                        "restored_days": leave_days,
                        "leave_type": leave_type
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to cancel leave",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update leave application"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to cancel leave: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            }

    def upload_leave_attachment(self, user_id, leave_id, attachment):
        """Upload attachment for a specific leave application"""
        try:
            # Check if user exists
            user = self.users_collection.find_one({"_id": ObjectId(user_id), "del": {"$ne": 1}})
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error": {"code": "USER_NOT_FOUND", "details": "User does not exist"}
                }

            # Check if leave application exists and belongs to user
            leave_record = self.leave_collection.find_one({
                "_id": ObjectId(leave_id),
                "user_id": user_id
            })

            if not leave_record:
                return {
                    "success": False,
                    "message": "Leave application not found",
                    "error": {"code": "LEAVE_NOT_FOUND", "details": "Leave application does not exist or does not belong to you"}
                }

            # Create uploads directory if it doesn't exist
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)

            # Create leave attachments subdirectory
            leave_attachments_dir = os.path.join(uploads_dir, "leave_attachments")
            if not os.path.exists(leave_attachments_dir):
                os.makedirs(leave_attachments_dir)

            # Generate unique filename
            file_extension = os.path.splitext(attachment.filename)[1].lower()
            unique_filename = f"{leave_id}_{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(leave_attachments_dir, unique_filename)

            # Save file
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(attachment.file, buffer)
            except Exception as e:
                return {
                    "success": False,
                    "message": "Failed to save file",
                    "error": {"code": "FILE_SAVE_ERROR", "details": str(e)}
                }

            # Update leave record with attachment
            attachment_data = {
                "filename": attachment.filename,
                "saved_filename": unique_filename,
                "file_path": file_path,
                "file_size": attachment.size,
                "content_type": attachment.content_type,
                "uploaded_at": datetime.now(self.timezone).isoformat(),
                "uploaded_by": user_id
            }

            # Add attachment to leave record
            result = self.leave_collection.update_one(
                {"_id": ObjectId(leave_id)},
                {
                    "$push": {"attachments": attachment_data},
                    "$set": {"updated_at": datetime.now(self.timezone).isoformat()}
                }
            )

            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": "Attachment uploaded successfully",
                    "data": {
                        "leave_id": leave_id,
                        "attachment": {
                            "filename": attachment.filename,
                            "saved_filename": unique_filename,
                            "file_path": file_path,
                            "file_size": attachment.size,
                            "uploaded_at": attachment_data["uploaded_at"]
                        }
                    }
                }
            else:
                # If update failed, delete the saved file
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                return {
                    "success": False,
                    "message": "Failed to update leave record with attachment",
                    "error": {"code": "DATABASE_ERROR", "details": "Could not update leave application"}
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to upload attachment: {str(e)}",
                "error": {"code": "SERVER_ERROR", "details": str(e)}
            } 