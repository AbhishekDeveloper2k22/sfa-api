# Celebration Module API Usage Summary

## Overview
The Celebration Module handles employee celebrations such as birthdays and work anniversaries. It provides functionality to track, manage, and send wishes for special occasions within the organization.

## Components and API Usage

### 1. CelebrationsPage.jsx
- **getTodaysCelebrations**: Fetches list of celebrations happening today
- **getWeeklyCelebrations**: Fetches celebrations for the current week
- **getWorkAnniversaries**: Fetches work anniversaries for the organization
- **getSpecialEvents**: Fetches special company events and celebrations

### 2. CelebrationsListPage.jsx
- **getCelebrations**: Fetches list of all celebrations with filtering capabilities (type, employee name, department)
- **getCelebrationStats**: Retrieves celebration statistics for dashboard display
- **sendCelebrationWish**: Sends automated wishes to employees for their special occasions
- **addCelebrationEvent**: Adds new celebration events to the system

## Key Features and Business Logic
1. **Celebration Types**: Supports different types of celebrations (Birthdays, Work Anniversaries)
2. **Status Management**: Celebrations can be Upcoming or Completed
3. **Employee Integration**: Linked to employee records for personalized messaging
4. **Automated Wishes**: System can send automated birthday and anniversary wishes
5. **Filtering and Search**: Comprehensive search and filtering capabilities
6. **Department-wise Tracking**: Celebrations tracked by department

## Data Relationships
- Celebrations linked to employees and their departments
- Celebration types categorized as Birthday or Work Anniversary
- Status tracking for each celebration event
- Message templates for different celebration types

## API Response Structures
- Celebrations contain employee information, type, date, message, and status
- Statistics provide aggregate information about celebration counts
- Employee details include name, ID, and department information
- Celebration types differentiate between birthdays and work anniversaries