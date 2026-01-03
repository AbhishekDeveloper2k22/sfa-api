# Announcement Module API Usage Summary

## Overview
The Announcement Module handles company-wide announcements and updates. It provides functionality to create, manage, and distribute important company communications to employees. The module supports different categories, priority levels, and target audiences for announcements.

## Components and API Usage

### 1. AnnouncementsPage.jsx
- **getAnnouncementStats**: Fetches announcement statistics for dashboard display
- **getRecentAnnouncements**: Gets recent announcements for overview

### 2. AnnouncementsListPage.jsx
- **getAnnouncements**: Fetches list of all announcements with filtering capabilities (category, search)
- **getAnnouncementStats**: Retrieves announcement statistics for dashboard display
- **createAnnouncement**: Creates new announcement entries in the system
- **updateAnnouncement**: Updates existing announcement information
- **deleteAnnouncement**: Removes announcements from the system
- **searchAnnouncements**: Searches announcements by title, category, or description

### 3. AnnouncementDetailPage.jsx
- **getAnnouncement**: Fetches detailed information for a specific announcement
- **updateAnnouncement**: Updates announcement status or information
- **deleteAnnouncement**: Removes announcement from the system
- **shareAnnouncement**: Shares announcement with target audience
- **trackAnnouncementViews**: Tracks announcement view statistics

### 4. AnnouncementAddPage.jsx
- **createAnnouncement**: Creates new announcement with all required metadata
- **updateAnnouncement**: Updates existing announcement information
- **validateAnnouncement**: Validates announcement data before saving

## Key Features and Business Logic
1. **Announcement Categories**: Organized by category (Holiday, Policy, Event, etc.)
2. **Priority Levels**: Three priority levels (High, Medium, Low) for importance classification
3. **Status Management**: Announcements can be Draft, Active, or Expired
4. **Date Management**: Published and expiry date management
5. **Target Audience**: Ability to target specific employee groups
6. **View Tracking**: Track how many times an announcement has been viewed
7. **Content Management**: Rich text content with markdown support

## Data Relationships
- Announcements contain metadata (title, category, priority, status)
- Announcements have content in markdown format
- Published and expiry dates control visibility
- Target audience defines who can see the announcement
- View tracking provides engagement metrics

## API Response Structures
- Announcements contain complete metadata, content, and engagement data
- Statistics provide aggregate information about announcement repository
- Categories define different types of announcements
- Priority levels indicate importance of announcements