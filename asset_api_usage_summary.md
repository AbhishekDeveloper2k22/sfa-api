# Asset Module API Usage Summary

## Overview
The Asset Module handles company asset management including inventory tracking, assignment, maintenance, and depreciation. It provides functionality to manage physical assets from acquisition to disposal, including employee assignments and maintenance schedules.

## Components and API Usage

### 1. AssetListPage.jsx
- **getAssets**: Fetches list of all assets with filtering capabilities (status, category)
- **getCategories**: Gets asset categories for filtering and display
- **getStats**: Retrieves asset statistics for dashboard display
- **assignAsset**: Assigns assets to employees
- **returnAsset**: Returns assets from employees
- **getFilterOptions**: Gets filter options for status, categories, and locations

### 2. AssetDetailPage.jsx
- **getAsset**: Fetches detailed information for a specific asset
- **getCategories**: Gets asset category information
- **getLocations**: Gets location information
- **assignAsset**: Assigns asset to an employee
- **returnAsset**: Returns asset from an employee

### 3. AssetRequestsPage.jsx
- **getRequests**: Fetches asset requests with status filtering
- **createRequest**: Creates new asset requests
- **requestAction**: Approves or denies asset requests
- **getEmployees**: Gets employee information for requests

### 4. AssetMaintenancePage.jsx
- **getMaintenanceLogs**: Fetches maintenance records
- **createMaintenanceLog**: Creates new maintenance records
- **completeMaintenanceLog**: Marks maintenance as completed

### 5. Common API Usage
- **getDepreciation**: Calculates asset depreciation
- **getLocations**: Gets asset location information
- **getEmployees**: Gets employee information for assignments

## Key Features and Business Logic
1. **Asset Categories**: Predefined categories with depreciation years
2. **Asset Status**: Assets can be available, assigned, under maintenance, or retired
3. **Employee Assignment**: Assets can be assigned to employees with tracking
4. **Maintenance Management**: Complete maintenance tracking with vendors and costs
5. **Depreciation Tracking**: Automatic depreciation calculation based on purchase price
6. **Warranty Management**: Warranty tracking and expiration monitoring
7. **Asset Requests**: Employee request system for new assets

## Data Relationships
- Assets linked to categories, locations, and assigned employees
- Maintenance logs linked to specific assets
- Asset requests linked to employees and asset categories
- Depreciation calculated based on purchase price and depreciation years

## API Response Structures
- Assets contain complete metadata including purchase information, depreciation, and assignment details
- Categories define depreciation years and asset types
- Maintenance logs track issues, costs, and completion status
- Asset requests contain employee information and request details