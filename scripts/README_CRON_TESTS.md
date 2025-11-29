# Cron Expression Conversion Tests

## Overview
This test suite validates the cron expression conversion logic that transforms frontend 5-field standard cron expressions into EventBridge 6-field format.

## Test Script
`test_cron_conversion.py` - Comprehensive test suite for cron expression conversion

## Running Tests
```bash
# From project root
python3 scripts/test_cron_conversion.py

# Make executable and run directly
chmod +x scripts/test_cron_conversion.py
./scripts/test_cron_conversion.py
```

## What It Tests

### 1. Basic Conversions
- Standard 5-field cron to 6-field EventBridge format
- Day-of-week conversion (0-6 → 1-7, where Sunday: 0→7)
- Day-of-month replacement with '?' when day-of-week is specified

### 2. Leading Zero Stripping
- Removes leading zeros from minutes, hours, days, months
- Handles comma-separated lists (e.g., `01,02,03` → `1,2,3`)
- Preserves single zero values

### 3. Timezone Conversions
- Converts local time to UTC based on timezone
- Tests multiple timezones (PST, EST, JST)
- Uses fixed date (Jan 15) to avoid DST complications

### 4. Edge Cases
- All days specified optimization (`0,1,2,3,4,5,6` → `*`)
- Already formatted EventBridge expressions (pass-through)
- Empty expressions (returns None)
- Invalid field counts (returns None)

### 5. Frontend Use Cases
- Quick schedule presets (weekday evenings, weekends, business hours)
- Real-world timezone scenarios
- Common scheduling patterns

## Test Cases

| Test | Input | Timezone | Expected Output |
|------|-------|----------|-----------------|
| Weekday evenings | `30 14 * * 1,2,3` | UTC | `cron(30 14 ? * 1,2,3 *)` |
| Weekend mornings | `00 10 * * 6,0` | UTC | `cron(0 10 ? * 6,7 *)` |
| PST to UTC | `00 14 * * 1,2,3,4,5` | America/Los_Angeles | `cron(0 22 ? * 1,2,3,4,5 *)` |
| Leading zeros | `05 08 * * 1` | UTC | `cron(5 8 ? * 1 *)` |
| All days | `30 15 * * 0,1,2,3,4,5,6` | UTC | `cron(30 15 ? * * *)` |

## Conversion Rules

### Format Transformation
```
Frontend:   minute hour day month day_of_week
            30     14   *   *     1,2,3

EventBridge: minute hour day month day_of_week year
             30     14   ?   *     1,2,3       *
```

### Day-of-Week Mapping
```
Standard Cron:  0 (Sun), 1 (Mon), 2 (Tue), 3 (Wed), 4 (Thu), 5 (Fri), 6 (Sat)
EventBridge:    7 (Sun), 1 (Mon), 2 (Tue), 3 (Wed), 4 (Thu), 5 (Fri), 6 (Sat)
```

### EventBridge Rules
- When day-of-week is specified, day-of-month must be `?`
- When day-of-month is specified, day-of-week must be `?`
- Year field is always `*` for recurring schedules
- Leading zeros must be stripped from all numeric fields

## Expected Output
```
================================================================================
CRON EXPRESSION CONVERSION TEST SUITE
================================================================================

Test 1: Weekday evenings (Mon-Wed 2:30 PM)
  Description: Standard weekday schedule
  Input:       30 14 * * 1,2,3
  Timezone:    UTC
  Expected:    cron(30 14 ? * 1,2,3 *)
  Result:      cron(30 14 ? * 1,2,3 *)
  ✓ PASSED

...

================================================================================
SUMMARY: 16 passed, 0 failed out of 16 tests
================================================================================
```

## Adding New Tests
To add a new test case, append to the `test_cases` list in `test_cron_conversion.py`:

```python
{
    'name': 'Test name',
    'input': '30 14 * * 1,2,3',
    'timezone': 'UTC',
    'expected': 'cron(30 14 ? * 1,2,3 *)',
    'description': 'What this test validates'
}
```

## Dependencies
- Python 3.6+
- `pytz` library (for timezone conversions)

Install dependencies:
```bash
pip install pytz
```

## Related Files
- `lambdas/serverActionProcessor/index.py` - Production conversion logic
- `dashboard/src/components/ServerSettings.vue` - Frontend cron input
- `docs/fix-schedule-expression-validation.md` - Implementation documentation
