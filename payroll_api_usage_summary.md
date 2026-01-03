# Payroll API Usage Summary

This document summarizes how the payroll APIs are used in the Payroll List, Run, Detail, Payslip, Salary Structure, and Challan Manager pages.

## API Usage in PayrollListPage.jsx

### 1. Data Loading APIs
- **getPayrollRuns()** - Fetches all payroll runs with filters and pagination
- **getStats()** - Fetches payroll statistics for the stats cards

### 2. Navigation APIs
- **getPayrollRun()** - Called when navigating to detail page via table row click

## API Usage in PayrollRunPage.jsx

### 1. Configuration APIs
- **getFilterOptions()** - Loads filter options for run types, departments, etc.

### 2. Processing APIs
- **startPreview()** - Starts a payroll preview job
- **getJobStatus()** - Polls job status during preview generation
- **getPreviewResults()** - Gets preview results after job completion
- **finalizePayroll()** - Finalizes the payroll run

### 3. Export APIs
- **exportPayroll()** - Exports payroll data

## API Usage in PayrollDetailPage.jsx

### 1. Data Loading APIs
- **getPayrollRun()** - Fetches specific payroll run details
- **getAllPayslips()** - Fetches all payslips for the payroll run period

### 2. Export APIs
- **exportPayroll()** - Exports payroll data
- **downloadPayslip()** - Downloads individual payslips

## API Usage in PayslipDetailPage.jsx

### 1. Data Loading APIs
- **getPayslipById()** - Fetches specific payslip details

### 2. Download APIs
- **downloadPayslip()** - Downloads payslip in specified format

## API Usage in SalaryStructurePage.jsx

### 1. CRUD APIs
- **getSalaryStructures()** - Fetches all salary structures
- **createSalaryStructure()** - Creates a new salary structure
- **updateSalaryStructure()** - Updates an existing salary structure
- **deleteSalaryStructure()** - Deletes a salary structure
- **getSalaryStructure()** - Fetches specific salary structure

### 2. Validation APIs
- **validateFormula()** - Validates salary calculation formulas

## API Usage in ChallanManagerPage.jsx

### 1. Data Loading APIs
- **getChallans()** - Fetches all statutory challans with filters
- **getFilterOptions()** - Loads filter options for challan types

### 2. CRUD APIs
- **getChallan()** - Fetches specific challan details
- **generateChallan()** - Generates new statutory challans
- **markChallanPaid()** - Marks challan as paid
- **downloadChallan()** - Downloads challan documents

## Common API Patterns

### 1. Error Handling
All pages implement consistent error handling:
- Loading states with spinners
- Error toasts using [useToast](file:///d:/StartUp%20Product/New%20HRMS%20WEB/src/contexts/ToastContext.jsx#L5-L21) context
- Fallback displays when data is not available

### 2. Filtering
- Status filters for payroll run status
- Period filters (month/year) for payroll runs and payslips
- Type filters for different challan types
- Search functionality by employee name or code

### 3. Asynchronous Processing
- Payroll preview jobs with progress tracking
- Background job polling for status updates
- File download handling with temporary URLs

## API Response Structures

### 1. Payroll Run Response
```json
{
  "id": "run_001",
  "period_month": 12,
  "period_year": 2024,
  "run_type": "regular",
  "status": "finalized",
  "employee_count": 8,
  "totals": {
    "gross": 425000,
    "net": 382500,
    "pf_total": 14400,
    "esi_total": 2800,
    "pt_total": 1600,
    "employer_cost": 445000
  }
}
```

### 2. Payslip Response
```json
{
  "id": "ps_run_001_emp_001",
  "payroll_run_id": "run_001",
  "employee_id": "emp_001",
  "employee": {...},
  "period_month": 12,
  "period_year": 2024,
  "salary_structure": "STD_INDIA",
  "earnings": [...],
  "deductions": [...],
  "gross": 45000,
  "total_deductions": 2500,
  "net_pay": 42500,
  "attendance_breakdown": {...},
  "warnings": ["Missing bank account details"],
  "status": "finalized",
  "generated_at": "2024-12-01T10:00:00Z"
}
```

### 3. Salary Structure Response
```json
{
  "id": "struct_001",
  "code": "STD_INDIA",
  "name": "Standard India CTC",
  "description": "Standard CTC structure for Indian employees with PF & ESI",
  "effective_from": "2024-04-01",
  "version": 1,
  "is_active": true,
  "components": [
    {
      "code": "BASIC",
      "label": "Basic Salary",
      "type": "earning",
      "value_type": "percentage_of",
      "value": 40,
      "reference": "CTC",
      "taxable": true,
      "gl_code": "SAL001",
      "sequence": 1
    }
  ]
}
```

### 4. Challan Response
```json
{
  "id": "ch_001",
  "payroll_run_id": "run_001",
  "type": "PF",
  "period_month": 12,
  "period_year": 2024,
  "amount": 28800,
  "employee_share": 14400,
  "employer_share": 14400,
  "due_date": "2024-12-15",
  "status": "paid",
  "paid_at": "2024-12-10T10:00:00Z",
  "payment_ref": "UTR123456789",
  "lines": [
    {
      "employee_id": "emp_001",
      "employee_name": "Rajesh Kumar",
      "employee_code": "EMP001",
      "employee_share": 1800,
      "employer_share": 1800
    }
  ]
}
```

## API Integration Points

### 1. Real-time Features
- Job progress tracking during payroll preview
- Status indicators that update after actions
- Stats cards that refresh after actions

### 2. Interactive Features
- Payroll run configuration
- Salary structure builder with formula validation
- Challan generation and payment tracking
- Filter application with immediate results

### 3. Navigation Integration
- Payroll detail page navigation
- Payslip detail page navigation
- Salary structure editor navigation
- Challan detail page navigation

## Performance Considerations

### 1. Caching
- Filter options loaded once and cached
- Salary structures loaded once and cached
- Stats data updated after actions
- Pagination to handle large datasets

### 2. Loading States
- Skeleton loading for initial load
- Loading indicators during API calls
- Progress bars for long-running operations
- Error boundaries for failed requests

## Security Considerations

### 1. Authentication
- All APIs require JWT authentication
- Role-based access (Admin/HR/Finance)
- Employee-specific access for viewing their own payslips

### 2. Authorization
- Only authorized personnel can finalize payroll runs
- Only HR/Finance can manage salary structures
- Only authorized personnel can mark challans as paid
- Validation to prevent unauthorized access to sensitive salary data