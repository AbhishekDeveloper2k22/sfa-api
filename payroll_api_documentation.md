# Payroll API Documentation

This document provides comprehensive information about the Payroll API endpoints available for frontend integration. The API follows REST conventions and uses JSON for data exchange.

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

## Payroll API Endpoints

### 1. Payroll Runs

#### Get Payroll Runs
- **Method**: GET
- **URL**: `/api/web/payroll/runs`
- **Description**: Fetches payroll runs
- **Query Parameters**:
  - `status` (optional): Filter by status
  - `year` (optional): Filter by year
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
        "period_month": 1,
        "period_year": 2024,
        "run_type": "regular",
        "status": "finalized",
        "created_by": "string",
        "created_at": "string",
        "finalized_at": "string",
        "employee_count": 10,
        "totals": {
          "gross": 500000,
          "net": 450000,
          "employer_cost": 550000
        }
      }
    ],
    "meta": {
      "total": 5
    }
  }
}
```

#### Get Payroll Run by ID
- **Method**: GET
- **URL**: `/api/web/payroll/runs/{runId}`
- **Description**: Fetches a specific payroll run
- **Path Parameters**:
  - `runId`: Payroll run ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "period_month": 1,
    "period_year": 2024,
    "run_type": "regular",
    "status": "finalized",
    "created_by": "string",
    "created_at": "string",
    "finalized_at": "string",
    "employee_count": 10,
    "totals": {
      "gross": 500000,
      "net": 450000,
      "employer_cost": 550000
    }
  }
}
```

#### Start Preview
- **Method**: POST
- **URL**: `/api/web/payroll/preview`
- **Description**: Starts a payroll preview calculation
- **Request Body**:
```json
{
  "period_month": 1,
  "period_year": 2024,
  "run_type": "regular"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 202,
  "data": {
    "job_id": "string",
    "status": "queued",
    "message": "Preview started"
  }
}
```

#### Get Preview Results
- **Method**: GET
- **URL**: `/api/web/payroll/preview/{jobId}/employees`
- **Description**: Gets payroll preview results
- **Path Parameters**:
  - `jobId`: Job ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "data": [
      {
        "employee_id": "string",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string",
          "department": "string"
        },
        "salary_structure": "string",
        "earnings": [
          {
            "code": "string",
            "label": "string",
            "amount": 0
          }
        ],
        "deductions": [
          {
            "code": "string",
            "label": "string",
            "amount": 0
          }
        ],
        "gross": 0,
        "total_deductions": 0,
        "net_pay": 0
      }
    ],
    "meta": {
      "page": 1,
      "page_size": 50,
      "total": 10,
      "total_pages": 1
    },
    "summary": {
      "total_employees": 10,
      "total_gross": 500000,
      "total_net": 450000,
      "total_deductions": 50000,
      "warnings_count": 0,
      "errors_count": 0
    }
  }
}
```

#### Finalize Payroll
- **Method**: POST
- **URL**: `/api/web/payroll/run`
- **Description**: Finalizes a payroll run
- **Request Body**:
```json
{
  "preview_job_id": "string",
  "finalize_notes": "string (optional)"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "payroll_run_id": "string",
    "status": "finalized",
    "message": "Payroll finalized successfully"
  }
}
```

#### Export Payroll Run
- **Method**: GET
- **URL**: `/api/web/payroll/runs/{runId}/export`
- **Description**: Exports a payroll run
- **Path Parameters**:
  - `runId`: Payroll run ID
- **Query Parameters**:
  - `format`: Export format (csv, pdf, excel)
  - `type`: Export type (summary, detailed)
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

#### Get Payroll Stats
- **Method**: GET
- **URL**: `/api/web/payroll/stats`
- **Description**: Gets payroll statistics
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "total_employees": 100,
    "current_month_payroll": 0,
    "ytd_payroll": 0,
    "pending_requests": 0,
    "pending_challans": 0,
    "last_run_date": null
  }
}
```

#### Get Filter Options
- **Method**: GET
- **URL**: `/api/web/payroll/filter-options`
- **Description**: Gets payroll filter options
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "departments": [],
    "employees": [],
    "salary_structures": [],
    "statutory_versions": [],
    "run_types": [
      {
        "value": "regular",
        "label": "Regular Monthly"
      }
    ],
    "challan_types": [
      {
        "value": "PF",
        "label": "Provident Fund"
      }
    ]
  }
}
```

#### Get Job Status
- **Method**: GET
- **URL**: `/api/web/payroll/jobs/{jobId}`
- **Description**: Gets the status of a payroll job
- **Path Parameters**:
  - `jobId`: Job ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "job_id": "string",
    "status": "completed",
    "progress": 100,
    "result_url": "string"
  }
}
```

### 2. Payslips

#### Get Payslips
- **Method**: GET
- **URL**: `/api/web/payslips`
- **Description**: Fetches payslips
- **Query Parameters**:
  - `period_month` (optional): Filter by month
  - `period_year` (optional): Filter by year
  - `status` (optional): Filter by status
  - `q` (optional): Search query
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
        "period_month": 1,
        "period_year": 2024,
        "status": "finalized",
        "employee": {
          "id": "string",
          "display_name": "string",
          "employee_code": "string",
          "department": "string"
        },
        "salary_structure": "string",
        "earnings": [
          {
            "code": "string",
            "label": "string",
            "amount": 0
          }
        ],
        "deductions": [
          {
            "code": "string",
            "label": "string",
            "amount": 0
          }
        ],
        "gross": 0,
        "total_deductions": 0,
        "net_pay": 0
      }
    ],
    "meta": {
      "total": 10
    }
  }
}
```

#### Get Payslip by ID or Employee Payslips
- **Method**: GET
- **URL**: `/api/web/payslips/{id}`
- **Description**: Gets a specific payslip or all payslips for an employee
- **Path Parameters**:
  - `id`: Either payslip ID or employee ID
- **Query Parameters**:
  - `period_month` (optional): Filter by month
  - `period_year` (optional): Filter by year
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "employee_id": "string",
    "period_month": 1,
    "period_year": 2024,
    "status": "finalized",
    "employee": {
      "id": "string",
      "display_name": "string",
      "employee_code": "string",
      "department": "string"
    },
    "salary_structure": "string",
    "earnings": [
      {
        "code": "string",
        "label": "string",
        "amount": 0
      }
    ],
    "deductions": [
      {
        "code": "string",
        "label": "string",
        "amount": 0
      }
    ],
    "gross": 0,
    "total_deductions": 0,
    "net_pay": 0
  }
}
```

#### Download Payslip
- **Method**: GET
- **URL**: `/api/web/payslips/{id}/download`
- **Description**: Downloads a payslip
- **Path Parameters**:
  - `id`: Payslip ID
- **Query Parameters**:
  - `format`: Download format (pdf, excel)
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

### 3. Salary Structures

#### Get Salary Structures
- **Method**: GET
- **URL**: `/api/web/salary-structures`
- **Description**: Fetches all salary structures
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "code": "string",
      "name": "string",
      "description": "string",
      "components": [
        {
          "code": "string",
          "label": "string",
          "type": "earning|deduction",
          "formula": "string",
          "percentage": 0
        }
      ]
    }
  ]
}
```

#### Create Salary Structure
- **Method**: POST
- **URL**: `/api/web/salary-structures`
- **Description**: Creates a new salary structure
- **Request Body**:
```json
{
  "code": "string",
  "name": "string",
  "description": "string",
  "components": [
    {
      "code": "string",
      "label": "string",
      "type": "earning|deduction",
      "formula": "string",
      "percentage": 0
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
    "code": "string",
    "name": "string",
    "description": "string",
    "components": [
      {
        "code": "string",
        "label": "string",
        "type": "earning|deduction",
        "formula": "string",
        "percentage": 0
      }
    ]
  }
}
```

#### Validate Formula
- **Method**: POST
- **URL**: `/api/web/salary-structures/validate-formula`
- **Description**: Validates a salary formula
- **Request Body**:
```json
{
  "formula": "string"
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "valid": true,
    "errors": []
  }
}
```

#### Get Salary Structure by Code
- **Method**: GET
- **URL**: `/api/web/salary-structures/{code}`
- **Description**: Fetches a specific salary structure by code
- **Path Parameters**:
  - `code`: Structure code
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "code": "string",
    "name": "string",
    "description": "string",
    "components": [
      {
        "code": "string",
        "label": "string",
        "type": "earning|deduction",
        "formula": "string",
        "percentage": 0
      }
    ]
  }
}
```

#### Update Salary Structure
- **Method**: PUT
- **URL**: `/api/web/salary-structures/{code}`
- **Description**: Updates a salary structure
- **Path Parameters**:
  - `code`: Structure code
- **Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "components": [
    {
      "code": "string",
      "label": "string",
      "type": "earning|deduction",
      "formula": "string",
      "percentage": 0
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
    "code": "string",
    "name": "string",
    "description": "string",
    "components": [
      {
        "code": "string",
        "label": "string",
        "type": "earning|deduction",
        "formula": "string",
        "percentage": 0
      }
    ]
  }
}
```

#### Delete Salary Structure
- **Method**: DELETE
- **URL**: `/api/web/salary-structures/{code}`
- **Description**: Deletes a salary structure
- **Path Parameters**:
  - `code`: Structure code
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "success": true
  }
}
```

### 4. Statutory & Challan

#### Get Statutory Rules
- **Method**: GET
- **URL**: `/api/web/statutory/rules`
- **Description**: Fetches statutory rules
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "rule_001",
      "name": "India Statutory Rules FY 2024-25",
      "version": "v2024_04",
      "effective_from": "2024-04-01",
      "config": {}
    }
  ]
}
```

#### Get Active Statutory Rule
- **Method**: GET
- **URL**: `/api/web/statutory/rules/active`
- **Description**: Fetches active statutory rule
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "rule_001",
    "name": "India Statutory Rules FY 2024-25",
    "version": "v2024_04",
    "effective_from": "2024-04-01",
    "config": {}
  }
}
```

#### Get Challans
- **Method**: GET
- **URL**: `/api/web/statutory/challans`
- **Description**: Fetches statutory challans
- **Query Parameters**:
  - `status` (optional): Filter by status
  - `type` (optional): Filter by type
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": [
    {
      "id": "string",
      "status": "draft",
      "period_month": 1,
      "period_year": 2024,
      "types": ["PF"],
      "created_at": "string"
    }
  ],
  "summary": {
    "total_due": 0,
    "total_paid": 0,
    "pending_count": 0
  }
}
```

#### Generate Challan
- **Method**: POST
- **URL**: `/api/web/statutory/challans`
- **Description**: Generates a new challan
- **Request Body**:
```json
{
  "period_month": 1,
  "period_year": 2024,
  "types": ["PF"]
}
```
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "challan_id": "string",
    "status": "draft",
    "message": "Challan generated"
  }
}
```

#### Get Challan by ID
- **Method**: GET
- **URL**: `/api/web/statutory/challans/{challanId}`
- **Description**: Fetches a specific challan
- **Path Parameters**:
  - `challanId`: Challan ID
- **Response**:
```json
{
  "success": true,
  "msg": null,
  "statuscode": 200,
  "data": {
    "id": "string",
    "status": "draft",
    "period_month": 1,
    "period_year": 2024,
    "types": ["PF"],
    "created_at": "string"
  }
}
```

#### Mark Challan as Paid
- **Method**: POST
- **URL**: `/api/web/statutory/challans/{challanId}/mark-paid`
- **Description**: Marks a challan as paid
- **Path Parameters**:
  - `challanId`: Challan ID
- **Request Body**:
```json
{
  "payment_date": "string",
  "payment_mode": "string",
  "reference_number": "string"
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
    "status": "paid",
    "message": "marked as paid"
  }
}
```

#### Download Challan
- **Method**: GET
- **URL**: `/api/web/statutory/challans/{challanId}/download`
- **Description**: Downloads a challan
- **Path Parameters**:
  - `challanId`: Challan ID
- **Query Parameters**:
  - `format`: Download format (pdf, excel)
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
4. For payroll operations, follow the sequence: preview → get results → finalize
5. The API provides both individual and bulk operations for efficiency