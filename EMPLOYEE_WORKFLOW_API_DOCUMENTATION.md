# Employee Workflow API Documentation

This document provides comprehensive information about the Employee Workflow API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

## Base URL
All endpoints are prefixed with `/api/web/employees`

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

### Employee Creation Workflow

#### 1. Save Step 1 (Personal Information)
- **Method**: POST
- **URL**: `/api/web/employees/step-1`
- **Description**: Save personal information for employee onboarding
- **Request Body**:
```json
{
  "draft_id": "optional draft ID for continuing an existing workflow",
  "personal": {
    "first_name": "string",
    "last_name": "string",
    "personal_email": "string",
    "phone": "string",
    "date_of_birth": "string (YYYY-MM-DD)",
    "gender": "string",
    "address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "zip_code": "string",
      "country": "string"
    }
  }
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Step 1 saved successfully",
  "statuscode": 201,
  "data": {
    "draft_id": "string",
    "step_completed": 1,
    "next_step": 2,
    "employee_id": "string (if existing draft)"
  }
}
```

#### 2. Save Step 2 (Employment Information)
- **Method**: POST
- **URL**: `/api/web/employees/step-2`
- **Description**: Save employment information
- **Request Body**:
```json
{
  "draft_id": "string (required)",
  "employment": {
    "employee_code": "string",
    "work_email": "string",
    "department_id": "string",
    "designation": "string",
    "role_id": "string",
    "work_location_id": "string",
    "manager_id": "string",
    "employment_type": "string",
    "join_date": "string (YYYY-MM-DD)",
    "probation_period": "string"
  }
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Step 2 saved successfully",
  "statuscode": 200,
  "data": {
    "draft_id": "string",
    "step_completed": 2,
    "next_step": 3
  }
}
```

#### 3. Save Step 3 (Compensation Information)
- **Method**: POST
- **URL**: `/api/web/employees/step-3`
- **Description**: Save compensation information
- **Request Body**:
```json
{
  "draft_id": "string (required)",
  "compensation": {
    "salary_structure_id": "string",
    "basic_salary": "number",
    "allowances": "number",
    "deductions": "number",
    "ctc": "number",
    "currency": "string"
  }
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Step 3 saved successfully",
  "statuscode": 200,
  "data": {
    "draft_id": "string",
    "step_completed": 3,
    "next_step": 4
  }
}
```

#### 4. Save Step 4 (Bank & Tax Information)
- **Method**: POST
- **URL**: `/api/web/employees/step-4`
- **Description**: Save bank and tax information
- **Request Body**:
```json
{
  "draft_id": "string (required)",
  "bank_tax": {
    "bank_name": "string",
    "account_number": "string",
    "ifsc": "string",
    "pan": "string",
    "aadhaar": "string",
    "tax_category": "string"
  }
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Step 4 saved successfully",
  "statuscode": 200,
  "data": {
    "draft_id": "string",
    "step_completed": 4,
    "next_step": 5
  }
}
```

#### 5. Save Step 5 (Documents)
- **Method**: POST
- **URL**: `/api/web/employees/step-5`
- **Description**: Save document information
- **Request Body**:
```json
{
  "draft_id": "string (required)",
  "documents": [
    {
      "document_type": "string",
      "document_url": "string",
      "uploaded_at": "string",
      "category": "string"
    }
  ]
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Documents saved successfully",
  "statuscode": 200,
  "data": {
    "draft_id": "string",
    "step_completed": 5,
    "next_step": 6
  }
}
```

#### 6. Save Step 6 (Emergency & Address)
- **Method**: POST
- **URL**: `/api/web/employees/step-6`
- **Description**: Save emergency contact and address information
- **Request Body**:
```json
{
  "draft_id": "string (required)",
  "emergency_address": {
    "emergency_contact_name": "string",
    "emergency_contact_phone": "string",
    "emergency_contact_relationship": "string",
    "permanent_address": {
      "street": "string",
      "city": "string",
      "state": "string",
      "zip_code": "string",
      "country": "string"
    }
  }
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Emergency & address saved successfully",
  "statuscode": 200,
  "data": {
    "draft_id": "string",
    "step_completed": 6,
    "next_step": null
  }
}
```

#### 7. Complete Employee Creation
- **Method**: POST
- **URL**: `/api/web/employees/complete`
- **Description**: Complete the employee creation process and finalize the record
- **Request Body**:
```json
{
  "draft_id": "string (required)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Employee created successfully",
  "statuscode": 200,
  "data": {
    "employee_id": "string",
    "employee_code": "string",
    "work_email": "string",
    "status": "active",
    "etag": "string"
  }
}
```

### Employee Management

#### 8. List Employees
- **Method**: GET
- **URL**: `/api/web/employees`
- **Description**: List employees with optional filtering and pagination
- **Query Parameters**:
  - `page` (optional, default: 1) - Page number
  - `limit` (optional, default: 20, max: 100) - Items per page
  - `search` (optional) - Search term for name, email, or code
  - `status` (optional) - Filter by status (active, inactive, suspended, terminated)
  - `employment_status` (optional) - Filter by employment status
  - `department_id` (optional) - Filter by department
  - `designation` (optional) - Filter by designation
  - `role_id` (optional) - Filter by role
  - `location_id` (optional) - Filter by location
  - `manager_id` (optional) - Filter by manager
  - `tags` (optional) - Filter by tags (array)
  - `join_date_from` (optional) - Filter by join date from
  - `join_date_to` (optional) - Filter by join date to
  - `sort_by` (optional) - Sort field
  - `sort_order` (optional) - Sort order (asc/desc)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "items": [
      {
        "id": "string",
        "employee_code": "string",
        "name": "string",
        "department": "string",
        "designation": "string",
        "manager_id": "string",
        "work_location_id": "string",
        "status": "string",
        "employment_status": "string",
        "tags": ["string"],
        "ess_enabled": boolean,
        "work_email": "string",
        "join_date": "string",
        "updated_at": "string"
      }
    ],
    "page": 1,
    "limit": 20,
    "total": 100,
    "total_pages": 5,
    "filters_applied": {}
  }
}
```

#### 9. Get Filter Options
- **Method**: GET
- **URL**: `/api/web/employees/filter-options`
- **Description**: Get filter options for employee listing
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "departments": [
      {
        "id": "string",
        "name": "string",
        "code": "string"
      }
    ],
    "designations": [
      {
        "id": "string",
        "name": "string",
        "department": "string"
      }
    ],
    "locations": [
      {
        "id": "string",
        "name": "string"
      }
    ],
    "roles": [
      {
        "id": "string",
        "name": "string",
        "code": "string"
      }
    ],
    "tags": ["string"],
    "statuses": [
      {
        "value": "active",
        "label": "Active"
      }
    ]
  }
}
```

#### 10. Export Employees
- **Method**: POST
- **URL**: `/api/web/employees/bulk/export`
- **Description**: Export employees with specified filters
- **Request Body**:
```json
{
  "filters": {
    "search": "string",
    "status": "string",
    "department_id": "string",
    "designation": "string",
    "role_id": "string",
    "location_id": "string",
    "manager_id": "string",
    "tags": ["string"],
    "join_date_from": "string",
    "join_date_to": "string"
  },
  "limit": 1000
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Employees export generated",
  "statuscode": 200,
  "data": {
    "items": [
      {
        "employee_code": "string",
        "full_name": "string",
        "department_id": "string",
        "designation": "string",
        "work_email": "string",
        "personal_email": "string",
        "employment_type": "string",
        "join_date": "string",
        "manager_id": "string",
        "status": "string",
        "employment_status": "string",
        "tags": ["string"],
        "bank_name": "string",
        "ifsc": "string"
      }
    ],
    "count": 50
  }
}
```

#### 11. Bulk Assign Role
- **Method**: POST
- **URL**: `/api/web/employees/bulk/assign-role`
- **Description**: Assign role to multiple employees
- **Request Body**:
```json
{
  "employee_ids": ["string"],
  "role_id": "string",
  "role_name": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Roles assigned successfully",
  "statuscode": 200,
  "data": {
    "updated": 5
  }
}
```

#### 12. Bulk Suspend
- **Method**: POST
- **URL**: `/api/web/employees/bulk/suspend`
- **Description**: Suspend multiple employees
- **Request Body**:
```json
{
  "employee_ids": ["string"],
  "reason": "string (optional)",
  "effective_date": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Employees suspended successfully",
  "statuscode": 200,
  "data": {
    "updated": 3
  }
}
```

#### 13. Bulk Terminate
- **Method**: POST
- **URL**: `/api/web/employees/bulk/terminate`
- **Description**: Terminate multiple employees
- **Request Body**:
```json
{
  "employee_ids": ["string"],
  "reason": "string (optional)",
  "last_working_day": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Employees terminated successfully",
  "statuscode": 200,
  "data": {
    "updated": 2
  }
}
```

#### 14. Bulk Activate ESS
- **Method**: POST
- **URL**: `/api/web/employees/bulk/activate-ess`
- **Description**: Activate/Deactivate ESS (Employee Self Service) for multiple employees
- **Request Body**:
```json
{
  "employee_ids": ["string"],
  "enable": true
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "ESS access updated",
  "statuscode": 200,
  "data": {
    "updated": 10
  }
}
```

#### 15. Bulk Add Tag
- **Method**: POST
- **URL**: `/api/web/employees/bulk/add-tag`
- **Description**: Add tag to multiple employees
- **Request Body**:
```json
{
  "employee_ids": ["string"],
  "tag": "string"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Tag added successfully",
  "statuscode": 200,
  "data": {
    "updated": 8
  }
}
```

### Draft Management

#### 16. Get Draft
- **Method**: GET
- **URL**: `/api/web/employees/drafts/{draft_id}`
- **Description**: Get a specific employee draft
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "draft_id": "string",
    "tenant_id": "string",
    "status": "string",
    "step_completed": 3,
    "next_step": 4,
    "personal": {},
    "employment": {},
    "compensation": {},
    "bank_tax": {},
    "documents": [],
    "emergency_address": {},
    "created_at": "string",
    "updated_at": "string",
    "history": []
  }
}
```

#### 17. List Drafts
- **Method**: GET
- **URL**: `/api/web/employees/drafts`
- **Description**: List all employee drafts for the current user
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "drafts": [
      {
        "draft_id": "string",
        "employee_name": "string",
        "step_completed": 2,
        "next_step": 3,
        "updated_at": "string"
      }
    ]
  }
}
```

#### 18. Delete Draft
- **Method**: DELETE
- **URL**: `/api/web/employees/drafts/{draft_id}`
- **Description**: Delete a specific employee draft
- **Response**:
```json
{
  "success": true,
  "msg": "Draft deleted",
  "statuscode": 200,
  "data": null
}
```

### Employee Operations

#### 19. Get Employee
- **Method**: GET
- **URL**: `/api/web/employees/{employee_id}`
- **Description**: Get a specific employee by ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "tenant_id": "string",
    "draft_id": "string",
    "personal": {},
    "employment": {},
    "compensation": {},
    "bank_tax": {},
    "documents": [],
    "emergency_address": {},
    "status": "active",
    "employment_status": "active",
    "version": 1,
    "etag": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### 20. Update Employee
- **Method**: PUT
- **URL**: `/api/web/employees/{employee_id}`
- **Description**: Update an existing employee
- **Headers**:
  - `If-Match`: ETag value for optimistic locking (optional)
- **Request Body**:
```json
{
  "personal": {},
  "employment": {},
  "compensation": {},
  "bank_tax": {},
  "documents": [],
  "emergency_address": {},
  "status": "active"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Employee updated successfully",
  "statuscode": 200,
  "data": {
    "id": "string",
    "tenant_id": "string",
    "draft_id": "string",
    "personal": {},
    "employment": {},
    "compensation": {},
    "bank_tax": {},
    "documents": [],
    "emergency_address": {},
    "status": "active",
    "employment_status": "active",
    "version": 2,
    "etag": "string",
    "created_at": "string",
    "updated_at": "string"
  }
}
```

#### 21. Update Employee Status
- **Method**: PATCH
- **URL**: `/api/web/employees/{employee_id}/status`
- **Description**: Update employee status
- **Request Body**:
```json
{
  "status": "active|inactive|suspended|terminated",
  "reason": "string (optional)",
  "effective_date": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Employee status updated",
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "active",
    "employment_status": "active",
    "status_reason": "string",
    "status_effective_date": "string",
    "updated_at": "string"
  }
}
```

#### 22. Update Employee Step
- **Method**: PATCH
- **URL**: `/api/web/employees/{employee_id}/step-{step_number}`
- **Description**: Update a specific step of an existing employee
- **Headers**:
  - `If-Match`: ETag value for optimistic locking (optional)
- **Request Body**:
```json
{
  "personal": {},
  "employment": {},
  "compensation": {},
  "bank_tax": {},
  "documents": [],
  "emergency_address": {}
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Step {step_number} updated successfully",
  "statuscode": 200,
  "data": {
    "id": "string",
    "personal": {},
    "employment": {},
    "compensation": {},
    "bank_tax": {},
    "documents": [],
    "emergency_address": {},
    "version": 2,
    "etag": "string",
    "updated_at": "string"
  }
}
```

### Validation Endpoints

#### 23. Validate Email
- **Method**: GET
- **URL**: `/api/web/employees/validate/email`
- **Description**: Check if an email is unique
- **Query Parameters**:
  - `email`: Email to validate (required)
  - `exclude_id`: Employee ID to exclude from validation (optional)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "is_unique": true,
    "message": "Value is available"
  }
}
```

#### 24. Validate Code
- **Method**: GET
- **URL**: `/api/web/employees/validate/code`
- **Description**: Check if an employee code is unique
- **Query Parameters**:
  - `code`: Code to validate (required)
  - `exclude_id`: Employee ID to exclude from validation (optional)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "is_unique": true,
    "message": "Value is available"
  }
}
```

#### 25. Validate Username
- **Method**: GET
- **URL**: `/api/web/employees/validate/username`
- **Description**: Check if a username is unique
- **Query Parameters**:
  - `username`: Username to validate (required)
  - `exclude_id`: Employee ID to exclude from validation (optional)
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "is_unique": true,
    "message": "Value is available"
  }
}
```

### Lookup Endpoints

#### 26. Lookup Resource
- **Method**: GET
- **URL**: `/api/web/employees/lookup/{resource}`
- **Description**: Get lookup data for various resources
- **Path Parameter**:
  - `resource`: One of: departments, locations, shifts, designations, salary-structures, roles, employees, document-categories, permission-profiles
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
        "code": "string",
        "extra": {}
      }
    ]
  }
}
```

### File Upload Endpoints

#### 27. Initialize Upload
- **Method**: POST
- **URL**: `/api/web/employees/uploads/init`
- **Description**: Initialize a file upload
- **Request Body**:
```json
{
  "file_name": "string",
  "file_size": "number",
  "mime_type": "string",
  "category": "string"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Upload initialized",
  "statuscode": 200,
  "data": {
    "upload_id": "string",
    "signed_url": "string",
    "expires_at": "string"
  }
}
```

#### 28. Complete Upload
- **Method**: POST
- **URL**: `/api/web/employees/uploads/{upload_id}/complete`
- **Description**: Complete a file upload
- **Request Body**:
```json
{
  "file_url": "string"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": "Upload completed",
  "statuscode": 200,
  "data": {
    "upload_id": "string",
    "file_url": "string",
    "file_size": "number"
  }
}
```

## Common HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request - Validation error
- `401`: Unauthorized - Invalid or missing token
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `409`: Conflict - Resource already completed
- `412`: Precondition Failed - Version mismatch (ETag)
- `422`: Unprocessable Entity - Validation failed
- `500`: Internal Server Error

## Notes for Frontend Developers
1. Always include the Authorization header with a valid JWT token
2. Handle the If-Match header for optimistic locking when updating employees
3. Check the `success` field in responses to determine if the operation was successful
4. Use the `next_step` field to guide users through the employee creation workflow
5. The `etag` field is used for optimistic locking to prevent concurrent updates
6. For bulk operations, always validate the `updated` count in the response to confirm how many records were affected
7. The employee creation workflow requires all 6 steps to be completed before calling the complete endpoint