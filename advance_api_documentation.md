# Advance API Documentation

This document provides comprehensive information about the Advance API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Advance API Endpoints

### 1. Advance Requests

#### Get Advances
- **Method**: GET
- **URL**: `/api/web/advance`
- **Description**: Fetches advance requests
- **Query Parameters**:
  - `status` (optional): Filter by status
  - `employee_id` (optional): Filter by employee ID
  - `department` (optional): Filter by department
  - `search` (optional): Search term
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
        "amount": 10000,
        "reason": "string",
        "status": "pending",
        "requested_at": "string",
        "approved_at": "string",
        "disbursed_at": "string",
        "total_repaid": 0,
        "remaining_balance": 10000,
        "employee": {
          "id": "string",
          "name": "string",
          "employee_code": "string",
          "department": "string",
          "designation": "string",
          "salary": 0
        }
      }
    ],
    "stats": {
      "total": 10,
      "pending": 2,
      "approved": 3,
      "active": 4,
      "closed": 1,
      "rejected": 0,
      "total_disbursed": 50000,
      "total_recovered": 10000,
      "total_outstanding": 40000,
      "pending_amount": 20000
    }
  }
}
```

#### Create Advance
- **Method**: POST
- **URL**: `/api/web/advance`
- **Description**: Creates a new advance request
- **Request Body**:
```json
{
  "employee_id": "string",
  "amount": 10000,
  "reason": "string",
  "reason_details": "string (optional)"
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
    "employee_id": "string",
    "amount": 10000,
    "reason": "string",
    "status": "pending",
    "requested_at": "string",
    "total_repaid": 0,
    "remaining_balance": 10000,
    "employee": {
      "id": "string",
      "name": "string",
      "employee_code": "string",
      "department": "string",
      "designation": "string",
      "salary": 0
    }
  }
}
```

#### Get Advance by ID
- **Method**: GET
- **URL**: `/api/web/advance/{id}`
- **Description**: Fetches a specific advance request
- **Path Parameters**:
  - `id`: Advance ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "employee_id": "string",
    "amount": 10000,
    "reason": "string",
    "status": "pending",
    "requested_at": "string",
    "approved_at": "string",
    "disbursed_at": "string",
    "total_repaid": 0,
    "remaining_balance": 10000,
    "repayment_history": [],
    "employee": {
      "id": "string",
      "name": "string",
      "employee_code": "string",
      "department": "string",
      "designation": "string",
      "salary": 0
    }
  }
}
```

#### Approve Advance
- **Method**: POST
- **URL**: `/api/web/advance/{id}/approve`
- **Description**: Approves an advance request
- **Path Parameters**:
  - `id`: Advance ID
- **Request Body**:
```json
{
  "approver_name": "string (optional)"
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
    "approved_at": "string",
    "approved_by": "string"
  }
}
```

#### Reject Advance
- **Method**: POST
- **URL**: `/api/web/advance/{id}/reject`
- **Description**: Rejects an advance request
- **Path Parameters**:
  - `id`: Advance ID
- **Request Body**:
```json
{
  "reason": "string",
  "rejecter_name": "string (optional)"
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
    "status": "rejected",
    "rejected_at": "string",
    "rejected_by": "string",
    "rejection_reason": "string"
  }
}
```

#### Disburse Advance
- **Method**: POST
- **URL**: `/api/web/advance/{id}/disburse`
- **Description**: Disburses an advance
- **Path Parameters**:
  - `id`: Advance ID
- **Request Body**:
```json
{
  "disbursement_mode": "string (optional, default: Bank Transfer)"
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
    "status": "active",
    "disbursed_at": "string",
    "disbursement_mode": "string"
  }
}
```

#### Record Repayment
- **Method**: POST
- **URL**: `/api/web/advance/{id}/repayments`
- **Description**: Records an advance repayment
- **Path Parameters**:
  - `id`: Advance ID
- **Request Body**:
```json
{
  "amount": 2000,
  "date": "string (optional)",
  "mode": "string (optional, default: Cash)",
  "remarks": "string (optional)",
  "recorded_by": "string (optional)"
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
    "status": "active",
    "total_repaid": 2000,
    "remaining_balance": 8000,
    "closed_at": null,
    "repayment_history": [
      {
        "id": "string",
        "date": "string",
        "amount": 2000,
        "mode": "string",
        "remarks": "string",
        "recorded_by": "string"
      }
    ]
  }
}
```

### 2. Reference Data

#### Get Employees
- **Method**: GET
- **URL**: `/api/web/advance/employees`
- **Description**: Fetches employees for advance requests
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
      "employee_code": "string",
      "department": "string",
      "designation": "string",
      "salary": 0
    }
  ]
}
```

#### Get Advance Reasons
- **Method**: GET
- **URL**: `/api/web/advance/advance-reasons`
- **Description**: Fetches available advance reasons
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    "Medical Emergency",
    "Wedding Expenses",
    "Home Renovation",
    "Education Fees",
    "Family Emergency",
    "Vehicle Purchase",
    "Festival Expenses",
    "Debt Consolidation",
    "Other Personal Needs"
  ]
}
```

#### Get Payment Modes
- **Method**: GET
- **URL**: `/api/web/advance/payment-modes`
- **Description**: Fetches available payment modes
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    "Salary Deduction",
    "Cash",
    "UPI Transfer",
    "Bank Transfer",
    "Cheque"
  ]
}
```

#### Get Departments
- **Method**: GET
- **URL**: `/api/web/advance/departments`
- **Description**: Fetches departments
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    "string"
  ]
}
```

### 3. Validation

#### Check Active Advance
- **Method**: GET
- **URL**: `/api/web/advance/employees/{employeeId}/active-advance`
- **Description**: Checks if an employee has an active advance
- **Path Parameters**:
  - `employeeId`: Employee ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "hasActive": true,
    "advance": {
      "id": "string",
      "status": "string",
      "amount": 0,
      "remaining_balance": 0
    }
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
4. For advance requests, follow the sequence: create → approve → disburse → record repayments
5. The API provides both individual and bulk operations for efficiency
6. For advance requests, check active advances before creating new ones