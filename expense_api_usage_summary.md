# Expense Module API Usage Summary

## Overview
The Expense Module handles expense claims, travel requests, advances, and reimbursement processes. It includes comprehensive functionality for employees to submit expense claims, managers to approve/reject them, and administrators to manage the entire process.

## Components and API Usage

### 1. ExpenseListPage.jsx
- **getExpenses**: Fetches list of expense claims with filtering options (status, employee)
- **getFilterOptions**: Gets filter options for status, categories, and employees
- **expenseAction**: Performs approve/reject actions on expense claims
- **getStats**: Retrieves expense statistics for dashboard display

### 2. ExpenseDetailPage.jsx
- **getExpense**: Fetches detailed information for a specific expense claim
- **expenseAction**: Performs approve/reject/settle actions on expense claims
- **computePreview**: Validates expense claim before submission (category limits, receipt requirements)

### 3. TravelRequestsPage.jsx
- **getTravelRequests**: Fetches list of travel requests with filtering options
- **travelAction**: Performs approve/reject actions on travel requests

### 4. TravelRequestDetailPage.jsx
- **getTravelRequest**: Fetches detailed information for a specific travel request
- **travelAction**: Performs approve/reject actions on travel requests

### 5. Common API Usage
- **getCategories**: Retrieves expense categories with limits and requirements
- **getAdvances**: Fetches advance requests for employees
- **getLedger**: Retrieves expense ledger entries combining advances and reimbursements
- **exportExpenses**: Generates expense exports in CSV format
- **extractReceipt**: Performs OCR on uploaded receipts

## Key Features and Business Logic
1. **Expense Categories**: Predefined categories with daily limits, per-claim limits, and receipt requirements
2. **Multi-stage Approval**: Draft → Pending → Approved → Settled workflow
3. **Travel Integration**: Linking travel requests to expense claims
4. **Validation Rules**: Category limits, receipt requirements, overlapping checks
5. **Financial Tracking**: Ledger system for advances and reimbursements
6. **OCR Processing**: Automated receipt data extraction

## Data Relationships
- Expense claims linked to employees
- Travel requests linked to expense claims (via trip_id)
- Advances linked to employees and optionally to travel requests
- Line items categorized within expense claims

## API Response Structures
- Expense claims contain employee details, line items, status, dates, and approval information
- Travel requests include itinerary, cost estimates, advance requirements
- Categories define limits and requirements for expense submission
- Advances track disbursement and settlement status