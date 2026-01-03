# Attendance API Documentation

This document provides comprehensive information about the Attendance API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

## Base URL
All endpoints are prefixed with `/api/v1` (based on the router definition in the code)

## Authentication
All endpoints require a valid JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

The JWT token must include `tenant_id` and `user_id` claims.

## Common Response Format
All API responses follow this structure:
```json
{
  "success": true/false,
  "msg": "Human-readable message",
  "statuscode": HTTP status code,
  "data": { /* response data */ }
}
```

## Error Handling
When an error occurs, the response includes an error object:
```json
{
  "success": false,
  "msg": "Error message",
  "statuscode": 400,
  "data": {
    "error": {
      "code": "ERROR_CODE",
      "message": "Error message",
      "details": []
    }
  }
}
```

## Endpoints

### 1. Live Attendance APIs

#### Get Live Attendance
- **Method**: GET
- **URL**: `/api/v1/live`
- **Description**: Fetches real-time attendance data
- **Query Parameters**:
  - `q` (optional): Search term for employee name or code
  - `status` (optional): Filter by attendance status
  - `department` (optional): Filter by department
  - `shift_id` (optional): Filter by shift ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "data": [
      {
        "id": "string",
        "employee_id": "string",
        "current_status": "string",
        "in_time": "string",
        "out_time": "string",
        "work_duration_minutes": "number",
        "late_minutes": "number",
        "ot_minutes": "number",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string",
          "department": "string",
          "designation": "string"
        },
        "shift": "string",
        "device": "string",
        "location": "string"
      }
    ],
    "stats": {
      "present_today": 0,
      "checked_in": 0,
      "late_today": 0,
      "absent_today": 0,
      "on_leave_today": 0,
      "avg_work_hours": 0
    }
  }
}
```

### 2. Daily Attendance APIs

#### Get Daily Attendance
- **Method**: GET
- **URL**: `/api/v1/daily`
- **Description**: Fetches daily attendance records
- **Query Parameters**:
  - `employee_id` (optional): Filter by employee ID
  - `date` (optional): Filter by specific date (YYYY-MM-DD)
  - `from_date` (optional): Filter from date (YYYY-MM-DD)
  - `to_date` (optional): Filter to date (YYYY-MM-DD)
  - `status` (optional): Filter by status
  - `department` (optional): Filter by department
  - `page` (optional, default: 1): Page number
  - `page_size` (optional, default: 25): Items per page
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "data": [
      {
        "id": "string",
        "employee_id": "string",
        "date": "string",
        "status": "string",
        "in_time": "string",
        "out_time": "string",
        "work_duration_minutes": "number",
        "late_minutes": "number",
        "ot_minutes": "number",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string",
          "department": "string",
          "designation": "string"
        },
        "shift": "string",
        "device": "string",
        "location": "string"
      }
    ],
    "meta": {
      "page": 1,
      "page_size": 25,
      "total": 100,
      "total_pages": 4
    }
  }
}
```

### 3. Monthly Attendance APIs

#### Get Monthly Attendance
- **Method**: GET
- **URL**: `/api/v1/{employeeId}`
- **Description**: Fetches monthly attendance records for an employee
- **Path Parameters**:
  - `employeeId`: Employee ID
- **Query Parameters**:
  - `month`: Month in YYYY-MM format (e.g., "2023-07")
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "records": [
      {
        "id": "string",
        "date": "string",
        "status": "string",
        "in_time": "string",
        "out_time": "string",
        "work_duration_minutes": "number",
        "late_minutes": "number",
        "ot_minutes": "number"
      }
    ],
    "summary": {
      "total_days": 30,
      "present_days": 22,
      "absent_days": 2,
      "late_days": 3,
      "leave_days": 4,
      "half_days": 1,
      "weekly_off_days": 4,
      "total_late_minutes": 45,
      "total_ot_minutes": 120,
      "avg_work_hours": 8
    },
    "employee": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string",
      "department": "string",
      "designation": "string"
    }
  }
}
```

### 4. Manual/Correction Requests APIs

#### Get Manual Requests
- **Method**: GET
- **URL**: `/api/v1/manual-requests`
- **Description**: Fetches manual attendance correction requests
- **Query Parameters**:
  - `employee_id` (optional): Filter by employee ID
  - `status` (optional): Filter by request status
  - `request_type` (optional): Filter by request type
  - `page` (optional, default: 1): Page number
  - `page_size` (optional, default: 25): Items per page
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "data": [
      {
        "id": "string",
        "employee_id": "string",
        "date": "string",
        "request_type": "string",
        "status": "pending|approved|rejected",
        "reason": "string",
        "created_at": "string",
        "updated_at": "string",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        }
      }
    ],
    "meta": {
      "page": 1,
      "page_size": 25,
      "total": 10,
      "total_pages": 1
    }
  }
}
```

#### Create Manual Request
- **Method**: POST
- **URL**: `/api/v1/manual-requests`
- **Description**: Create a manual attendance correction request
- **Request Body**:
```json
{
  "employee_id": "string",
  "date": "string",
  "request_type": "punch_correction|attendance_correction",
  "reason": "string",
  "in_time": "string (optional)",
  "out_time": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 201,
  "data": {
    "id": "string",
    "status": "pending",
    "message": "Request submitted successfully"
  }
}
```

#### Action Manual Request
- **Method**: POST
- **URL**: `/api/v1/manual-requests/{requestId}/action`
- **Description**: Approve or reject a manual request
- **Path Parameters**:
  - `requestId`: Request ID
- **Request Body**:
```json
{
  "action": "approve|reject",
  "comment": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "approved|rejected",
    "message": "Request approved/rejected successfully"
  }
}
```

### 5. Overtime (OT) Requests APIs

#### Get OT Requests
- **Method**: GET
- **URL**: `/api/v1/ot-requests`
- **Description**: Fetches overtime requests
- **Query Parameters**:
  - `employee_id` (optional): Filter by employee ID
  - `status` (optional): Filter by request status
  - `page` (optional, default: 1): Page number
  - `page_size` (optional, default: 25): Items per page
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "data": [
      {
        "id": "string",
        "employee_id": "string",
        "date": "string",
        "status": "pending|approved|rejected",
        "hours": "number",
        "reason": "string",
        "created_at": "string",
        "updated_at": "string",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        }
      }
    ],
    "meta": {
      "page": 1,
      "page_size": 25,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

#### Create OT Request
- **Method**: POST
- **URL**: `/api/v1/ot-requests`
- **Description**: Create an overtime request
- **Request Body**:
```json
{
  "employee_id": "string",
  "date": "string",
  "hours": "number",
  "reason": "string"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 201,
  "data": {
    "id": "string",
    "status": "pending",
    "message": "OT request submitted successfully"
  }
}
```

#### Action OT Request
- **Method**: POST
- **URL**: `/api/v1/ot-requests/{requestId}/action`
- **Description**: Approve or reject an OT request
- **Path Parameters**:
  - `requestId`: Request ID
- **Request Body**:
```json
{
  "action": "approve|reject",
  "comment": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "approved|rejected",
    "message": "OT request approved/rejected successfully"
  }
}
```

#### Bulk Approve OT Requests
- **Method**: POST
- **URL**: `/api/v1/ot-requests/bulk-approve`
- **Description**: Bulk approve OT requests
- **Request Body**:
```json
{
  "ids": ["string"],
  "comment": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": 5,
    "failed": 0,
    "message": "Bulk approval completed"
  }
}
```

### 6. Punch/Event APIs

#### Record Punch
- **Method**: POST
- **URL**: `/api/v1/punch`
- **Description**: Record a punch event
- **Request Body**:
```json
{
  "employee_id": "string",
  "timestamp": "string",
  "type": "in|out",
  "device_id": "string (optional)",
  "location": {
    "lat": "number",
    "lng": "number"
  },
  "device_info": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "status": "accepted",
    "event_id": "string",
    "message": "Punch recorded successfully"
  }
}
```

#### Get Events
- **Method**: GET
- **URL**: `/api/v1/events`
- **Description**: Get attendance events
- **Query Parameters**:
  - `employee_id` (optional): Filter by employee ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "employee_id": "string",
      "timestamp": "string",
      "type": "in|out",
      "device_id": "string",
      "location": {
        "lat": "number",
        "lng": "number"
      },
      "device_info": "string"
    }
  ]
}
```

### 7. Shift APIs

#### Get Shifts
- **Method**: GET
- **URL**: `/api/v1/shifts`
- **Description**: Get all shifts
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "string",
      "code": "string",
      "start_time": "string",
      "end_time": "string",
      "break_start": "string",
      "break_end": "string",
      "grace_period": "number",
      "late_mark_threshold": "number",
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

#### Get Shift
- **Method**: GET
- **URL**: `/api/v1/shifts/{shiftId}`
- **Description**: Get a specific shift
- **Path Parameters**:
  - `shiftId`: Shift ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "name": "string",
    "code": "string",
    "start_time": "string",
    "end_time": "string",
    "break_start": "string",
    "break_end": "string",
    "grace_period": "number",
    "late_mark_threshold": "number",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Create Shift
- **Method**: POST
- **URL**: `/api/v1/shifts`
- **Description**: Create a new shift
- **Request Body**:
```json
{
  "name": "string",
  "code": "string",
  "start_time": "string",
  "end_time": "string",
  "break_start": "string (optional)",
  "break_end": "string (optional)",
  "grace_period": "number (optional)",
  "late_mark_threshold": "number (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 201,
  "data": {
    "id": "string",
    "name": "string",
    "code": "string",
    "start_time": "string",
    "end_time": "string",
    "break_start": "string",
    "break_end": "string",
    "grace_period": "number",
    "late_mark_threshold": "number",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Update Shift
- **Method**: PUT
- **URL**: `/api/v1/shifts/{shiftId}`
- **Description**: Update a shift
- **Path Parameters**:
  - `shiftId`: Shift ID
- **Request Body**:
```json
{
  "name": "string (optional)",
  "code": "string (optional)",
  "start_time": "string (optional)",
  "end_time": "string (optional)",
  "break_start": "string (optional)",
  "break_end": "string (optional)",
  "grace_period": "number (optional)",
  "late_mark_threshold": "number (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "name": "string",
    "code": "string",
    "start_time": "string",
    "end_time": "string",
    "break_start": "string",
    "break_end": "string",
    "grace_period": "number",
    "late_mark_threshold": "number",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

### 8. Roster APIs

#### Get Rosters
- **Method**: GET
- **URL**: `/api/v1/rosters`
- **Description**: Get roster assignments
- **Query Parameters**:
  - `employee_id` (optional): Filter by employee ID
  - `shift_id` (optional): Filter by shift ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "employee_id": "string",
      "shift_id": "string",
      "date": "string",
      "start_date": "string",
      "end_date": "string",
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

#### Assign Roster
- **Method**: POST
- **URL**: `/api/v1/rosters/assign`
- **Description**: Assign a roster to an employee
- **Request Body**:
```json
{
  "employee_id": "string",
  "shift_id": "string",
  "date": "string",
  "start_date": "string (optional)",
  "end_date": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 201,
  "data": {
    "assignment_id": "string",
    "status": "created",
    "message": "Roster assigned successfully"
  }
}
```

#### Bulk Assign Roster
- **Method**: POST
- **URL**: `/api/v1/rosters/bulk-assign`
- **Description**: Bulk assign roster to multiple employees
- **Request Body**:
```json
{
  "employee_ids": ["string"],
  "shift_id": "string",
  "date": "string (optional)",
  "start_date": "string (optional)",
  "end_date": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": 5,
    "failed": 0,
    "message": "Bulk roster assignment completed"
  }
}
```

#### Delete Roster Assignment
- **Method**: DELETE
- **URL**: `/api/v1/rosters/{assignmentId}`
- **Description**: Delete a roster assignment
- **Path Parameters**:
  - `assignmentId`: Assignment ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Roster assignment deleted successfully"
  }
}
```

### 9. Device & Geofence APIs

#### Get Devices
- **Method**: GET
- **URL**: `/api/v1/devices`
- **Description**: Get attendance devices
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "string",
      "device_id": "string",
      "location": {
        "lat": "number",
        "lng": "number",
        "radius": "number"
      },
      "allowed": true,
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

#### Register Device
- **Method**: POST
- **URL**: `/api/v1/devices`
- **Description**: Register a new attendance device
- **Request Body**:
```json
{
  "name": "string",
  "device_id": "string",
  "location": {
    "lat": "number",
    "lng": "number",
    "radius": "number"
  }
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 201,
  "data": {
    "id": "string",
    "name": "string",
    "device_id": "string",
    "location": {
      "lat": "number",
      "lng": "number",
      "radius": "number"
    },
    "allowed": true,
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Geofences
- **Method**: GET
- **URL**: `/api/v1/geofences`
- **Description**: Get geofence configurations
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "string",
      "location": {
        "lat": "number",
        "lng": "number",
        "radius": "number"
      },
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

## Common HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request - Validation error
- `401`: Unauthorized - Invalid or missing token
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `422`: Unprocessable Entity - Validation failed
- `500`: Internal Server Error

## Notes for Frontend Developers
1. Always include the Authorization header with a valid JWT token
2. Check the `success` field in responses to determine if the operation was successful
3. Handle pagination parameters for list endpoints (page, page_size)
4. Use the `requestId` parameter for action endpoints to approve/reject requests
5. The attendance API supports both individual and bulk operations for efficiency
6. For punch operations, ensure accurate timestamp and location data
7. The API provides both real-time (live) and historical (daily, monthly) attendance data