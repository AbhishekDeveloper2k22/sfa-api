# Holiday Module API Usage Summary

## Overview
The Holiday Module handles company holiday calendar management, including national holidays, festival holidays, and optional holidays. It provides functionality to track, manage, and display holidays for the organization.

## Components and API Usage

### 1. HolidayListPage.jsx
- **getHolidays**: Fetches list of all holidays with filtering capabilities (type, search)
- **getHolidayStats**: Retrieves holiday statistics for dashboard display
- **createHoliday**: Creates new holiday entries in the system
- **updateHoliday**: Updates existing holiday information
- **deleteHoliday**: Removes holidays from the system
- **searchHolidays**: Searches holidays by name or description

## Key Features and Business Logic
1. **Holiday Types**: Supports different types of holidays (National, Festival, Optional)
2. **Status Management**: Holidays can be upcoming or in the past
3. **Date Management**: Comprehensive date handling for holiday scheduling
4. **Search and Filter**: Advanced search and filtering capabilities
5. **Calendar Integration**: Holiday data for calendar displays
6. **Description Management**: Detailed descriptions for each holiday

## Data Relationships
- Holidays contain name, date, type, and description
- Holiday types categorized as National, Festival, or Optional
- Status tracking based on current date (upcoming vs past)
- Search functionality across name and description fields

## API Response Structures
- Holidays contain complete information including name, date, type, and description
- Statistics provide aggregate information about holiday counts by type
- Holiday types differentiate between National, Festival, and Optional holidays
- Date fields follow ISO format for consistency