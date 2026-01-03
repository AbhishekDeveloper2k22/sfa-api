# Leave API Usage Summary

This document summarizes how the leave APIs are used in the Leave List, Detail, and Balance pages.

## API Usage in LeaveListPage.jsx

### 1. Data Loading APIs
- **getFilterOptions()** - Loads filter options for leave types, departments, employees
- **getLeaveStats()** - Fetches leave statistics for the stats cards
- **getLeaveRequests()** - Fetches leave requests for the table view
- **getTeamCalendar()** - Fetches calendar data when viewMode is 'calendar'

### 2. Action APIs
- **leaveAction()** - Performs approve/reject actions on individual leave requests
- **bulkApprove()** - Performs bulk approval of selected leave requests

### 3. Navigation APIs
- **getLeaveRequest()** - Called when navigating to detail page via table row click or calendar day click

### 4. Calendar APIs
- **getTeamCalendar()** - Fetches calendar data for the calendar view

## API Usage in LeaveDetailPage.jsx

### 1. Data Loading APIs
- **getLeaveRequest()** - Fetches detailed leave request data for the specified leave ID

### 2. Action APIs
- **leaveAction()** - Performs approve/reject/cancel actions on the leave request

## API Usage in LeaveBalancePage.jsx

### 1. Data Loading APIs
- **getLeaveBalances()** - Fetches current leave balances for the employee
- **getLeaveHistory()** - Fetches leave history and transaction data

### 2. Action APIs
- **requestEncashment()** - Requests encashment of unused leave balance

## Common API Patterns

### 1. Error Handling
All pages implement consistent error handling:
- Loading states with spinner
- Error toasts using [useToast](file:///d:/StartUp%20Product/New%20HRMS%20WEB/src/contexts/ToastContext.jsx#L5-L21) context
- Fallback displays when data is not available

### 2. Filtering
- Query parameters for search
- Status filters for leave status
- Leave type filters
- Date range filters
- Department filters
- Employee filters

### 3. Pagination
- Server-side pagination for leave requests
- Page size options (10, 25, 50, 100)
- Total counts and page numbers

## API Response Structures

### 1. Leave Request Response
```json
{
  "id": "lr_0001",
  "applicant": {...},
  "applicant_id": "emp_001",
  "leave_type": "CL",
  "leave_type_name": "Casual Leave",
  "leave_type_color": "#3B82F6",
  "from_date": "2025-01-15",
  "to_date": "2025-01-17",
  "is_half_day": false,
  "duration": 3,
  "reason": "Family function",
  "status": "pending",
  "created_at": "2025-01-10T09:30:00Z",
  "approvals": [...]
}
```

### 2. Leave Balance Response
```json
[
  {
    "leave_type": "CL",
    "leave_type_name": "Casual Leave",
    "opening": 12,
    "accrued": 0,
    "taken": 4,
    "pending": 1,
    "available": 7,
    "color": "#3B82F6"
  }
]
```

### 3. Calendar Events Response
```json
{
  "month": 1,
  "year": 2025,
  "events": [...],
  "holidays": [...]
}
```

## API Integration Points

### 1. Real-time Features
- Stats cards that update after actions
- Status indicators that change after approval/rejection
- Calendar views that refresh after actions

### 2. Interactive Features
- Day click functionality in calendar view
- Approval/rejection workflows
- Bulk action capabilities
- Filter application with immediate results
- Pagination with preserved state

### 3. Navigation Integration
- Leave detail page navigation
- Employee profile navigation
- Calendar navigation between months
- Back navigation to list view

## Performance Considerations

### 1. Caching
- Filter options loaded once and cached
- Stats data updated after actions
- Pagination to handle large datasets

### 2. Loading States
- Skeleton loading for initial load
- Loading indicators during API calls
- Error boundaries for failed requests

## Security Considerations

### 1. Authentication
- All APIs require JWT authentication
- Role-based access (Admin/HR for list page)
- Employee-specific access for balance page

### 2. Authorization
- Employees can only view their own balance data
- Managers can approve/reject for their team
- Admins have full access to all data
- Approval workflows follow organizational hierarchy