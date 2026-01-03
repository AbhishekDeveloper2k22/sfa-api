# Policy Module API Usage Summary

## Overview
The Policy Module handles general company policy management, including creating, editing, viewing, and managing company documents and policies. This includes HR policies, code of conduct, remote work policies, and other organizational guidelines.

## Components and API Usage

### 1. PolicyListPage.jsx
- **getPolicies**: Fetches list of all policies with filtering capabilities (category, search)
- **getPolicyStats**: Retrieves policy statistics for dashboard display
- **deletePolicy**: Removes policies from the system
- **exportPolicies**: Exports policy data in various formats

### 2. PolicyDetailPage.jsx
- **getPolicy**: Fetches detailed information for a specific policy
- **downloadPolicy**: Downloads policy document in PDF format
- **sendPolicyEmail**: Sends policy to all employees via email

### 3. PolicyAddPage.jsx
- **createPolicy**: Creates new policy with metadata and content
- **updatePolicy**: Updates existing policy information
- **uploadPolicyAttachment**: Uploads supporting documents to policies
- **removePolicyAttachment**: Removes attachments from policies

## Key Features and Business Logic
1. **Policy Categories**: Policies organized by category (HR, General, Operations, Finance, IT, Compliance)
2. **Version Control**: Complete version history for policies with change tracking
3. **Status Management**: Policies can be in Draft, Active, or Archived states
4. **Content Management**: Rich text content with markdown support
5. **Document Attachments**: Support for uploading related documents
6. **Distribution**: Ability to email policies to all employees

## Data Relationships
- Policies contain metadata (title, category, description, version, status)
- Policies have content in markdown format
- Policies can have multiple attachments
- Revision history tracks all changes to policies

## API Response Structures
- Policies contain complete metadata, content, attachments, and revision history
- Statistics provide aggregate information about policy repository
- Attachments include file information and upload metadata
- Revision history tracks changes with timestamps and user information