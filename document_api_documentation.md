# Document API Documentation

This document provides comprehensive information about the Document API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Document API Endpoints

### 1. Categories

#### Get Categories
- **Method**: GET
- **URL**: `/api/web/document/categories`
- **Description**: Fetches document categories
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
      "required": true,
      "expires": true,
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

### 2. Documents

#### Get Documents
- **Method**: GET
- **URL**: `/api/web/document/documents`
- **Description**: Fetches documents
- **Query Parameters**:
  - `category_id` (optional): Filter by category ID
  - `employee_id` (optional): Filter by employee ID
  - `search` (optional): Search term
  - `expiring_within_days` (optional): Filter by documents expiring within specified days
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
        "category_id": "string",
        "name": "string",
        "description": "string",
        "file_url": "string",
        "version": "string",
        "expires_at": "string",
        "is_expired": false,
        "created_at": "string",
        "updated_at": "string",
        "employee_details": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string"
        },
        "category_details": {
          "id": "string",
          "name": "string"
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

#### Create Document
- **Method**: POST
- **URL**: `/api/web/document/documents`
- **Description**: Creates a new document
- **Request Body**:
```json
{
  "employee_id": "string",
  "category_id": "string",
  "name": "string",
  "description": "string",
  "file_url": "string",
  "expires_at": "string (optional)"
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
    "category_id": "string",
    "name": "string",
    "description": "string",
    "file_url": "string",
    "version": "1.0",
    "expires_at": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### Get Document by ID
- **Method**: GET
- **URL**: `/api/web/document/documents/{id}`
- **Description**: Fetches a specific document
- **Path Parameters**:
  - `id`: Document ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "employee_id": "string",
    "category_id": "string",
    "name": "string",
    "description": "string",
    "file_url": "string",
    "version": "string",
    "expires_at": "string",
    "is_expired": false,
    "created_at": "string",
    "updated_at": "string",
    "employee_details": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string"
    },
    "category_details": {
      "id": "string",
      "name": "string"
    },
    "versions": [
      {
        "id": "string",
        "version": "string",
        "file_url": "string",
        "uploaded_at": "string",
        "uploaded_by": "string"
      }
    ]
  }
}
```

#### Update Document
- **Method**: PUT
- **URL**: `/api/web/document/documents/{id}`
- **Description**: Updates a document
- **Path Parameters**:
  - `id`: Document ID
- **Request Body**:
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "file_url": "string (optional)",
  "expires_at": "string (optional)"
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
    "description": "string",
    "file_url": "string",
    "expires_at": "string",
    "updated_at": "string"
  }
}
```

#### Delete Document
- **Method**: DELETE
- **URL**: `/api/web/document/documents/{id}`
- **Description**: Deletes a document
- **Path Parameters**:
  - `id`: Document ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Document deleted successfully"
  }
}
```

### 3. Versions

#### Get Document Versions
- **Method**: GET
- **URL**: `/api/web/document/documents/{id}/versions`
- **Description**: Fetches document versions
- **Path Parameters**:
  - `id`: Document ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "version": "string",
      "file_url": "string",
      "uploaded_at": "string",
      "uploaded_by": "string",
      "is_active": true
    }
  ]
}
```

#### Upload Document Version
- **Method**: POST
- **URL**: `/api/web/document/documents/{id}/versions`
- **Description**: Uploads a new version of a document
- **Path Parameters**:
  - `id`: Document ID
- **Request Body**:
```json
{
  "file_url": "string",
  "version": "string (optional)"
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
    "version": "string",
    "file_url": "string",
    "uploaded_at": "string",
    "uploaded_by": "string",
    "is_active": true
  }
}
```

#### Restore Document Version
- **Method**: POST
- **URL**: `/api/web/document/documents/{id}/versions/{versionId}/restore`
- **Description**: Restores a specific version of a document
- **Path Parameters**:
  - `id`: Document ID
  - `versionId`: Version ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Version restored successfully"
  }
}
```

### 4. Downloads & Extensions

#### Get Download URL
- **Method**: GET
- **URL**: `/api/web/document/documents/{id}/download`
- **Description**: Gets download URL for a document
- **Path Parameters**:
  - `id`: Document ID
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

#### Extend Expiry
- **Method**: POST
- **URL**: `/api/web/document/documents/{id}/extend`
- **Description**: Extends the expiry date of a document
- **Path Parameters**:
  - `id`: Document ID
- **Request Body**:
```json
{
  "expires_at": "string"
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
    "expires_at": "string",
    "message": "Expiry extended successfully"
  }
}
```

### 5. Expiring & Misc

#### Get Expiring Documents
- **Method**: GET
- **URL**: `/api/web/document/expiring`
- **Description**: Fetches documents expiring within specified days
- **Query Parameters**:
  - `days` (optional, default: 30): Number of days to check for expiring documents
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
      "category_id": "string",
      "name": "string",
      "expires_at": "string",
      "days_to_expiry": 0,
      "employee_details": {
        "id": "string",
        "display_name": "string",
        "employee_code": "string"
      }
    }
  ]
}
```

#### Initialize Upload
- **Method**: POST
- **URL**: `/api/web/document/upload/init`
- **Description**: Initializes a file upload
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "upload_id": "string",
    "upload_url": "string",
    "expires_at": "string"
  }
}
```

#### Complete Upload
- **Method**: POST
- **URL**: `/api/web/document/upload/{uploadId}/complete`
- **Description**: Completes a file upload
- **Path Parameters**:
  - `uploadId`: Upload ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true,
    "message": "Upload completed successfully"
  }
}
```

#### Get Stats
- **Method**: GET
- **URL**: `/api/web/document/stats`
- **Description**: Fetches document statistics
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_documents": 0,
    "expiring_documents": 0,
    "expired_documents": 0,
    "categories_count": []
  }
}
```

#### Get Filter Options
- **Method**: GET
- **URL**: `/api/web/document/filter-options`
- **Description**: Fetches filter options for document module
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "categories": [],
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
4. For file uploads, use multipart/form-data content type
5. The API provides both individual and bulk operations for efficiency
6. Document versions allow maintaining history of document changes