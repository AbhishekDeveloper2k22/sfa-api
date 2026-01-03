# Advance API Usage Summary

This document summarizes how the advance APIs are used in the Advance List and Detail pages.

## API Usage in AdvanceListPage.jsx

### 1. Data Loading APIs
- **getAdvances()** - Fetches all advance requests with filters and statistics
- **getEmployees()** - Loads employees for the create advance modal dropdown
- **getReasons()** - Loads reasons for the create advance modal dropdown

### 2. Action APIs
- **createAdvance()** - Creates a new advance request
- **approveAdvance()** - Approves a pending advance request
- **rejectAdvance()** - Rejects a pending advance request
- **disburseAdvance()** - Disburses an approved advance
- **checkActiveAdvance()** - Validates if employee already has an active advance before creating new request

### 3. Navigation APIs
- **getAdvanceById()** - Called when navigating to detail page via table row click

## API Usage in AdvanceDetailPage.jsx

### 1. Data Loading APIs
- **getAdvanceById()** - Fetches detailed advance request data for the specified advance ID
- **getPaymentModes()** - Loads payment modes for the record repayment modal

### 2. Action APIs
- **approveAdvance()** - Approves a pending advance request
- **rejectAdvance()** - Rejects a pending advance request
- **disburseAdvance()** - Disburses an approved advance
- **recordRepayment()** - Records a repayment for an active advance

## Common API Patterns

### 1. Error Handling
All pages implement consistent error handling:
- Loading states with spinners
- Error toasts using [useToast](file:///d:/StartUp%20Product/New%20HRMS%20WEB/src/contexts/ToastContext.jsx#L5-L21) context
- Fallback displays when data is not available

### 2. Filtering
- Status filters for advance status
- Search functionality by ID, name, or employee code
- Department filters

### 3. Flexible Repayment System
- No fixed EMI schedule
- Employee can repay any amount at any time
- Real-time balance calculation
- Payment history tracking

## API Response Structures

### 1. Advance Response
```json
{
  "id": "ADV001",
  "employee_id": "EMP001",
  "employee": {...},
  "amount": 50000,
  "reason": "Medical Emergency",
  "reason_details": "Mother needs surgery...",
  "status": "active",
  "requested_at": "2024-10-15T10:30:00Z",
  "approved_at": "2024-10-16T14:20:00Z",
  "approved_by": "Priya Sharma",
  "disbursed_at": "2024-10-18T11:00:00Z",
  "disbursement_mode": "Bank Transfer",
  "total_repaid": 25000,
  "remaining_balance": 25000,
  "repayment_history": [...]
}
```

### 2. Repayment Response
```json
{
  "id": "REP001",
  "date": "2024-11-05",
  "amount": 10000,
  "mode": "Salary Deduction",
  "remarks": "November salary deduction",
  "recorded_by": "HR Admin"
}
```

### 3. Statistics Response
```json
{
  "total": 7,
  "pending": 2,
  "approved": 1,
  "active": 2,
  "closed": 1,
  "rejected": 1,
  "total_disbursed": 225000,
  "total_recovered": 54000,
  "total_outstanding": 171000,
  "pending_amount": 85000
}
```

## API Integration Points

### 1. Real-time Features
- Status indicators that update after actions
- Balance calculations that update after repayments
- Stats cards that refresh after actions

### 2. Interactive Features
- Approval/rejection workflows
- Disbursement functionality
- Flexible repayment recording
- Filter application with immediate results

### 3. Navigation Integration
- Advance detail page navigation
- Employee profile navigation
- Back navigation to list view

## Performance Considerations

### 1. Caching
- Reference data (employees, reasons, payment modes) loaded once and cached
- Stats data updated after actions
- Pagination for large datasets (though not implemented in current version)

### 2. Loading States
- Skeleton loading for initial load
- Loading indicators during API calls
- Error boundaries for failed requests

## Security Considerations

### 1. Authentication
- All APIs require JWT authentication
- Role-based access (Manager/HR/Finance)
- Employee-specific access for viewing their own advances

### 2. Authorization
- Only authorized personnel can approve/reject advances
- Only HR/Finance can disburse advances
- Only authorized personnel can record repayments
- Validation to prevent duplicate advances for same employee

## Backend Logic Implementation Guidelines

### 1. Status Transitions
- Pending → Approved → Active → Closed (normal flow)
- Pending → Rejected (alternative flow)
- Each status change should trigger appropriate notifications

### 2. Validation Rules
- Check for existing active advances before creating new ones
- Validate repayment amount against remaining balance
- Ensure repayment amount is positive

### 3. Data Consistency
- Total repaid + remaining balance should equal original amount
- Repayment history should be immutable
- Status should be automatically updated based on balance

### 4. Audit Trail
- All actions should be logged with user details
- Timestamps for all status changes
- Repayment recording with "recorded_by" information