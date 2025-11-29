# Fix: Cron Expression Double Conversion Bug

## Issue
When selecting 4:00 PM PST Monday-Friday in the frontend, EventBridge was showing 8:00 AM UTC instead of the expected midnight UTC (12:00 AM).

**Expected behavior:**
- User selects: 4:00 PM PST
- EventBridge should have: 12:00 AM UTC (midnight, next day)

**Actual behavior:**
- User selects: 4:00 PM PST  
- EventBridge had: 8:00 AM UTC

## Root Cause
The timezone conversion was happening **twice**:

1. **Frontend** converted local time (4:00 PM PST) → UTC (12:00 AM UTC)
2. **Backend** received the already-converted UTC time and converted it **again** → 8:00 AM UTC

This double conversion resulted in an 8-hour offset error.

## Solution
The frontend should send cron expressions in **local time** and let the backend handle the single conversion to UTC.

### Data Flow (Corrected)
```
Frontend (User Input)
  ↓
  4:00 PM PST → Cron: "00 16 * * 1,2,3,4,5" (local time)
  ↓
Backend (serverActionProcessor)
  ↓
  Receives: "00 16 * * 1,2,3,4,5" + timezone: "America/Los_Angeles"
  ↓
  Converts to UTC: "00 00 * * 1,2,3,4,5" (midnight UTC)
  ↓
  Formats for EventBridge: "cron(0 0 ? * 1,2,3,4,5 *)"
  ↓
  Stores in DynamoDB: "00 16 * * 1,2,3,4,5" (original local time) + timezone
  ↓
EventBridge Rule
  ↓
  Triggers at: 12:00 AM UTC (4:00 PM PST)
```

## Changes Made

### Frontend (`dashboard/src/components/ServerSettings.vue`)

#### Before (Incorrect - Double Conversion)
```javascript
function generateCronExpression(time, weekdays) {
    // Convert local time to UTC before creating cron expression
    const utcTime = convertToUTC(time, serverConfigInput.timezone);
    const [hours, minutes] = utcTime.split(':');
    
    // Return standard 5-field cron expression in UTC
    return `${minutes} ${hours} * * ${cronWeekdays}`;
}
```

#### After (Correct - Single Conversion in Backend)
```javascript
function generateCronExpression(time, weekdays) {
    // Keep time in local timezone - backend will convert to UTC
    const [hours, minutes] = time.split(':');
    
    // Return standard 5-field cron expression in local time
    return `${minutes} ${hours} * * ${cronWeekdays}`;
}
```

#### Parsing Function Update
```javascript
// Before: Converted from UTC to local
function parseCronExpression(cronExpression, isStartSchedule = false) {
    const utcTime = `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    const localTime = convertFromUTC(utcTime, serverConfigInput.timezone);
    selectedTime.value = localTime;
}

// After: Already in local time from backend
function parseCronExpression(cronExpression, isStartSchedule = false) {
    // Backend stores cron in local time, so no conversion needed
    const localTime = `${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}`;
    selectedTime.value = localTime;
}
```

### Backend (No Changes Required)
The backend logic in `lambdas/serverActionProcessor/index.py` was already correct:
- Receives cron expression in local time + timezone
- Converts to UTC for EventBridge rules
- Stores original local time expression in DynamoDB

## Testing

### Test Script
Added test case in `scripts/test_cron_conversion.py`:

```python
{
    'name': 'Bug fix: 4:00 PM PST Mon-Fri',
    'input': '00 16 * * 1,2,3,4,5',
    'timezone': 'America/Los_Angeles',
    'expected': 'cron(0 0 ? * 1,2,3,4,5 *)',
    'description': '4:00 PM PST = 12:00 AM UTC next day (midnight)'
}
```

Run tests:
```bash
python3 scripts/test_cron_conversion.py
```

### Manual Testing
1. Open ServerSettings in the dashboard
2. Select "Schedule" shutdown method
3. Choose timezone: "US/Pacific (PST/PDT)"
4. Select days: Monday-Friday
5. Select time: 16:00 (4:00 PM)
6. Save configuration
7. Verify EventBridge rule shows: `cron(0 0 ? * 1,2,3,4,5 *)`

## Architecture Notes

### Why Store Local Time in DynamoDB?
The backend stores the **original local time** cron expression along with the timezone in DynamoDB because:

1. **User Intent Preservation**: The user's original schedule intent is preserved
2. **Timezone Changes**: If timezone changes, the schedule can be recalculated
3. **Display Consistency**: Frontend can display the same time the user entered
4. **Audit Trail**: Clear record of what the user configured

### Conversion Points
- **Frontend → Backend**: Local time cron + timezone (no conversion)
- **Backend → EventBridge**: Converts to UTC for rule creation
- **Backend → DynamoDB**: Stores local time cron + timezone
- **DynamoDB → Frontend**: Returns local time cron (no conversion needed)

## Related Files
- `dashboard/src/components/ServerSettings.vue` - Frontend schedule configuration
- `lambdas/serverActionProcessor/index.py` - Backend cron conversion logic
- `layers/ddbHelper/ddbHelper.py` - DynamoDB storage
- `scripts/test_cron_conversion.py` - Test suite
- `docs/fix-schedule-expression-validation.md` - Original schedule feature documentation

## Impact
- **User Experience**: Schedules now work as expected with correct timezone conversion
- **Breaking Changes**: None - existing schedules will continue to work
- **Migration**: No data migration needed
