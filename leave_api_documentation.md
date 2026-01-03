# Leave API Documentation

This document provides comprehensive information about the Leave API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

## Base URL
All endpoints are prefixed with `/api/web` (based on the router definition in the code)

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

## Leave API Endpoints

### 1. Leave Types

#### Get Leave Types
- **Method**: GET
- **URL**: `/api/web/leave/leave-types`
- **Description**: Fetches available leave types
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "Casual Leave",
      "code": "CL",
      "max_days_per_year": 12,
      "carry_forward": true,
      "encashable": false,
      "requires_approval": true
    }
  ]
}
```

### 2. Leave Requests

#### Get Leave Requests
- **Method**: GET
- **URL**: `/api/web/leave/requests`
- **Description**: Fetches leave requests
- **Query Parameters**:
  - `applicant_id` (optional): Filter by applicant ID
  - `status` (optional): Filter by status (comma-separated)
  - `leave_type` (optional): Filter by leave type
  - `from` (optional): Filter from date
  - `to` (optional): Filter to date
  - `department` (optional): Filter by department
  - `q` (optional): Search query
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
        "applicant_id": "string",
        "leave_type": "string",
        "from_date": "string",
        "to_date": "string",
        "duration_days": 5,
        "reason": "string",
        "status": "pending",
        "created_at": "string",
        "updated_at": "string",
        "applicant": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string",
          "department": "string",
          "designation": "string"
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

#### Apply Leave
- **Method**: POST
- **URL**: `/api/web/leave/requests`
- **Description**: Applies for leave
- **Request Body**:
```json
{
  "leave_type": "string",
  "from_date": "string",
  "to_date": "string",
  "reason": "string",
  "applicant_id": "string (optional, defaults to actor)"
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
    "duration_days": 0,
    "message": "Leave request created and routed for approval."
  }
}
```

#### Bulk Approve Leave Requests
- **Method**: POST
- **URL**: `/api/web/leave/requests/bulk-approve`
- **Description**: Bulk approves leave requests
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
    "results": [
      {
        "id": "string",
        "success": true
      }
    ]
  }
}
```

#### Get Leave Request by ID
- **Method**: GET
- **URL**: `/api/web/leave/requests/{requestId}`
- **Description**: Fetches a specific leave request
- **Path Parameters**:
  - `requestId`: Request ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "applicant_id": "string",
    "leave_type": "string",
    "from_date": "string",
    "to_date": "string",
    "duration_days": 5,
    "reason": "string",
    "status": "pending",
    "created_at": "string",
    "updated_at": "string",
    "applicant": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string",
      "department": "string",
      "designation": "string"
    }
  }
}
```

#### Leave Action
- **Method**: POST
- **URL**: `/api/web/leave/requests/{requestId}/action`
- **Description**: Performs an action on a leave request
- **Path Parameters**:
  - `requestId`: Request ID
- **Request Body**:
```json
{
  "action": "approve|reject|cancel|forward|request_changes",
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
    "status": "approved",
    "message": "Leave request approved successfully"
  }
}
```

### 3. Leave Balances

#### Get Leave Balances
- **Method**: GET
- **URL**: `/api/web/leave/balances/{employeeId}`
- **Description**: Fetches leave balances for an employee
- **Path Parameters**:
  - `employeeId`: Employee ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "leave_type": "string",
      "opening": 0,
      "accrued": 0,
      "taken": 0,
      "pending": 0,
      "adjusted": 0,
      "available": 0
    }
  ]
}
```

#### Get Leave History
- **Method**: GET
- **URL**: `/api/web/leave/history/{employeeId}`
- **Description**: Fetches leave history for an employee
- **Path Parameters**:
  - `employeeId`: Employee ID
- **Query Parameters**:
  - `year` (optional): Year to filter
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "requests": [
      {
        "id": "string",
        "from_date": "string",
        "to_date": "string",
        "status": "string",
        "duration_days": 0
      }
    ],
    "transactions": [
      {
        "type": "string",
        "leave_type": "string",
        "delta": 0,
        "date": "string",
        "reason": "string"
      }
    ],
    "year": 2024
  }
}
```

#### Adjust Balance
- **Method**: POST
- **URL**: `/api/web/leave/balances/{employeeId}/adjust`
- **Description**: Adjusts leave balance for an employee
- **Path Parameters**:
  - `employeeId`: Employee ID
- **Request Body**:
```json
{
  "leave_type": "string",
  "delta": 5,
  "reason": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Balance adjusted by 5 for leave_type",
    "new_balance": 10
  }
}
```

### 4. Holidays

#### Get Holidays
- **Method**: GET
- **URL**: `/api/web/leave/holidays`
- **Description**: Fetches holidays
- **Query Parameters**:
  - `year` (optional): Year to filter
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "New Year",
      "date": "2024-01-01",
      "type": "public"
    }
  ]
}
```

#### Get Blackout Dates
- **Method**: GET
- **URL**: `/api/web/leave/blackout-dates`
- **Description**: Fetches blackout dates
- **Query Parameters**:
  - `year` (optional): Year to filter
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "Company Event",
      "date": "2024-01-15",
      "type": "company"
    }
  ]
}
```

### 5. Leave Policies

#### Get Leave Policies
- **Method**: GET
- **URL**: `/api/web/leave/policies`
- **Description**: Fetches leave policies
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "name": "Annual Leave Policy",
      "description": "string",
      "rules": {}
    }
  ]
}
```

#### Create Leave Policy
- **Method**: POST
- **URL**: `/api/web/leave/policies`
- **Description**: Creates a new leave policy
- **Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "rules": {}
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
    "description": "string",
    "rules": {},
    "created_at": "string"
  }
}
```

#### Get Leave Policy by ID
- **Method**: GET
- **URL**: `/api/web/leave/policies/{policyId}`
- **Description**: Fetches a specific leave policy
- **Path Parameters**:
  - `policyId`: Policy ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "name": "string",
    "description": "string",
    "rules": {},
    "created_at": "string"
  }
}
```

### 6. Calendar

#### Get Team Calendar
- **Method**: GET
- **URL**: `/api/web/leave/calendar/team`
- **Description**: Fetches team leave calendar
- **Query Parameters**:
  - `month`: Month (1-12)
  - `year`: Year
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "month": 1,
    "year": 2024,
    "events": [
      {
        "id": "string",
        "from_date": "string",
        "to_date": "string",
        "status": "approved",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        }
      }
    ],
    "holidays": [
      {
        "id": "string",
        "name": "New Year",
        "date": "2024-01-01"
      }
    ]
  }
}
```

#### Get My Calendar
- **Method**: GET
- **URL**: `/api/web/leave/calendar/my`
- **Description**: Fetches personal leave calendar
- **Query Parameters**:
  - `month`: Month (1-12)
  - `year`: Year
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "month": 1,
    "year": 2024,
    "events": [
      {
        "id": "string",
        "from_date": "string",
        "to_date": "string",
        "status": "approved"
      }
    ],
    "holidays": [
      {
        "id": "string",
        "name": "New Year",
        "date": "2024-01-01"
      }
    ]
  }
}
```

### 7. Encashment

#### Request Encashment
- **Method**: POST
- **URL**: `/api/web/leave/encash`
- **Description**: Requests leave encashment
- **Request Body**:
```json
{
  "leave_type": "string",
  "days": 5,
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
    "message": "Encashment request submitted for approval"
  }
}
```

### 8. Stats

#### Get Leave Stats
- **Method**: GET
- **URL**: `/api/web/leave/stats`
- **Description**: Fetches leave statistics
- **Query Parameters**:
  - `department` (optional): Filter by department
  - `location_id` (optional): Filter by location
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "pending_requests": 5,
    "approved_this_month": 0,
    "rejected_this_month": 0,
    "upcoming_leaves": 0,
    "on_leave_today": 0,
    "leave_by_type": []
  }
}
```

#### Get Filter Options
- **Method**: GET
- **URL**: `/api/web/leave/filters`
- **Description**: Fetches leave filter options
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "departments": [],
    "leave_types": []
  }
}
```

## Common HTTP Status Codes
- `200`: Success
- `201`: Created
- `202`: Accepted
- `400`: Bad Request - Validation error
- `401`: Unauthorized - Invalid or missing token
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `422`: Unprocessable Entity - Validation failed
- `500`: Internal Server Error

## Notes for Frontend Developers
1. Always include the Authorization header with a valid JWT token
2. Check the `success` field in responses to determine if the operation was successful
3. Use the pagination parameters for list endpoints (page, page_size)
4. For leave requests, use the action endpoint to approve/reject requests
5. The API provides both individual and bulk operations for efficiency