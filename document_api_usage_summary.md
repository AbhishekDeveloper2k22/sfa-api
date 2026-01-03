# Document Module API Usage Summary

## Overview
The Document Module handles document management for both employee and company documents. It includes functionality for storing, categorizing, versioning, and tracking document expiry dates. The module supports various document types with different confidentiality levels and retention policies.

## Components and API Usage

### 1. DocumentListPage.jsx
- **getDocuments**: Fetches list of documents with filtering options (category, employee, search)
- **getCategories**: Gets document categories for filtering and display
- **getDownloadUrl**: Gets download URL for specific documents
- **getStats**: Retrieves document statistics for dashboard display
- **getFilterOptions**: Gets filter options for categories, employees, and confidential levels
- **getVersions**: Fetches version history for specific documents

### 2. ExpiringDocumentsPage.jsx
- **getExpiringSummary**: Fetches documents expiring within a specified time period (default 60 days)
- **getDocuments**: Used for viewing expiring documents with expiry date filtering

### 3. Common API Usage
- **createDocument**: Creates new documents in the system
- **updateDocument**: Updates existing document metadata
- **deleteDocument**: Removes documents from the system
- **uploadVersion**: Adds new versions to existing documents
- **restoreVersion**: Restores previous versions of documents
- **extendExpiry**: Updates expiry dates for documents
- **uploadInit** and **uploadComplete**: Handles document file uploads

## Key Features and Business Logic
1. **Document Categories**: Predefined categories with retention policies and required status
2. **Version Control**: Complete version history for documents with restore capability
3. **Expiry Tracking**: Automatic tracking of document expiry dates with alerts
4. **Confidentiality Levels**: Different access levels (public, internal, restricted)
5. **File Management**: Complete file upload and download workflow
6. **Retention Policies**: Automatic retention based on document category

## Data Relationships
- Documents linked to categories and optionally to employees
- Version history linked to individual documents
- Confidentiality levels controlling access permissions
- Expiry dates triggering automated alerts

## API Response Structures
- Documents contain metadata, employee information, category details, and version information
- Categories define retention policies and required status
- Versions track document history with timestamps and notes
- Statistics provide aggregate information about document repository