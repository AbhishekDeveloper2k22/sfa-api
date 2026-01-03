# Holiday API Documentation

This document provides comprehensive information about the Holiday API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Holiday API Endpoints

### 1. Holidays

#### Get Holidays
- **Method**: GET
- **URL**: `/api/web/holiday/holidays`
- **Description**: Fetches holidays
- **Query Parameters**:
  - `type` (optional): Filter by type (public, optional, restricted)
  - `year` (optional): Filter by year
  - `month` (optional): Filter by month
  - `status` (optional): Filter by status
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
        "date": "string",
        "type": "public|optional|restricted",
        "description": "string",
        "status": "active|inactive",
        "year": "string",
        "month": "string",
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

#### Create Holiday
- **Method**: POST
- **URL**: `/api/web/holiday/holidays`
- **Description**: Creates a new holiday
- **Request Body**:
```json
{
  "name": "string",
  "date": "string",
  "type": "public|optional|restricted",
  "description": "string (optional)",
  "status": "active|inactive (optional)"
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
    "date": "string",
    "type": "public|optional|restricted",
    "description": "string",
    "status": "active",
    "year": "string",
    "month": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Calendar
- **Method**: GET
- **URL**: `/api/web/holiday/holidays/calendar`
- **Description**: Fetches holiday calendar
- **Query Parameters**:
  - `year` (required): Year to get calendar for
  - `month` (optional): Month to get calendar for (if not provided, returns full year)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "year": "string",
    "month": "string (if requested)",
    "holidays": [
      {
        "id": "string",
        "name": "string",
        "date": "string",
        "type": "public|optional|restricted"
      }
    ],
    "working_days": 0,
    "total_holidays": 0
  }
}
```

#### Validate Date
- **Method**: GET
- **URL**: `/api/web/holiday/holidays/validate`
- **Description**: Validates if a date is a holiday
- **Query Parameters**:
  - `date` (required): Date to validate in YYYY-MM-DD format
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "is_holiday": true,
    "holiday": {
      "id": "string",
      "name": "string",
      "date": "string",
      "type": "public|optional|restricted"
    }
  }
}
```

#### Get Stats
- **Method**: GET
- **URL**: `/api/web/holiday/holidays/stats`
- **Description**: Fetches holiday statistics
- **Query Parameters**:
  - `year` (optional): Year to get stats for (defaults to current year)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_holidays": 0,
    "public_holidays": 0,
    "optional_holidays": 0,
    "restricted_holidays": 0,
    "holidays_by_month": {},
    "holiday_types_distribution": {}
  }
}
```

#### Export Holidays
- **Method**: GET
- **URL**: `/api/web/holiday/holidays/export`
- **Description**: Exports holidays data
- **Query Parameters**:
  - `format` (optional, default: "csv"): Export format (csv, excel, pdf)
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

#### Get Holiday by ID
- **Method**: GET
- **URL**: `/api/web/holiday/holidays/{id}`
- **Description**: Fetches a specific holiday
- **Path Parameters**:
  - `id`: Holiday ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "name": "string",
    "date": "string",
    "type": "public|optional|restricted",
    "description": "string",
    "status": "active|inactive",
    "year": "string",
    "month": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Update Holiday
- **Method**: PUT
- **URL**: `/api/web/holiday/holidays/{id}`
- **Description**: Updates a holiday
- **Path Parameters**:
  - `id`: Holiday ID
- **Request Body**:
```json
{
  "name": "string (optional)",
  "date": "string (optional)",
  "type": "public|optional|restricted (optional)",
  "description": "string (optional)",
  "status": "active|inactive (optional)"
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
    "date": "string",
    "type": "public|optional|restricted",
    "description": "string",
    "status": "active|inactive",
    "updated_at": "string"
  }
}
```

#### Delete Holiday
- **Method**: DELETE
- **URL**: `/api/web/holiday/holidays/{id}`
- **Description**: Deletes a holiday
- **Path Parameters**:
  - `id`: Holiday ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Holiday deleted successfully"
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
4. The API provides both individual and bulk operations for efficiency
5. Use the calendar endpoint to display holiday information in calendar views
6. Use the validate endpoint to check if a specific date is a holiday