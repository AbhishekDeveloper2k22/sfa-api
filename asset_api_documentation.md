# Asset API Documentation

This document provides comprehensive information about the Asset API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Asset API Endpoints

### 1. Categories & Locations

#### Get Categories
- **Method**: GET
- **URL**: `/api/web/asset/categories`
- **Description**: Fetches asset categories
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

#### Get Locations
- **Method**: GET
- **URL**: `/api/web/asset/locations`
- **Description**: Fetches asset locations
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
      "address": "string",
      "created_at": "string"
    }
  ]
}
```

### 2. Assets

#### Get Assets
- **Method**: GET
- **URL**: `/api/web/asset/assets`
- **Description**: Fetches assets
- **Query Parameters**:
  - `status` (optional): Filter by status (available, assigned, maintenance, disposed)
  - `category` (optional): Filter by category
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
        "name": "string",
        "category": "string",
        "location": "string",
        "status": "available|assigned|maintenance|disposed",
        "purchase_date": "string",
        "purchase_price": 0,
        "serial_number": "string",
        "assigned_to": "string (employee id)",
        "assigned_at": "string",
        "assigned_to_details": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        },
        "created_at": "string",
        "updated_at": "string"
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

#### Create Asset
- **Method**: POST
- **URL**: `/api/web/asset/assets`
- **Description**: Creates a new asset
- **Request Body**:
```json
{
  "name": "string",
  "category": "string",
  "location": "string",
  "purchase_date": "string",
  "purchase_price": 0,
  "serial_number": "string",
  "description": "string (optional)"
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
    "category": "string",
    "location": "string",
    "status": "available",
    "purchase_date": "string",
    "purchase_price": 0,
    "serial_number": "string",
    "description": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Asset by ID
- **Method**: GET
- **URL**: `/api/web/asset/assets/{id}`
- **Description**: Fetches a specific asset
- **Path Parameters**:
  - `id`: Asset ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "name": "string",
    "category": "string",
    "location": "string",
    "status": "available|assigned|maintenance|disposed",
    "purchase_date": "string",
    "purchase_price": 0,
    "serial_number": "string",
    "description": "string",
    "assigned_to": "string (employee id)",
    "assigned_at": "string",
    "assigned_to_details": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string"
    },
    "maintenance_logs": [
      {
        "id": "string",
        "date": "string",
        "type": "string",
        "description": "string",
        "status": "completed|pending"
      }
    ],
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Update Asset
- **Method**: PUT
- **URL**: `/api/web/asset/assets/{id}`
- **Description**: Updates an asset
- **Path Parameters**:
  - `id`: Asset ID
- **Request Body**:
```json
{
  "name": "string (optional)",
  "category": "string (optional)",
  "location": "string (optional)",
  "purchase_date": "string (optional)",
  "purchase_price": 0 (optional),
  "serial_number": "string (optional)",
  "description": "string (optional)"
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
    "category": "string",
    "location": "string",
    "status": "available|assigned|maintenance|disposed",
    "purchase_date": "string",
    "purchase_price": 0,
    "serial_number": "string",
    "description": "string",
    "assigned_to": "string (employee id)",
    "assigned_at": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Assign Asset
- **Method**: POST
- **URL**: `/api/web/asset/assets/{id}/assign`
- **Description**: Assigns an asset to an employee
- **Path Parameters**:
  - `id`: Asset ID
- **Request Body**:
```json
{
  "employee_id": "string",
  "assigned_date": "string (optional)",
  "note": "string (optional)"
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
    "status": "assigned",
    "assigned_to": "string",
    "assigned_at": "string",
    "message": "Asset assigned successfully"
  }
}
```

#### Return Asset
- **Method**: POST
- **URL**: `/api/web/asset/assets/{id}/return`
- **Description**: Returns an asset from an employee
- **Path Parameters**:
  - `id`: Asset ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "available",
    "assigned_to": null,
    "assigned_at": null,
    "message": "Asset returned successfully"
  }
}
```

#### Dispose Asset
- **Method**: POST
- **URL**: `/api/web/asset/assets/{id}/dispose`
- **Description**: Disposes an asset
- **Path Parameters**:
  - `id`: Asset ID
- **Request Body**:
```json
{
  "disposed_date": "string (optional)",
  "reason": "string (optional)",
  "disposal_value": 0 (optional)"
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
    "status": "disposed",
    "disposed_at": "string",
    "message": "Asset disposed successfully"
  }
}
```

### 3. Requests

#### Get Requests
- **Method**: GET
- **URL**: `/api/web/asset/requests`
- **Description**: Fetches asset requests
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
        "asset_id": "string",
        "status": "pending|approved|rejected|fulfilled",
        "request_date": "string",
        "required_date": "string",
        "reason": "string",
        "employee_details": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        },
        "asset_details": {
          "id": "string",
          "name": "string",
          "category": "string"
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

#### Create Request
- **Method**: POST
- **URL**: `/api/web/asset/requests`
- **Description**: Creates a new asset request
- **Request Body**:
```json
{
  "asset_id": "string",
  "required_date": "string",
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
    "asset_id": "string",
    "status": "pending",
    "request_date": "string",
    "required_date": "string",
    "reason": "string"
  }
}
```

#### Request Action
- **Method**: POST
- **URL**: `/api/web/asset/requests/{id}/{action}`
- **Description**: Performs an action on a request (approve, reject, fulfill, etc.)
- **Path Parameters**:
  - `id`: Request ID
  - `action`: Action to perform (approve, reject, fulfill, etc.)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "approved|rejected|fulfilled",
    "message": "Action completed successfully"
  }
}
```

### 4. Maintenance

#### Get Maintenance
- **Method**: GET
- **URL**: `/api/web/asset/maintenance`
- **Description**: Fetches maintenance logs
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
        "asset_id": "string",
        "asset_details": {
          "id": "string",
          "name": "string",
          "category": "string"
        },
        "type": "string",
        "description": "string",
        "scheduled_date": "string",
        "completed_date": "string",
        "status": "pending|in_progress|completed",
        "cost": 0,
        "vendor": "string",
        "notes": "string"
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

#### Create Maintenance
- **Method**: POST
- **URL**: `/api/web/asset/maintenance`
- **Description**: Creates a new maintenance log
- **Request Body**:
```json
{
  "asset_id": "string",
  "type": "string",
  "description": "string",
  "scheduled_date": "string",
  "cost": 0 (optional),
  "vendor": "string (optional)",
  "notes": "string (optional)"
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
    "asset_id": "string",
    "type": "string",
    "description": "string",
    "scheduled_date": "string",
    "status": "pending",
    "cost": 0,
    "vendor": "string",
    "notes": "string",
    "created_at": "string"
  }
}
```

#### Complete Maintenance
- **Method**: POST
- **URL**: `/api/web/asset/maintenance/{id}/complete`
- **Description**: Marks maintenance as completed
- **Path Parameters**:
  - `id`: Maintenance log ID
- **Request Body**:
```json
{
  "completed_date": "string (optional)",
  "notes": "string (optional)"
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
    "status": "completed",
    "completed_date": "string",
    "message": "Maintenance completed successfully"
  }
}
```

### 5. Reports

#### Get Depreciation
- **Method**: GET
- **URL**: `/api/web/asset/depreciation`
- **Description**: Fetches depreciation data
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "asset_id": "string",
      "asset_name": "string",
      "purchase_price": 0,
      "current_value": 0,
      "depreciation_rate": 0,
      "depreciation_amount": 0,
      "year": 0
    }
  ]
}
```

#### Get Stats
- **Method**: GET
- **URL**: `/api/web/asset/stats`
- **Description**: Fetches asset statistics
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_assets": 0,
    "available_assets": 0,
    "assigned_assets": 0,
    "assets_in_maintenance": 0,
    "disposed_assets": 0,
    "total_value": 0,
    "categories_count": []
  }
}
```

#### Get Filter Options
- **Method**: GET
- **URL**: `/api/web/asset/filter-options`
- **Description**: Fetches filter options for asset module
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "categories": [],
    "locations": [],
    "statuses": [],
    "employees": []
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
4. For asset assignment, use assign/return endpoints to track asset allocation
5. The API provides both individual and bulk operations for efficiency