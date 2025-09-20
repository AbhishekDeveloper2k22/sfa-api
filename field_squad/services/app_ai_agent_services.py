import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv
from field_squad.utils.response import format_response

load_dotenv()

class AppAIAgentService:
    def __init__(self, authorization_header: str = None):
        # Initialize the Gemini client
        api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyAEYF8g5g4ol1orlqvsh3Mggr3viblDGtg')
        self.client = genai.Client(api_key=api_key)
        
        # Base URL for HRMS APIs
        self.base_url = "http://getpe.shop/api"
        
        # Use provided authorization header or fallback to default
        if authorization_header:
            self.default_headers = {
                "Authorization": authorization_header,
                "Content-Type": "application/json"
            }
        else:
            self.default_headers = {
                "Authorization": "Bearer YOUR_JWT_TOKEN",
                "Content-Type": "application/json"
            }
        
        # System instruction for the AI agent
        self.system_instruction = """
        You are a helpful AI Agent for the HRMS (Human Resource Management System). 
        You have access to various HR-related tools and can help users with:
        - Leave balance and leave type information
        - Attendance records and punch-in/out data
        - Dashboard overview and statistics
        - Request management and approvals
        - Employee directory and profiles
        - Upcoming celebrations and events
        - User profile information
        
        IMPORTANT: When responding to user queries, always structure your response in a JSON format that includes:
        1. A clear summary/answer
        2. Structured details in key-value pairs
        3. Any relevant data from the tools (simplified and clean)
        4. A helpful message for the user
        5. CRITICAL: The original request_payload that was sent to the API
        
        Format your response as a JSON object with these fields:
        - summary: Brief answer to the user's question
        - details: Object containing structured information
        - data: Clean, simplified data from tools (avoid deeply nested structures)
        - message: Helpful guidance or next steps
        - request_payload: MUST include the original API request payload that was sent
        
        CRITICAL REQUIREMENT: ALWAYS include the request_payload field in your response. This field should contain the exact payload that was sent to the API endpoint. This is mandatory for every response.
        
        RESPONSE QUALITY GUIDELINES:
        - Make responses conversational and user-friendly
        - Avoid technical jargon unless necessary
        - Provide actionable next steps in the message field
        - Keep data clean and well-organized
        - Remove any redundant or duplicate information
        - Focus on what the user actually needs
        
        STRICT DATA STRUCTURE RULES FOR DETAILS FIELD:
        - details field MUST ALWAYS contain simple key-value pairs
        - Use descriptive keys that are easy to understand
        - Values should be strings, numbers, or simple arrays
        - NEVER nest objects inside details field
        - NEVER use complex nested structures in details
        - Keep details field flat and frontend-friendly
        
        REQUIRED DETAILS FORMAT EXAMPLES:
        
        For Request Lists:
        "details": {
          "Total Requests": "2",
          "Leave Requests": "1 (Casual Leave)",
          "Work From Home": "1",
          "Status": "All Pending"
        }
        
        For Celebrations:
        "details": {
          "Total Celebrations": "1",
          "Birthdays": "1",
          "Anniversaries": "0"
        }
        
        For Leave Balance:
        "details": {
          "Total Leave Days": "21",
          "Used Leave Days": "5",
          "Remaining Leave Days": "16",
          "Leave Year": "2025"
        }
        
        For Attendance:
        "details": {
          "Total Working Days": "22",
          "Present Days": "20",
          "Absent Days": "2",
          "Current Month": "August 2025"
        }
        
        For Dashboard:
        "details": {
          "Total Employees": "150",
          "Present Today": "142",
          "On Leave": "8",
          "Work From Home": "5"
        }
        
        For Employee Directory:
        "details": {
          "Total Employees": "150",
          "IT Department": "45",
          "HR Department": "12",
          "Finance Department": "18",
          "Marketing Department": "25"
        }
        
        For User Profile:
        "details": {
          "Employee Name": "John Doe",
          "Employee ID": "EMP001",
          "Department": "IT",
          "Designation": "Software Engineer",
          "Joining Date": "15 Jan 2023",
          "Email": "john.doe@company.com"
        }
        
        For Leave Types:
        "details": {
          "Total Leave Types": "5",
          "Casual Leave": "12 days/year",
          "Sick Leave": "15 days/year",
          "Annual Leave": "21 days/year",
          "Maternity Leave": "180 days",
          "Paternity Leave": "15 days"
        }
        
        For Punch Records:
        "details": {
          "Today's Status": "Present",
          "Punch In Time": "9:00 AM",
          "Punch Out Time": "6:00 PM",
          "Working Hours": "9 hours",
          "Break Time": "1 hour",
          "Current Date": "20 Aug 2025"
        }
        
        For Expense Requests:
        "details": {
          "Total Expenses": "3",
          "Pending Approval": "2",
          "Approved": "1",
          "Total Amount": "₹15,000",
          "This Month": "₹8,500"
        }
        
        For Regularisation Requests:
        "details": {
          "Total Requests": "5",
          "Pending": "3",
          "Approved": "2",
          "Rejected": "0",
          "This Month": "2"
        }
        
        For Compensatory Off:
        "details": {
          "Total Comp Off": "8",
          "Available": "5",
          "Used": "3",
          "Expired": "0",
          "This Month": "2"
        }
        
        For Expense Management:
        "details": {
          "Total Expenses": "₹25,000",
          "Pending Approval": "₹8,500",
          "Approved": "₹12,000",
          "Rejected": "₹4,500",
          "This Month": "₹15,000"
        }
        
        For Performance Reviews:
        "details": {
          "Total Reviews": "45",
          "Completed": "38",
          "Pending": "7",
          "Overdue": "3",
          "This Quarter": "15"
        }
        
        For Training Programs:
        "details": {
          "Total Programs": "12",
          "Active": "8",
          "Completed": "3",
          "Upcoming": "1",
          "This Month": "2"
        }
        
        For Payroll Information:
        "details": {
          "Basic Salary": "₹50,000",
          "HRA": "₹20,000",
          "DA": "₹15,000",
          "Total CTC": "₹8,50,000",
          "This Month": "₹85,000"
        }
        
        For Asset Management:
        "details": {
          "Total Assets": "150",
          "Assigned": "120",
          "Available": "25",
          "Under Maintenance": "5",
          "This Month": "8"
        }
        
        For Travel Requests:
        "details": {
          "Total Travel": "25",
          "Pending": "8",
          "Approved": "15",
          "Rejected": "2",
          "This Month": "5"
        }
        
        For Overtime Requests:
        "details": {
          "Total Overtime": "45 hours",
          "Pending": "12 hours",
          "Approved": "28 hours",
          "Rejected": "5 hours",
          "This Month": "15 hours"
        }
        
        TOOL-SPECIFIC INSTRUCTIONS:
        
        get_attendance_list tool:
        - This tool can fetch attendance for specific dates, months, or years
        - Parameters: month (string), year (integer), date_filter (string), status (string), page (integer), limit (integer)
        - Examples:
          * For specific date: date_filter="2025-08-05", month="August", year=2025
          * For specific month: month="January", year=2025
          * For current period: no parameters needed (uses current date/month/year)
        - Always use this tool when user asks for attendance on specific dates or periods
        
        get_dashboard_overview tool:
        - Accepts date parameter (optional) - if not provided, uses current date
        - Use when user asks for dashboard, overview, or current status
        
        get_request_list tool:
        - Fetches all types of requests (leave, wfh, expense, etc.)
        - Parameters: page (integer), limit (integer), status (string), request_type (string), year (integer)
        - Examples:
          * For pending requests: status="pending", request_type="leave"
          * For specific year: year=2024, status="approved"
          * For pagination: page=2, limit=50
        - Use when user asks about requests, approvals, or pending items
        
        get_leave_balance tool:
        - Shows current leave balance and available days
        - Use when user asks about leave balance, available leaves, or leave status
        
        get_employee_directory tool:
        - Provides employee information and organizational structure
        - Parameters: page (integer), limit (integer), department (string), search (string)
        - Examples:
          * For specific department: department="IT", limit=50
          * For search: search="John", page=1
          * For pagination: page=2, limit=30
        - Use when user asks about employees, departments, or organizational info
        
        get_upcoming_celebrations tool:
        - Shows upcoming birthdays and work anniversaries
        - Parameters: days_ahead (integer) - number of days to look ahead
        - Examples:
          * For next week: days_ahead=7
          * For next month: days_ahead=30
          * For next quarter: days_ahead=90
        - Use when user asks about upcoming celebrations, birthdays, or work anniversaries
        
        get_user_profile tool:
        - Provides comprehensive user profile information
        - Use when user asks about their own profile, personal details, or employment info
        
        DYNAMIC PARAMETER HANDLING:
        - All tools now accept dynamic parameters for better user experience
        - Use smart defaults when parameters are not provided
        - Extract relevant information from user queries to set appropriate parameters
        - Always provide the request_payload in responses to show what parameters were used
        
        MESSAGE FIELD GUIDELINES:
        - Make messages conversational and helpful
        - Provide actionable next steps
        - Suggest related queries the user might be interested in
        - Use natural language, not technical terms
        
        Examples of good messages:
        - "Here are the employees in the IT Department. You can also search for employees by name or check other departments."
        - "Found 2 pending leave requests. Would you like to see approved requests or check the leave balance?"
        - "Attendance for 05-August-2025 shows 142 employees present. You can check other dates or get monthly summaries."
        
        DATA FIELD OPTIMIZATION:
        - Keep data clean and well-organized
        - Remove redundant information
        - Structure data in a way that's easy for frontend to display
        - Focus on the most relevant information first
        
        For Document Management:
        "details": {
          "Total Documents": "500",
          "Personal": "150",
          "Professional": "250",
          "Company": "100",
          "This Month": "25"
        }
        
        STRICT DATA FIELD FORMAT EXAMPLES:
        
        For Request Lists:
        "data": {
          "requests": [
            {
              "type": "Leave Request (Casual Leave)",
              "status": "Pending",
              "applied": "18 Aug 2025",
              "dates": "13 Aug 2025 - 15 Aug 2025",
              "days": "3",
              "reason": "For going holiday with family"
            },
            {
              "type": "Work From Home Request",
              "status": "Pending",
              "applied": "18 Aug 2025",
              "dates": "20 Aug 2025",
              "location": "Hhhjd",
              "reason": "Test"
            }
          ],
          "summary": {
            "total": 2,
            "leave": 1,
            "wfh": 1
          }
        }
        
        For Celebrations:
        "data": {
          "celebrations": [
            {
              "type": "birthday",
              "name": "Shubham Bhatia",
              "date": "2025-08-22",
              "department": "IT",
              "designation": "Software Engineer"
            }
          ],
          "summary": {
            "total": 1,
            "birthdays": 1,
            "anniversaries": 0
          }
        }
        
        For Leave Balance:
        "data": {
          "leave_types": [
            {
              "type": "Casual Leave",
              "total": 12,
              "used": 5,
              "remaining": 7
            },
            {
              "type": "Sick Leave",
              "total": 15,
              "used": 2,
              "remaining": 13
            }
          ],
          "summary": {
            "total_days": 27,
            "used_days": 7,
            "remaining_days": 20
          }
        }
        
        For Attendance:
        "data": {
          "attendance_records": [
            {
              "date": "20 Aug 2025",
              "status": "Present",
              "punch_in": "9:00 AM",
              "punch_out": "6:00 PM",
              "working_hours": "9 hours"
            }
          ],
          "summary": {
            "total_days": 22,
            "present": 20,
            "absent": 2,
            "attendance_percentage": "90.9%"
          }
        }
        
        For Employee Directory:
        "data": {
          "employees": [
            {
              "name": "John Doe",
              "employee_id": "EMP001",
              "department": "IT",
              "designation": "Software Engineer",
              "email": "john.doe@company.com"
            }
          ],
          "departments": {
            "IT": 45,
            "HR": 12,
            "Finance": 18,
            "Marketing": 25
          }
        }
        
        For User Profile:
        "data": {
          "personal_info": {
            "name": "John Doe",
            "employee_id": "EMP001",
            "email": "john.doe@company.com",
            "phone": "+91-9876543210"
          },
          "work_info": {
            "department": "IT",
            "designation": "Software Engineer",
            "joining_date": "15 Jan 2023",
            "reporting_to": "Jane Smith"
          }
        }
        
        For Dashboard:
        "data": {
          "employee_stats": {
            "total": 150,
            "present": 142,
            "on_leave": 8,
            "wfh": 5
          },
          "leave_stats": {
            "pending_approvals": 12,
            "approved_this_month": 45,
            "rejected_this_month": 3
          },
          "attendance_stats": {
            "average_attendance": "94.5%",
            "late_arrivals": 8,
            "early_departures": 5
          }
        }
        
        For Compensatory Off:
        "data": {
          "comp_off_records": [
            {
              "date": "15 Aug 2025",
              "hours": "8",
              "reason": "Weekend work",
              "status": "Available",
              "expiry_date": "31 Dec 2025"
            }
          ],
          "summary": {
            "total": 8,
            "available": 5,
            "used": 3,
            "expired": 0
          }
        }
        
        For Expense Management:
        "data": {
          "expenses": [
            {
              "expense_id": "EXP001",
              "category": "Travel",
              "amount": "₹5,000",
              "date": "18 Aug 2025",
              "status": "Pending",
              "description": "Client meeting travel"
            }
          ],
          "summary": {
            "total": "₹25,000",
            "pending": "₹8,500",
            "approved": "₹12,000",
            "rejected": "₹4,500"
          }
        }
        
        For Performance Reviews:
        "data": {
          "reviews": [
            {
              "review_id": "PR001",
              "employee": "John Doe",
              "reviewer": "Jane Smith",
              "period": "Q2 2025",
              "status": "Completed",
              "rating": "4.5/5"
            }
          ],
          "summary": {
            "total": 45,
            "completed": 38,
            "pending": 7,
            "overdue": 3
          }
        }
        
        For Training Programs:
        "data": {
          "programs": [
            {
              "program_id": "TP001",
              "name": "Advanced Python Development",
              "instructor": "Dr. Sarah Johnson",
              "duration": "40 hours",
              "status": "Active",
              "participants": 25
            }
          ],
          "summary": {
            "total": 12,
            "active": 8,
            "completed": 3,
            "upcoming": 1
          }
        }
        
        For Payroll Information:
        "data": {
          "salary_breakdown": {
            "basic": "₹50,000",
            "hra": "₹20,000",
            "da": "₹15,000",
            "special_allowance": "₹25,000",
            "bonus": "₹50,000"
          },
          "deductions": {
            "pf": "₹6,000",
            "tax": "₹8,500",
            "insurance": "₹1,500"
          },
          "summary": {
            "gross_salary": "₹1,60,000",
            "net_salary": "₹1,44,000",
            "total_ctc": "₹8,50,000"
          }
        }
        
        For Asset Management:
        "data": {
          "assets": [
            {
              "asset_id": "AST001",
              "name": "MacBook Pro",
              "category": "Laptop",
              "assigned_to": "John Doe",
              "status": "Assigned",
              "purchase_date": "15 Jan 2023"
            }
          ],
          "summary": {
            "total": 150,
            "assigned": 120,
            "available": 25,
            "maintenance": 5
          }
        }
        
        For Travel Requests:
        "data": {
          "travel_requests": [
            {
              "request_id": "TR001",
              "destination": "Mumbai",
              "purpose": "Client Meeting",
              "start_date": "25 Aug 2025",
              "end_date": "27 Aug 2025",
              "status": "Pending",
              "estimated_cost": "₹15,000"
            }
          ],
          "summary": {
            "total": 25,
            "pending": 8,
            "approved": 15,
            "rejected": 2
          }
        }
        
        For Overtime Requests:
        "data": {
          "overtime_records": [
            {
              "request_id": "OT001",
              "date": "20 Aug 2025",
              "hours": "3",
              "reason": "Project deadline",
              "status": "Approved",
              "rate": "1.5x"
            }
          ],
          "summary": {
            "total_hours": 45,
            "pending": 12,
            "approved": 28,
            "rejected": 5
          }
        }
        
        For Document Management:
        "data": {
          "documents": [
            {
              "doc_id": "DOC001",
              "name": "Employment Contract",
              "category": "Professional",
              "upload_date": "15 Jan 2023",
              "status": "Active",
              "size": "2.5 MB"
            }
          ],
          "summary": {
            "total": 500,
            "personal": 150,
            "professional": 250,
            "company": 100
          }
        }
        
        CRITICAL: Both details and data fields MUST follow the exact formats shown above. NEVER deviate from these structures.
        
        MANDATORY REQUEST_PAYLOAD FIELD:
        - request_payload field MUST ALWAYS be included in every response
        - This field should contain the exact API request parameters that were sent
        - Examples of request_payload:
          * For request list: {"page": 1, "limit": 20, "status": "all", "requestType": "all", "year": 2025}
          * For attendance: {"page": 1, "limit": 20, "status": "all", "month": "August", "year": 2025}
          * For dashboard: {"date": "2025-08-20"}
          * For simple requests: {}
        
        IMPORTANT: Return ONLY the JSON object, do NOT wrap it in markdown code blocks (```json) or any other formatting.
        
        Always be helpful, professional, and provide clear, actionable responses with clean, simplified data structures. NEVER forget to include the request_payload field.
        """

    def _make_api_request(self, url: str, method: str = "GET", headers: Dict = None, 
                         payload: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to HRMS APIs with error handling"""
        try:
            request_headers = headers or self.default_headers
            print(f"Making {method} request to: {url}")
            print(f"Headers: {request_headers}")
            if payload:
                print(f"Payload: {payload}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, json=payload, timeout=30)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            # Check if response is successful
            if response.status_code >= 400:
                error_detail = {
                    "error": f"HTTP {response.status_code} Error",
                    "url": url,
                    "method": method,
                    "status_code": response.status_code,
                    "response_text": response.text[:500],  # First 500 chars
                    "response_headers": dict(response.headers)
                }
                print(f"HTTP Error Details: {error_detail}")
                return error_detail
            
            # Try to parse JSON response
            try:
                data = response.json()
                print(f"Response data: {data}")
                
                # Add request metadata to the response
                if isinstance(data, dict):
                    data["request_payload"] = payload if payload else {}
                    data["api_url"] = url
                    data["http_method"] = method
                    data["response_status"] = response.status_code
                
                return data
            except json.JSONDecodeError as json_err:
                error_detail = {
                    "error": f"JSON Parse Error: {str(json_err)}",
                    "url": url,
                    "method": method,
                    "status_code": response.status_code,
                    "response_text": response.text[:500],
                    "raw_response": response.text
                }
                print(f"JSON Parse Error Details: {error_detail}")
                return error_detail
            
        except requests.exceptions.Timeout as e:
            error_detail = {
                "error": f"Request Timeout: {str(e)}",
                "url": url,
                "method": method,
                "timeout": "30 seconds"
            }
            print(f"Timeout Error Details: {error_detail}")
            return error_detail
        except requests.exceptions.ConnectionError as e:
            error_detail = {
                "error": f"Connection Error: {str(e)}",
                "url": url,
                "method": method
            }
            print(f"Connection Error Details: {error_detail}")
            return error_detail
        except requests.exceptions.RequestException as e:
            error_detail = {
                "error": f"Request Exception: {str(e)}",
                "url": url,
                "method": method,
                "exception_type": type(e).__name__
            }
            print(f"Request Exception Details: {error_detail}")
            return error_detail
        except Exception as e:
            error_detail = {
                "error": f"Unexpected Error: {str(e)}",
                "url": url,
                "method": method,
                "exception_type": type(e).__name__,
                "traceback": str(e)
            }
            print(f"Unexpected Error Details: {error_detail}")
            return error_detail

    # ------------------ API Functions ------------------

    def get_leave_balance(self) -> dict:
        print("Tool Call: get_leave_balance()")
        url = f"{self.base_url}/app/request/balance"
        try:
            result = self._make_api_request(url, method="POST")
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_leave_types(self) -> dict:
        print("Tool Call: get_leave_types()")
        url = f"{self.base_url}/app/request/types"
        try:
            result = self._make_api_request(url, method="POST")
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_attendance_list(self, 
                           month: str = None, 
                           year: int = None, 
                           date_filter: str = None, 
                           status: str = "all", 
                           page: int = 1, 
                           limit: int = 20) -> dict:
        print(f"Tool Call: get_attendance_list(month={month}, year={year}, date_filter={date_filter}, status={status}, page={page}, limit={limit})")
        
        # Set smart defaults if not provided
        if not month:
            month = datetime.now().strftime("%B")  # Current month name
        
        if not year:
            year = datetime.now().year  # Current year
            
        if not date_filter:
            date_filter = datetime.now().strftime("%Y-%m-%d")  # Current date
            
        url = f"{self.base_url}/app/attendance/attendance-list"
        payload = {
            "page": page,
            "limit": limit, 
            "status": status,
            "month": month, 
            "date_filter": date_filter, 
            "year": year
        }
        
        try:
            result = self._make_api_request(url, method="POST", payload=payload)
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_dashboard_overview(self,date: str = None) -> dict:
        print(f"Tool Call: get_dashboard_overview(date={date})")
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/app/dashboard/overview?date={date}"
        try:
            result = self._make_api_request(url, method="GET")
            print(f"Tool Response: {result}")
            
            # Simplify the response for frontend
            if "error" in result:
                return {"error": result["error"]}
            
            # If result has nested structure, simplify it
            if isinstance(result, dict) and len(result) == 1:
                # Extract the first (and likely only) key's value
                first_key = list(result.keys())[0]
                if isinstance(result[first_key], dict):
                    return result[first_key]
            
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_request_list(self, 
                        page: int = 1, 
                        limit: int = 20, 
                        status: str = "all", 
                        request_type: str = "all", 
                        year: int = None) -> dict:
        print(f"Tool Call: get_request_list(page={page}, limit={limit}, status={status}, request_type={request_type}, year={year})")
        
        # Set smart defaults if not provided
        if not year:
            year = datetime.now().year  # Current year
            
        url = f"{self.base_url}/app/request/list"
        payload = {
            "page": page, 
            "limit": limit, 
            "status": status, 
            "requestType": request_type, 
            "year": year
        }
        
        try:
            result = self._make_api_request(url, method="POST", payload=payload)
            print(f"Tool Response: {result}")
            
            # Check for API errors first
            if "error" in result:
                return {"error": result["error"]}
            
            # Check if the response is successful
            if result.get("success") == True and "data" in result:
                data = result["data"]
                
                # Extract requests and summary
                requests = data.get("requests", [])
                summary = data.get("summary", {})
                pagination = data.get("pagination", {})
                
                # Transform requests to simplified format
                simplified_requests = []
                for req in requests:
                    request_data = {
                        "type": req.get("requestTypeDisplay", req.get("requestType", "")),
                        "status": req.get("status", ""),
                        "applied": req.get("appliedAtFormatted", ""),
                        "dates": f"{req.get('startDateFormatted', '')} - {req.get('endDateFormatted', '')}",
                        "reason": req.get("reason", ""),
                        "id": req.get("id", "")
                    }
                    
                    # Add specific fields based on request type
                    if req.get("requestType") == "leave":
                        request_data["days"] = req.get("leaveDays", "")
                        request_data["leave_type"] = req.get("leaveTypeDisplay", "")
                    elif req.get("requestType") == "wfh":
                        request_data["location"] = req.get("location", "")
                    
                    simplified_requests.append(request_data)
                
                # Create simplified summary
                simplified_summary = {
                    "total": summary.get("total", {}).get("count", 0),
                    "leave": summary.get("leave", {}).get("count", 0),
                    "wfh": summary.get("wfh", {}).get("count", 0),
                    "expense": summary.get("expense", {}).get("count", 0),
                    "regularisation": summary.get("regularisation", {}).get("count", 0),
                    "compensatory_off": summary.get("compensatory_off", {}).get("count", 0)
                }
                
                # Return simplified response structure
                return {
                    "success": True,
                    "message": "Request list retrieved successfully",
                    "requests": simplified_requests,
                    "summary": simplified_summary,
                    "pagination": {
                        "total": pagination.get("total", 0),
                        "page": pagination.get("page", 1),
                        "total_pages": pagination.get("totalPages", 1)
                    }
                }
            else:
                # Handle case where response structure is different
                if "get_request_list_response" in result:
                    # Old nested structure
                    nested_data = result["get_request_list_response"]["result"]["data"]
                    return self._simplify_nested_response(nested_data)
                else:
                    return {"error": "Unexpected response structure"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    def _simplify_nested_response(self, data):
        """Helper method to simplify nested response structure"""
        try:
            requests = data.get("requests", [])
            summary = data.get("summary", {})
            pagination = data.get("pagination", {})
            
            # Transform requests
            simplified_requests = []
            for req in requests:
                request_data = {
                    "type": req.get("requestTypeDisplay", req.get("requestType", "")),
                    "status": req.get("status", ""),
                    "applied": req.get("appliedAtFormatted", ""),
                    "dates": f"{req.get('startDateFormatted', '')} - {req.get('endDateFormatted', '')}",
                    "reason": req.get("reason", ""),
                    "id": req.get("id", "")
                }
                
                if req.get("requestType") == "leave":
                    request_data["days"] = req.get("leaveDays", "")
                    request_data["leave_type"] = req.get("leaveTypeDisplay", "")
                elif req.get("requestType") == "wfh":
                    request_data["location"] = req.get("location", "")
                
                simplified_requests.append(request_data)
            
            # Transform summary
            simplified_summary = {
                "total": summary.get("total", {}).get("count", 0),
                "leave": summary.get("leave", {}).get("count", 0),
                "wfh": summary.get("wfh", {}).get("count", 0),
                "expense": summary.get("expense", {}).get("count", 0),
                "regularisation": summary.get("regularisation", {}).get("count", 0),
                "compensatory_off": summary.get("compensatory_off", {}).get("count", 0)
            }
            
            return {
                "success": True,
                "message": "Request list retrieved successfully",
                "requests": simplified_requests,
                "summary": simplified_summary,
                "pagination": {
                    "total": pagination.get("total", 0),
                    "page": pagination.get("page", 1),
                    "total_pages": pagination.get("totalPages", 1)
                }
            }
            
        except Exception as e:
            return {"error": f"Error simplifying response: {str(e)}"}

    def get_upcoming_celebrations(self, days_ahead: int = 30) -> dict:
        print(f"Tool Call: get_upcoming_celebrations(days_ahead={days_ahead})")
        url = f"{self.base_url}/app/sidebar/upcoming-celebrations"
        try:
            result = self._make_api_request(url, method="GET")
            print(f"Tool Response: {result}")
            
            # Check if there's an error in the result
            if "error" in result:
                error_detail = {
                    "error": f"get_upcoming_celebrations failed: {result['error']}",
                    "url": url,
                    "method": "GET",
                    "full_error": result
                }
                print(f"Celebrations Error Details: {error_detail}")
                return error_detail
            
            return result
        except Exception as e:
            error_detail = {
                "error": f"Exception in get_upcoming_celebrations: {str(e)}",
                "url": url,
                "method": "GET",
                "exception_type": type(e).__name__,
                "traceback": str(e)
            }
            print(f"Celebrations Exception Details: {error_detail}")
            return error_detail

    def get_employee_directory(self, 
                             page: int = 1, 
                             limit: int = 20, 
                             department: str = None, 
                             search: str = None) -> dict:
        print(f"Tool Call: get_employee_directory(page={page}, limit={limit}, department={department}, search={search})")
        url = f"{self.base_url}/app/sidebar/employee-directory"
        
        # Build query parameters if provided
        params = {}
        if page > 1:
            params["page"] = page
        if limit != 20:
            params["limit"] = limit
        if department:
            params["department"] = department
        if search:
            params["search"] = search
            
        # Add query parameters to URL if any
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"
            
        try:
            result = self._make_api_request(url, method="GET")
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_user_profile(self) -> dict:
        print("Tool Call: get_user_profile()")
        url = f"{self.base_url}/app/auth/profile"
        try:
            result = self._make_api_request(url, method="GET")
            print(f"Tool Response: {result}")
            return result
        except Exception as e:
            return {"error": str(e)}

    # ------------------ AI Agent Logic ------------------

    def generate_ai_response(self, user_message: str) -> dict:
        try:
            print(f"Generating AI response for message: {user_message}")
            
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                tools=[self.get_leave_balance, self.get_leave_types, self.get_attendance_list,
                    self.get_dashboard_overview, self.get_request_list, self.get_user_profile,
                    self.get_employee_directory, self.get_upcoming_celebrations]
            )

            print("Calling Gemini AI Model...")
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_message,
                config=config,
            )
            
            print(f"Gemini response received: {response.text}")
            return {"text": response.text}
            
        except Exception as e:
            error_detail = {
                "error": f"AI Generation Error: {str(e)}",
                "message": user_message,
                "exception_type": type(e).__name__,
                "traceback": str(e)
            }
            print(f"AI Generation Error Details: {error_detail}")
            return error_detail