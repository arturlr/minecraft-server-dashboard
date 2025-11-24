# Timezone Support for Server Schedules

## Overview
Added timezone support to the server schedule configuration, allowing users to set schedules in their local timezone. The system automatically converts local times to UTC for EventBridge rules.

## Changes Made

### 1. GraphQL Schema (`appsync/schema.graphql`)
- Added `timezone: String` field to `ServerConfig` type
- Added `timezone: String` field to `ServerConfigInput` input type

### 2. Frontend (`dashboard/src/components/ServerSettings.vue`)

#### New Features
- **Timezone Selector**: Dropdown with common timezones (US, Europe, Asia, Australia)
- **Automatic Conversion**: Local times are converted to UTC when saving
- **Display in Local Time**: Stored UTC times are converted back to local time when loading

#### Key Functions
- `convertToUTC(time, timezone)`: Converts local time to UTC
- `convertFromUTC(time, timezone)`: Converts UTC time to local timezone
- `generateCronExpression(time, weekdays, timezone)`: Generates cron expression in UTC

#### UI Changes
- Added timezone selector in schedule configuration section
- Time fields now show timezone hint (e.g., "Time when the server should shutdown (America/New_York)")
- Timezone is displayed in schedule summary

### 3. Backend (`layers/ec2Helper/ec2Helper.py`)

#### Tag Storage
- Added `timezone` field to `get_instance_attributes_from_tags()` function
- Defaults to 'UTC' if not set
- Stored as EC2 instance tag (automatically handled by `set_instance_attributes_to_tags()`)

### 4. GraphQL Queries/Mutations
- Updated `getServerConfig` query to include `timezone` field
- Updated `putServerConfig` mutation to include `timezone` field

## How It Works

### Saving Configuration
1. User selects timezone (e.g., "America/New_York")
2. User sets schedule time in local timezone (e.g., "23:00")
3. Frontend sends local time cron expression and timezone to backend (e.g., "0 23 * * 1,2,3" + "America/New_York")
4. Backend converts local time to UTC using pytz (e.g., "0 23 * * 1,2,3" EST → "0 4 * * 2,3,4" UTC)
5. Backend creates EventBridge rule with UTC time
6. Both cron expression (in local time) and timezone are stored as EC2 instance tags

### Loading Configuration
1. Backend retrieves cron expression from tags (stored in local timezone)
2. Backend retrieves timezone from tags
3. Frontend receives local time cron expression and timezone
4. Frontend displays schedule in the stored local timezone
5. User sees schedule in their configured timezone

## Supported Timezones
- UTC
- America/New_York (EST/EDT)
- America/Chicago (CST/CDT)
- America/Denver (MST/MDT)
- America/Los_Angeles (PST/PDT)
- Europe/London (GMT/BST)
- Europe/Paris (CET/CEST)
- Asia/Tokyo (JST)
- Asia/Shanghai (CST)
- Australia/Sydney (AEDT/AEST)

## Testing
A test file is provided at `dashboard/test_timezone_conversion.html` to verify timezone conversion logic.

## Example

### User Input
- Timezone: America/New_York (EST, UTC-5)
- Stop Time: 23:00 (11 PM local)
- Days: Monday, Tuesday, Wednesday

### Stored in EC2 Tags
- Cron Expression: `0 23 * * 1,2,3` (stored in local time)
- Timezone Tag: America/New_York

### EventBridge Rule (Created by Backend)
- Schedule: `cron(0 4 ? * 2,3,4 *)` (converted to UTC)
- Triggers at 4 AM UTC = 11 PM EST

## Notes
- All EventBridge rules are created in UTC (AWS requirement)
- Cron expressions are stored in local timezone in EC2 tags for user convenience
- Timezone conversion happens in backend using Python's pytz library
- Timezone conversion handles DST automatically
- Day-of-week may shift when converting across midnight (handled automatically by pytz)
- Existing servers without timezone tag default to UTC
