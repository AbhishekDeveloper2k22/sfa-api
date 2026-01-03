# Expense API Documentation

This document provides comprehensive information about the Expense API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Expense API Endpoints

### 1. Categories

#### Get Categories
- **Method**: GET
- **URL**: `/api/web/expense/categories`
- **Description**: Fetches expense categories
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
      "description": "string",
      "created_at": "string"
    }
  ]
}
```

### 2. Claims

#### Get Claims
- **Method**: GET
- **URL**: `/api/web/expense/claims`
- **Description**: Fetches expense claims
- **Query Parameters**:
  - `status` (optional): Filter by status
  - `employee_id` (optional): Filter by employee ID
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
        "status": "draft|submitted|approved|rejected|settled",
        "total_amount": 0,
        "submitted_at": "string",
        "approved_at": "string",
        "settled_at": "string",
        "items": [
          {
            "id": "string",
            "category": "string",
            "amount": 0,
            "date": "string",
            "description": "string"
          }
        ],
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        }
      }
    ],
    "meta": {
      "total": 0,
      "page": 1,
      "page_size": 25,
      "total_pages": 1
    }
  }
}
```

#### Create Claim
- **Method**: POST
- **URL**: `/api/web/expense/claims`
- **Description**: Creates a new expense claim
- **Request Body**:
```json
{
  "employee_id": "string",
  "items": [
    {
      "category": "string",
      "amount": 0,
      "date": "string",
      "description": "string"
    }
  ]
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
    "status": "draft",
    "total_amount": 0,
    "items": [
      {
        "id": "string",
        "category": "string",
        "amount": 0,
        "date": "string",
        "description": "string"
      }
    ]
  }
}
```

#### Get Claim by ID
- **Method**: GET
- **URL**: `/api/web/expense/claims/{id}`
- **Description**: Fetches a specific expense claim
- **Path Parameters**:
  - `id`: Claim ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "employee_id": "string",
    "status": "draft|submitted|approved|rejected|settled",
    "total_amount": 0,
    "submitted_at": "string",
    "approved_at": "string",
    "settled_at": "string",
    "items": [
      {
        "id": "string",
        "category": "string",
        "amount": 0,
        "date": "string",
        "description": "string"
      }
    ],
    "employee": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string"
    }
  }
}
```

#### Update Claim
- **Method**: PUT
- **URL**: `/api/web/expense/claims/{id}`
- **Description**: Updates an expense claim
- **Path Parameters**:
  - `id`: Claim ID
- **Request Body**:
```json
{
  "items": [
    {
      "id": "string (optional, for updates)",
      "category": "string",
      "amount": 0,
      "date": "string",
      "description": "string"
    }
  ]
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
    "employee_id": "string",
    "status": "draft",
    "total_amount": 0,
    "items": [
      {
        "id": "string",
        "category": "string",
        "amount": 0,
        "date": "string",
        "description": "string"
      }
    ]
  }
}
```

#### Submit Claim
- **Method**: POST
- **URL**: `/api/web/expense/claims/{id}/submit`
- **Description**: Submits an expense claim for approval
- **Path Parameters**:
  - `id`: Claim ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "submitted",
    "message": "Claim submitted successfully"
  }
}
```

#### Settle Claim
- **Method**: POST
- **URL**: `/api/web/expense/claims/{id}/settle`
- **Description**: Sets an expense claim as settled
- **Path Parameters**:
  - `id`: Claim ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "settled",
    "message": "Claim settled successfully"
  }
}
```

#### Preview Claim
- **Method**: POST
- **URL**: `/api/web/expense/claims/{id}/preview`
- **Description**: Gets a preview of an expense claim
- **Path Parameters**:
  - `id`: Claim ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "total_amount": 0,
    "items": [
      {
        "category": "string",
        "amount": 0,
        "count": 0
      }
    ]
  }
}
```

#### Claim Action
- **Method**: POST
- **URL**: `/api/web/expense/claims/{id}/{action}`
- **Description**: Performs an action on a claim (approve, reject, etc.)
- **Path Parameters**:
  - `id`: Claim ID
  - `action`: Action to perform (approve, reject, etc.)
- **Request Body**:
```json
{
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
    "message": "Action completed successfully"
  }
}
```

### 3. Travel

#### Get Travel Requests
- **Method**: GET
- **URL**: `/api/web/expense/travel`
- **Description**: Fetches travel requests
- **Query Parameters**:
  - `status` (optional): Filter by status
  - `employee_id` (optional): Filter by employee ID
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
        "status": "draft|submitted|approved|rejected",
        "destination": "string",
        "from_date": "string",
        "to_date": "string",
        "purpose": "string",
        "estimated_cost": 0,
        "submitted_at": "string",
        "approved_at": "string",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        }
      }
    ],
    "meta": {
      "total": 0,
      "page": 1,
      "page_size": 25,
      "total_pages": 1
    }
  }
}
```

#### Create Travel Request
- **Method**: POST
- **URL**: `/api/web/expense/travel`
- **Description**: Creates a new travel request
- **Request Body**:
```json
{
  "employee_id": "string",
  "destination": "string",
  "from_date": "string",
  "to_date": "string",
  "purpose": "string",
  "estimated_cost": 0
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
    "status": "draft",
    "destination": "string",
    "from_date": "string",
    "to_date": "string",
    "purpose": "string",
    "estimated_cost": 0
  }
}
```

#### Get Travel Request by ID
- **Method**: GET
- **URL**: `/api/web/expense/travel/{id}`
- **Description**: Fetches a specific travel request
- **Path Parameters**:
  - `id`: Travel request ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "employee_id": "string",
    "status": "draft|submitted|approved|rejected",
    "destination": "string",
    "from_date": "string",
    "to_date": "string",
    "purpose": "string",
    "estimated_cost": 0,
    "submitted_at": "string",
    "approved_at": "string",
    "employee": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string"
    }
  }
}
```

#### Travel Action
- **Method**: POST
- **URL**: `/api/web/expense/travel/{id}/{action}`
- **Description**: Performs an action on a travel request (approve, reject, etc.)
- **Path Parameters**:
  - `id`: Travel request ID
  - `action`: Action to perform (approve, reject, etc.)
- **Request Body**:
```json
{
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
    "message": "Action completed successfully"
  }
}
```

### 4. Advances

#### Get Advances
- **Method**: GET
- **URL**: `/api/web/expense/advances`
- **Description**: Fetches expense advances
- **Query Parameters**:
  - `status` (optional): Filter by status
  - `employee_id` (optional): Filter by employee ID
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
        "amount": 0,
        "status": "pending|approved|disbursed|closed",
        "requested_at": "string",
        "approved_at": "string",
        "disbursed_at": "string",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        }
      }
    ],
    "meta": {
      "total": 0,
      "page": 1,
      "page_size": 25,
      "total_pages": 1
    }
  }
}
```

#### Create Advance
- **Method**: POST
- **URL**: `/api/web/expense/advances`
- **Description**: Creates a new expense advance
- **Request Body**:
```json
{
  "employee_id": "string",
  "amount": 0,
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
    "employee_id": "string",
    "amount": 0,
    "status": "pending",
    "reason": "string"
  }
}
```

#### Disburse Advance
- **Method**: POST
- **URL**: `/api/web/expense/advances/{id}/disburse`
- **Description**: Disburses an expense advance
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
    "status": "disbursed",
    "message": "Advance disbursed successfully"
  }
}
```

### 5. Reports & Misc

#### Get Ledger
- **Method**: GET
- **URL**: `/api/web/expense/ledger`
- **Description**: Fetches expense ledger
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
      "type": "claim|advance|travel",
      "amount": 0,
      "date": "string",
      "status": "string"
    }
  ]
}
```

#### Get Stats
- **Method**: GET
- **URL**: `/api/web/expense/stats`
- **Description**: Fetches expense statistics
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_claims": 0,
    "pending_claims": 0,
    "total_amount": 0,
    "monthly_expenses": []
  }
}
```

#### Export Expenses
- **Method**: POST
- **URL**: `/api/web/expense/export`
- **Description**: Exports expenses data
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "download_url": "string",
    "expires_at": "string"
  }
}
```

#### Extract Receipt
- **Method**: POST
- **URL**: `/api/web/expense/receipts/{uploadId}/extract`
- **Description**: Extracts data from a receipt image
- **Path Parameters**:
  - `uploadId`: Upload ID of the receipt image
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "items": [
      {
        "category": "string",
        "amount": 0,
        "date": "string",
        "description": "string"
      }
    ]
  }
}
```

#### Get Filter Options
- **Method**: GET
- **URL**: `/api/web/expense/filter-options`
- **Description**: Fetches filter options for expense module
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "categories": [],
    "employees": [],
    "statuses": []
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
4. For claims, follow the sequence: create → update → submit → approval → settle
5. The API provides both individual and bulk operations for efficiency