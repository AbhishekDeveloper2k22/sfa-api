# Policy API Documentation

This document provides comprehensive information about the Policy API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Policy API Endpoints

### 1. Policies

#### Get Policies
- **Method**: GET
- **URL**: `/api/web/policy/policies`
- **Description**: Fetches policies
- **Query Parameters**:
  - `category` (optional): Filter by category
  - `search` (optional): Search term
  - `status` (optional): Filter by status
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
        "category": "string",
        "status": "draft|published|archived",
        "content": "string",
        "created_by": "string",
        "created_at": "string",
        "updated_at": "string",
        "published_at": "string",
        "attachments": [
          {
            "id": "string",
            "filename": "string",
            "size": "string",
            "url": "string"
          }
        ]
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

#### Create Policy
- **Method**: POST
- **URL**: `/api/web/policy/policies`
- **Description**: Creates a new policy
- **Request Body**:
```json
{
  "title": "string",
  "category": "string",
  "content": "string",
  "status": "draft|published"
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
    "category": "string",
    "status": "draft",
    "content": "string",
    "created_by": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Policy Stats
- **Method**: GET
- **URL**: `/api/web/policy/policies/stats`
- **Description**: Fetches policy statistics
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_policies": 0,
    "published_policies": 0,
    "draft_policies": 0,
    "categories_count": []
  }
}
```

#### Export Policies
- **Method**: POST
- **URL**: `/api/web/policy/policies/export`
- **Description**: Exports policies
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

#### Get Policy by ID
- **Method**: GET
- **URL**: `/api/web/policy/policies/{id}`
- **Description**: Fetches a specific policy
- **Path Parameters**:
  - `id`: Policy ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "title": "string",
    "category": "string",
    "status": "draft|published|archived",
    "content": "string",
    "created_by": "string",
    "created_at": "string",
    "updated_at": "string",
    "published_at": "string",
    "attachments": [
      {
        "id": "string",
        "filename": "string",
        "size": "string",
        "url": "string"
      }
    ]
  }
}
```

#### Update Policy
- **Method**: PUT
- **URL**: `/api/web/policy/policies/{id}`
- **Description**: Updates a policy
- **Path Parameters**:
  - `id`: Policy ID
- **Request Body**:
```json
{
  "title": "string (optional)",
  "category": "string (optional)",
  "content": "string (optional)",
  "status": "draft|published|archived (optional)"
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
    "category": "string",
    "status": "draft|published|archived",
    "content": "string",
    "updated_at": "string"
  }
}
```

#### Delete Policy
- **Method**: DELETE
- **URL**: `/api/web/policy/policies/{id}`
- **Description**: Deletes a policy
- **Path Parameters**:
  - `id`: Policy ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Policy deleted successfully"
  }
}
```

### 2. Attachments

#### Add Attachment
- **Method**: POST
- **URL**: `/api/web/policy/policies/{id}/attachments`
- **Description**: Adds an attachment to a policy
- **Path Parameters**:
  - `id`: Policy ID
- **Request Body** (multipart/form-data):
```json
{
  "file": "binary file"
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
    "filename": "string",
    "size": "string",
    "url": "string",
    "added_at": "string"
  }
}
```

#### Remove Attachment
- **Method**: DELETE
- **URL**: `/api/web/policy/policies/{policy_id}/attachments/{attachment_id}`
- **Description**: Removes an attachment from a policy
- **Path Parameters**:
  - `policy_id`: Policy ID
  - `attachment_id`: Attachment ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Attachment removed successfully"
  }
}
```

### 3. Downloads & Actions

#### Download Policy
- **Method**: GET
- **URL**: `/api/web/policy/policies/{id}/download`
- **Description**: Downloads a policy as PDF
- **Path Parameters**:
  - `id`: Policy ID
- **Response**: PDF file content with appropriate headers

#### Email Policy
- **Method**: POST
- **URL**: `/api/web/policy/policies/{id}/email`
- **Description**: Emails a policy to specified recipients
- **Path Parameters**:
  - `id`: Policy ID
- **Request Body**:
```json
{
  "recipients": ["string"],
  "subject": "string",
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
    "sent": true,
    "message": "Policy emailed successfully"
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
4. For file uploads, use multipart/form-data content type
5. The API provides both individual and bulk operations for efficiency