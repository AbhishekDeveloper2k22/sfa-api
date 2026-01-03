# Announcement API Documentation

This document provides comprehensive information about the Announcement API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Announcement API Endpoints

### 1. Announcements

#### Get Announcements
- **Method**: GET
- **URL**: `/api/web/announcement/announcements`
- **Description**: Fetches announcements
- **Query Parameters**:
  - `category` (optional): Filter by category
  - `priority` (optional): Filter by priority (low, medium, high, urgent)
  - `status` (optional): Filter by status (draft, published, archived)
  - `target_audience` (optional): Filter by target audience
  - `search` (optional): Search term
  - `page` (optional, default: 1): Page number
  - `size` (optional, default: 10): Items per page
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
        "title": "string",
        "content": "string",
        "category": "string",
        "priority": "low|medium|high|urgent",
        "status": "draft|published|archived",
        "target_audience": "string",
        "publish_date": "string",
        "expiry_date": "string",
        "created_by": "string",
        "created_at": "string",
        "updated_at": "string",
        "view_count": 0,
        "is_read": false
      }
    ],
    "meta": {
      "total": 0,
      "page": 1,
      "page_size": 10,
      "total_pages": 1
    }
  }
}
```

#### Create Announcement
- **Method**: POST
- **URL**: `/api/web/announcement/announcements`
- **Description**: Creates a new announcement
- **Request Body**:
```json
{
  "title": "string",
  "content": "string",
  "category": "string",
  "priority": "low|medium|high|urgent",
  "status": "draft|published",
  "target_audience": "string",
  "publish_date": "string (optional)",
  "expiry_date": "string (optional)"
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
    "title": "string",
    "content": "string",
    "category": "string",
    "priority": "low|medium|high|urgent",
    "status": "draft",
    "target_audience": "string",
    "publish_date": "string",
    "expiry_date": "string",
    "created_by": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Announcement Stats
- **Method**: GET
- **URL**: `/api/web/announcement/announcements/stats`
- **Description**: Fetches announcement statistics
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_announcements": 0,
    "published_announcements": 0,
    "draft_announcements": 0,
    "categories_count": [],
    "priority_distribution": {}
  }
}
```

#### Export Announcements
- **Method**: GET
- **URL**: `/api/web/announcement/announcements/export`
- **Description**: Exports announcements
- **Query Parameters**:
  - `format` (optional, default: "pdf"): Export format (pdf, excel, csv)
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

#### Get Announcement by ID
- **Method**: GET
- **URL**: `/api/web/announcement/announcements/{id}`
- **Description**: Fetches a specific announcement
- **Path Parameters**:
  - `id`: Announcement ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "title": "string",
    "content": "string",
    "category": "string",
    "priority": "low|medium|high|urgent",
    "status": "draft|published|archived",
    "target_audience": "string",
    "publish_date": "string",
    "expiry_date": "string",
    "created_by": "string",
    "created_at": "string",
    "updated_at": "string",
    "view_count": 0,
    "is_read": false
  }
}
```

#### Update Announcement
- **Method**: PUT
- **URL**: `/api/web/announcement/announcements/{id}`
- **Description**: Updates an announcement
- **Path Parameters**:
  - `id`: Announcement ID
- **Request Body**:
```json
{
  "title": "string (optional)",
  "content": "string (optional)",
  "category": "string (optional)",
  "priority": "low|medium|high|urgent (optional)",
  "status": "draft|published|archived (optional)",
  "target_audience": "string (optional)",
  "publish_date": "string (optional)",
  "expiry_date": "string (optional)"
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
    "title": "string",
    "content": "string",
    "category": "string",
    "priority": "low|medium|high|urgent",
    "status": "draft|published|archived",
    "target_audience": "string",
    "publish_date": "string",
    "expiry_date": "string",
    "updated_at": "string"
  }
}
```

#### Delete Announcement
- **Method**: DELETE
- **URL**: `/api/web/announcement/announcements/{id}`
- **Description**: Deletes an announcement
- **Path Parameters**:
  - `id`: Announcement ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Announcement deleted successfully"
  }
}
```

### 2. Views & Sharing

#### Track View
- **Method**: POST
- **URL**: `/api/web/announcement/announcements/{id}/view`
- **Description**: Tracks when a user views an announcement
- **Path Parameters**:
  - `id`: Announcement ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "View tracked successfully"
  }
}
```

#### Share Announcement
- **Method**: POST
- **URL**: `/api/web/announcement/announcements/{id}/share`
- **Description**: Shares an announcement with specific users or groups
- **Path Parameters**:
  - `id`: Announcement ID
- **Request Body**:
```json
{
  "recipients": ["string"],
  "message": "string (optional)"
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
    "message": "Announcement shared successfully"
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
3. Use the pagination parameters for list endpoints (page, size)
4. The API provides both individual and bulk operations for efficiency
5. Track views to monitor announcement engagement
6. Use priority levels to indicate importance of announcements