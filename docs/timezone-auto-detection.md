# Timezone Auto-Detection Implementation

## Overview
The system now automatically detects the user's browser timezone and uses it for schedule configuration, eliminating the need for manual timezone selection.

## Data Storage in DynamoDB

### Schema
The `timezone` field is stored as a String in the ServerConfig table:

```graphql
type ServerConfig {
    id: String!
    shutdownMethod: String
    stopScheduleExpression: String      # Cron in local time
    startScheduleExpression: String     # Cron in local time
    timezone: String                    # IANA timezone (e.g., "America/Los_Angeles")
    alarmThreshold: Float
    alarmEvaluationPeriod: Int
    runCommand: String
    workDir: String
    # ... other fields
}
```

### DynamoDB Item Example
```json
{
    "id": "i-1234567890abcdef0",
    "shutdownMethod": "Schedule",
    "stopScheduleExpression": "00 16 * * 1,2,3,4,5",
    "startScheduleExpression": "00 08 * * 1,2,3,4,5",
    "timezone": "America/Los_Angeles",
    "alarmThreshold": 0,
    "alarmEvaluationPeriod": 0,
    "runCommand": "java -jar server.jar",
    "workDir": "/opt/minecraft",
    "updatedAt": "2024-01-15T10:30:00.000Z",
    "createdAt": "2024-01-10T08:00:00.000Z"
}
```

## Complete Data Flow

### 1. User Opens Settings
```
Browser
  ↓
  dayjs.tz.guess() → "America/Los_Angeles"
  ↓
Frontend State
  detectedTimezone.value = "America/Los_Angeles"
  serverConfigInput.timezone = "America/Los_Angeles"
```

### 2. User Configures Schedule
```
User Input:
  - Days: Monday-Friday
  - Time: 4:00 PM (16:00)
  
Frontend Processing:
  - generateCronExpression("16:00", ["MON","TUE","WED","THU","FRI"])
  - Returns: "00 16 * * 1,2,3,4,5" (local time)
  
GraphQL Mutation:
  putServerConfig({
    id: "i-1234567890abcdef0",
    shutdownMethod: "Schedule",
    stopScheduleExpression: "00 16 * * 1,2,3,4,5",
    timezone: "America/Los_Angeles"
  })
```

### 3. Backend Processing
```
ec2ActionWorker Lambda
  ↓
  Receives:
    - stopScheduleExpression: "00 16 * * 1,2,3,4,5"
    - timezone: "America/Los_Angeles"
  ↓
  Stores in DynamoDB (via ddbHelper):
    - stopScheduleExpression: "00 16 * * 1,2,3,4,5" (original local time)
    - timezone: "America/Los_Angeles"
  ↓
  Converts for EventBridge:
    - _format_schedule_expression("00 16 * * 1,2,3,4,5", "America/Los_Angeles")
    - Returns: "cron(0 0 ? * 1,2,3,4,5 *)" (UTC midnight)
  ↓
  Creates EventBridge Rule:
    - Name: "shutdown-i-1234567890abcdef0"
    - ScheduleExpression: "cron(0 0 ? * 1,2,3,4,5 *)"
    - State: ENABLED
```

### 4. User Reopens Settings
```
Frontend Query:
  getServerConfig(id: "i-1234567890abcdef0")
  ↓
Backend Response:
  {
    stopScheduleExpression: "00 16 * * 1,2,3,4,5",
    timezone: "America/Los_Angeles"
  }
  ↓
Frontend Processing:
  - Browser detects: "America/Los_Angeles" (same timezone)
  - parseCronExpression("00 16 * * 1,2,3,4,5")
  - Displays: 4:00 PM (16:00)
  - Shows: "Detected Timezone: America/Los_Angeles (UTC-08:00)"
```

## Timezone Change Scenarios

### Scenario 1: User Travels to Different Timezone
```
Original Config:
  - Timezone: America/Los_Angeles (PST)
  - Schedule: 4:00 PM PST → Midnight UTC
  
User travels to New York:
  - Browser detects: America/New_York (EST)
  - Opens settings
  - Sees: "Detected Timezone: America/New_York (UTC-05:00)"
  - Old schedule shows: 4:00 PM (from stored cron)
  
If user saves without changes:
  - New timezone: America/New_York
  - Same cron: "00 16 * * 1,2,3,4,5"
  - EventBridge: "cron(0 21 ? * 1,2,3,4,5 *)" (9 PM UTC)
  - Server now shuts down at 4:00 PM EST (their new local time)
```

### Scenario 2: Daylight Saving Time
```
Winter (PST = UTC-8):
  - User sets: 4:00 PM PST
  - EventBridge: Midnight UTC
  
Summer (PDT = UTC-7):
  - Browser still detects: America/Los_Angeles
  - dayjs automatically handles DST
  - User sets: 4:00 PM PDT
  - EventBridge: 11:00 PM UTC (1 hour earlier)
  
Note: IANA timezone names (America/Los_Angeles) handle DST automatically
```

## Storage Details

### DynamoDB Table: ServerConfig
- **Partition Key**: `id` (String) - EC2 instance ID
- **Attributes**:
  - `timezone`: String - IANA timezone identifier
  - `stopScheduleExpression`: String - Cron in local time
  - `startScheduleExpression`: String - Cron in local time
  - `shutdownMethod`: String - "Schedule", "CPUUtilization", or "Connections"
  - Other config fields...

### Why Store Local Time?
1. **User Intent**: Preserves what the user actually configured
2. **Portability**: User can change timezones and reschedule
3. **Clarity**: Easy to understand what time was set
4. **Flexibility**: Can recalculate UTC if timezone rules change

### Why Store Timezone?
1. **Conversion**: Backend needs it to convert to UTC
2. **Display**: Frontend can show which timezone was used
3. **Audit**: Track what timezone the user was in when configuring
4. **Recalculation**: Can update EventBridge rules if needed

## Code References

### Frontend
- **Detection**: `dashboard/src/components/ServerSettings.vue`
  ```javascript
  const detectedTimezone = ref(dayjs.tz.guess());
  ```

- **Display**: 
  ```javascript
  const timezoneDisplay = computed(() => {
      const tz = detectedTimezone.value;
      const offset = dayjs().tz(tz).format('Z');
      return `${tz} (UTC${offset})`;
  });
  ```

- **Cron Generation**:
  ```javascript
  function generateCronExpression(time, weekdays) {
      const [hours, minutes] = time.split(':');
      return `${minutes} ${hours} * * ${cronWeekdays}`;
  }
  ```

### Backend
- **Storage**: `layers/ddbHelper/ddbHelper.py`
  ```python
  item = {
      'timezone': config.get('timezone', 'UTC'),
      'stopScheduleExpression': config.get('stopScheduleExpression', ''),
      # ...
  }
  ```

- **Conversion**: `lambdas/ec2ActionWorker/index.py`
  ```python
  def configure_scheduled_shutdown_event(instance_id, cron_expression, timezone='UTC'):
      formatted_schedule = _format_schedule_expression(cron_expression, timezone)
      # Creates EventBridge rule with UTC time
  ```

## Benefits

### User Experience
- ✅ No manual timezone selection required
- ✅ Automatically uses correct local time
- ✅ Clear display of detected timezone
- ✅ Simpler interface with one less dropdown

### Technical
- ✅ Accurate timezone detection via browser API
- ✅ Handles DST automatically with IANA timezones
- ✅ Preserves user intent in database
- ✅ Single source of truth for conversion (backend)

### Maintenance
- ✅ Less user error (can't select wrong timezone)
- ✅ Consistent behavior across users
- ✅ Easy to debug (timezone stored with config)
- ✅ Future-proof for timezone rule changes

## Testing

### Manual Test
1. Open browser developer console
2. Check detected timezone: `Intl.DateTimeFormat().resolvedOptions().timeZone`
3. Open ServerSettings
4. Verify displayed timezone matches
5. Configure schedule
6. Save and verify EventBridge rule has correct UTC time

### Automated Test
Run the cron conversion test suite:
```bash
python3 scripts/test_cron_conversion.py
```

## Migration Notes

### Existing Configurations
- Old configs with stored timezone will continue to work
- Frontend now ignores stored timezone and uses browser-detected one
- When user saves, new browser timezone is stored
- No data migration required

### Backward Compatibility
- Schema unchanged (timezone field already exists)
- Backend logic unchanged (already handles timezone conversion)
- Only frontend behavior changed (auto-detect vs manual select)

## Related Documentation
- `docs/fix-cron-double-conversion.md` - Double conversion bug fix
- `docs/fix-schedule-expression-validation.md` - Original schedule feature
- `scripts/test_cron_conversion.py` - Test suite
- `scripts/README_CRON_TESTS.md` - Test documentation
