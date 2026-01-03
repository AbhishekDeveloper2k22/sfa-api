# Attendance API Usage Summary

This document summarizes how the attendance APIs are used in the Attendance List and Detail pages.

## API Usage in AttendanceListPage.jsx

### 1. Data Loading APIs
- **getFilterOptions()** - Loads filter options for departments, shifts, locations, etc.
- **getStats()** - Fetches attendance statistics for the stats cards
- **getLiveAttendance()** - Fetches live attendance data when viewMode is 'live'
- **getDailyAttendance()** - Fetches historical attendance data when viewMode is 'history'

### 2. Navigation APIs
- **getMonthlyAttendance()** - Called when navigating to detail page via table row click
- **createManualRequest()** - Called when submitting a correction request from the list page

### 3. Auto-refresh
- **getLiveAttendance()** - Called every 30 seconds in live view mode to refresh data

## API Usage in AttendanceDetailPage.jsx

### 1. Initial Data Loading
- **getMonthlyAttendance()** - Fetches monthly attendance data for the specified employee (using route param id)

### 2. Interaction APIs
- **createManualRequest()** - Called when user submits a correction request for a specific day

## Common API Patterns

### 1. Error Handling
Both pages implement consistent error handling:
- Loading states with spinner
- Error toasts using [useToast](file:///d:/StartUp%20Product/New%20HRMS%20WEB/src/contexts/ToastContext.jsx#L5-L21) context
- Fallback displays when data is not available

### 2. Filtering
- Query parameters for search
- Status filters for attendance status
- Department, shift, location filters
- Date range filters for historical data

### 3. Pagination
- Server-side pagination for historical data
- Client-side handling for live data
- Page size options (10, 25, 50, 100)

## API Response Structures

### 1. Live Attendance Response
```json
{
  "data": [...],
  "stats": {
    "present_today": 0,
    "checked_in": 0,
    "late_today": 0,
    "absent_today": 0,
    "on_leave_today": 0,
    "avg_work_hours": 0
  }
}
```

### 2. Historical Attendance Response
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total": 0,
    "total_pages": 1
  }
}
```

### 3. Monthly Attendance Response
```json
{
  "records": [...],
  "summary": {
    "total_days": 0,
    "present_days": 0,
    "absent_days": 0,
    "late_days": 0,
    "leave_days": 0,
    "half_days": 0,
    "weekly_off_days": 0,
    "total_late_minutes": 0,
    "total_ot_minutes": 0,
    "avg_work_hours": 0
  },
  "employee": {...}
}
```

## API Integration Points

### 1. Real-time Features
- Live attendance auto-refreshes every 30 seconds
- Status indicators that update automatically
- Current day highlighting in calendar view

### 2. Interactive Features
- Day click functionality in calendar view
- Correction request submission
- Filter application with immediate results
- Pagination with preserved state

### 3. Navigation Integration
- Employee detail page navigation
- Link to manual requests page
- Link to OT requests page
- Link to roster management

## Performance Considerations

### 1. Caching
- Filter options loaded once and cached
- Stats data updated periodically
- Pagination to handle large datasets

### 2. Loading States
- Skeleton loading for initial load
- Loading indicators during API calls
- Error boundaries for failed requests

## Security Considerations

### 1. Authentication
- All APIs require JWT authentication
- Role-based access (Admin/HR only for list page)
- Employee-specific access for detail page

### 2. Authorization
- Employees can only view their own detailed data
- Managers can view reports for their team
- Admins have full access to all data