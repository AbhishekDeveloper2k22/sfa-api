# Celebration API Documentation

This document provides comprehensive information about the Celebration API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Celebration API Endpoints

### 1. Celebrations

#### Get Celebrations
- **Method**: GET
- **URL**: `/api/web/celebration/celebrations`
- **Description**: Fetches celebrations
- **Query Parameters**:
  - `type` (optional): Filter by type (birthday, anniversary, etc.)
  - `department` (optional): Filter by department
  - `status` (optional): Filter by status
  - `date_from` (optional): Filter from date
  - `date_to` (optional): Filter to date
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
        "type": "birthday|anniversary",
        "celebration_date": "string",
        "status": "confirmed|pending|cancelled",
        "department": "string",
        "name": "string",
        "designation": "string",
        "profile_image": "string",
        "created_at": "string",
        "updated_at": "string",
        "employee_details": {
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

#### Create Celebration
- **Method**: POST
- **URL**: `/api/web/celebration/celebrations`
- **Description**: Creates a new celebration
- **Request Body**:
```json
{
  "employee_id": "string",
  "type": "birthday|anniversary",
  "celebration_date": "string",
  "status": "confirmed|pending|cancelled",
  "department": "string",
  "name": "string",
  "designation": "string"
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
    "type": "birthday|anniversary",
    "celebration_date": "string",
    "status": "confirmed",
    "department": "string",
    "name": "string",
    "designation": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Today's Celebrations
- **Method**: GET
- **URL**: `/api/web/celebration/celebrations/today`
- **Description**: Fetches celebrations happening today
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
      "type": "birthday|anniversary",
      "name": "string",
      "designation": "string",
      "profile_image": "string",
      "department": "string"
    }
  ]
}
```

#### Get Weekly Celebrations
- **Method**: GET
- **URL**: `/api/web/celebration/celebrations/week`
- **Description**: Fetches celebrations happening this week
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
      "type": "birthday|anniversary",
      "name": "string",
      "designation": "string",
      "profile_image": "string",
      "department": "string",
      "celebration_date": "string"
    }
  ]
}
```

#### Send All Wishes
- **Method**: POST
- **URL**: `/api/web/celebration/celebrations/send-all-wishes`
- **Description**: Sends wishes to all employees celebrating on a specific date
- **Query Parameters**:
  - `date` (optional): Date to send wishes for (defaults to today)
- **Request Body**:
```json
{
  "message": "string (optional)",
  "channel": "email|sms|notification (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "sent_count": 0,
    "failed_count": 0,
    "message": "Wishes sent successfully"
  }
}
```

#### Get Stats
- **Method**: GET
- **URL**: `/api/web/celebration/celebrations/stats`
- **Description**: Fetches celebration statistics
- **Query Parameters**:
  - `period` (optional, default: "month"): Time period (day, week, month, year)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_celebrations": 0,
    "today_celebrations": 0,
    "upcoming_celebrations": 0,
    "celebration_types": {},
    "department_distribution": {}
  }
}
```

#### Export Celebrations
- **Method**: GET
- **URL**: `/api/web/celebration/celebrations/export`
- **Description**: Exports celebrations data
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

#### Get Celebration by ID
- **Method**: GET
- **URL**: `/api/web/celebration/celebrations/{id}`
- **Description**: Fetches a specific celebration
- **Path Parameters**:
  - `id`: Celebration ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "employee_id": "string",
    "type": "birthday|anniversary",
    "celebration_date": "string",
    "status": "confirmed|pending|cancelled",
    "department": "string",
    "name": "string",
    "designation": "string",
    "profile_image": "string",
    "created_at": "string",
    "updated_at": "string",
    "employee_details": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string"
    }
  }
}
```

#### Update Celebration
- **Method**: PUT
- **URL**: `/api/web/celebration/celebrations/{id}`
- **Description**: Updates a celebration
- **Path Parameters**:
  - `id`: Celebration ID
- **Request Body**:
```json
{
  "type": "birthday|anniversary (optional)",
  "celebration_date": "string (optional)",
  "status": "confirmed|pending|cancelled (optional)",
  "department": "string (optional)",
  "name": "string (optional)",
  "designation": "string (optional)"
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
    "type": "birthday|anniversary",
    "celebration_date": "string",
    "status": "confirmed|pending|cancelled",
    "department": "string",
    "name": "string",
    "designation": "string",
    "updated_at": "string"
  }
}
```

#### Delete Celebration
- **Method**: DELETE
- **URL**: `/api/web/celebration/celebrations/{id}`
- **Description**: Deletes a celebration
- **Path Parameters**:
  - `id`: Celebration ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Celebration deleted successfully"
  }
}
```

#### Send Wish
- **Method**: POST
- **URL**: `/api/web/celebration/celebrations/{id}/send-wish`
- **Description**: Sends a wish for a specific celebration
- **Path Parameters**:
  - `id`: Celebration ID
- **Request Body**:
```json
{
  "message": "string (optional)",
  "channel": "email|sms|notification (optional)"
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
    "message": "Wish sent successfully"
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
5. Use the today/week endpoints to display timely celebration information