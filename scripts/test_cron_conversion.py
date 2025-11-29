#!/usr/bin/env python3
"""
Test script for cron expression conversion from frontend format to EventBridge format.

This script validates the conversion logic that transforms:
- 5-field standard cron expressions to 6-field EventBridge format
- Day-of-week conversion (0-6 to 1-7, where 0/7 = Sunday)
- Leading zero stripping
- Timezone conversion to UTC
- Validation of edge cases
"""

import sys
from datetime import datetime
import pytz


def _strip_leading_zeros(field):
    """Strip leading zeros from numeric fields."""
    if not field or field == '*' or field == '?':
        return field
    
    if ',' in field:
        values = field.split(',')
        return ','.join([v.lstrip('0') or '0' for v in values])
    
    if '-' in field:
        start, end = field.split('-')
        start = start.lstrip('0') or '0'
        end = end.lstrip('0') or '0'
        return f"{start}-{end}"
    
    if '/' in field:
        base, step = field.split('/')
        base = base.lstrip('0') or '0' if base != '*' else '*'
        step = step.lstrip('0') or '0'
        return f"{base}/{step}"
    
    if field.isdigit():
        return field.lstrip('0') or '0'
    
    return field


def _convert_day_of_week(day_of_week):
    """Convert day-of-week from standard cron (0-6) to EventBridge (1-7)."""
    if day_of_week == '*':
        return '*'
    
    if ',' in day_of_week:
        values = day_of_week.split(',')
        converted_values = []
        for val in values:
            val = val.strip().lstrip('0') or '0'  # Strip leading zeros
            if val == '0':
                converted_values.append('7')
            elif val.isdigit() and 1 <= int(val) <= 6:
                converted_values.append(val)
        return ','.join(converted_values)
    
    # Strip leading zeros for single values
    day_of_week = day_of_week.lstrip('0') or '0'
    
    if day_of_week == '0':
        return '7'
    elif day_of_week.isdigit() and 1 <= int(day_of_week) <= 6:
        return day_of_week
    
    return None


def _convert_timezone_to_utc(hour, minute, timezone):
    """Convert local time to UTC based on timezone."""
    if not timezone or timezone == 'UTC':
        return hour, minute
    
    try:
        # Create a datetime in the specified timezone
        tz = pytz.timezone(timezone)
        # Use a fixed date to get consistent offset (mid-January to avoid most DST transitions)
        local_time = tz.localize(datetime(2024, 1, 15, int(hour), int(minute)))
        
        # Convert to UTC
        utc_time = local_time.astimezone(pytz.UTC)
        
        return str(utc_time.hour), str(utc_time.minute)
    except Exception as e:
        print(f"Error converting timezone {timezone} to UTC: {e}")
        # Return original values if conversion fails
        return hour, minute


def _format_schedule_expression(cron_expression, timezone='UTC'):
    """Format cron expression for EventBridge, converting from local timezone to UTC."""
    if not cron_expression:
        return None
    
    cron_expression = cron_expression.strip()
    
    # If already in EventBridge format, extract and clean it
    if cron_expression.startswith('cron(') and cron_expression.endswith(')'):
        cron_content = cron_expression[5:-1]
        fields = cron_content.split()
        if len(fields) == 6:
            minute, hour, day, month, day_of_week, year = fields
            
            # Convert timezone if not UTC
            if timezone and timezone != 'UTC':
                hour, minute = _convert_timezone_to_utc(hour, minute, timezone)
            
            minute = _strip_leading_zeros(minute)
            hour = _strip_leading_zeros(hour)
            day = _strip_leading_zeros(day)
            month = _strip_leading_zeros(month)
            return f"cron({minute} {hour} {day} {month} {day_of_week} {year})"
        return cron_expression
    
    # Handle standard 5-field cron expression
    fields = cron_expression.split()
    if len(fields) == 5:
        minute, hour, day, month, day_of_week = fields
        
        # Convert timezone to UTC if needed
        if timezone and timezone != 'UTC':
            hour, minute = _convert_timezone_to_utc(hour, minute, timezone)
        
        # Strip leading zeros
        minute = _strip_leading_zeros(minute)
        hour = _strip_leading_zeros(hour)
        day = _strip_leading_zeros(day)
        month = _strip_leading_zeros(month)
        
        # Convert day-of-week
        converted_dow = _convert_day_of_week(day_of_week)
        if not converted_dow:
            return None
        
        # Optimize: if all days are specified, use '*'
        if ',' in converted_dow:
            dow_values = set(converted_dow.split(','))
            if dow_values == {'1', '2', '3', '4', '5', '6', '7'}:
                converted_dow = '*'
        
        # EventBridge rule: when day-of-week is specified, day-of-month must be '?'
        if converted_dow != '?':
            day = '?'
        
        return f"cron({minute} {hour} {day} {month} {converted_dow} *)"
    
    return None


# Test cases
test_cases = [
    # Basic conversions
    {
        'name': 'Weekday evenings (Mon-Wed 2:30 PM)',
        'input': '30 14 * * 1,2,3',
        'timezone': 'UTC',
        'expected': 'cron(30 14 ? * 1,2,3 *)',
        'description': 'Standard weekday schedule'
    },
    {
        'name': 'Weekend mornings (Sat-Sun 10:00 AM)',
        'input': '00 10 * * 6,0',
        'timezone': 'UTC',
        'expected': 'cron(0 10 ? * 6,7 *)',
        'description': 'Weekend schedule with Sunday as 0'
    },
    {
        'name': 'Every day at midnight',
        'input': '00 00 * * *',
        'timezone': 'UTC',
        'expected': 'cron(0 0 ? * * *)',
        'description': 'Daily schedule with all days'
    },
    {
        'name': 'Business hours start (Mon-Fri 9:00 AM)',
        'input': '00 09 * * 1,2,3,4,5',
        'timezone': 'UTC',
        'expected': 'cron(0 9 ? * 1,2,3,4,5 *)',
        'description': 'Weekday business hours'
    },
    
    # Leading zero stripping
    {
        'name': 'Leading zeros in time',
        'input': '05 08 * * 1',
        'timezone': 'UTC',
        'expected': 'cron(5 8 ? * 1 *)',
        'description': 'Strip leading zeros from minute and hour'
    },
    {
        'name': 'Leading zeros in day-of-week list',
        'input': '00 12 * * 01,02,03',
        'timezone': 'UTC',
        'expected': 'cron(0 12 ? * 1,2,3 *)',
        'description': 'Strip leading zeros from day-of-week values'
    },
    
    # Timezone conversions
    {
        'name': 'PST to UTC (2:00 PM PST = 10:00 PM UTC)',
        'input': '00 14 * * 1,2,3,4,5',
        'timezone': 'America/Los_Angeles',
        'expected': 'cron(0 22 ? * 1,2,3,4,5 *)',
        'description': 'Convert Pacific time to UTC'
    },
    {
        'name': 'EST to UTC (9:00 AM EST = 2:00 PM UTC)',
        'input': '00 09 * * 1,2,3,4,5',
        'timezone': 'America/New_York',
        'expected': 'cron(0 14 ? * 1,2,3,4,5 *)',
        'description': 'Convert Eastern time to UTC'
    },
    {
        'name': 'JST to UTC (8:00 PM JST = 11:00 AM UTC)',
        'input': '00 20 * * 6,0',
        'timezone': 'Asia/Tokyo',
        'expected': 'cron(0 11 ? * 6,7 *)',
        'description': 'Convert Japan time to UTC'
    },
    
    # Edge cases
    {
        'name': 'All days specified (should optimize to *)',
        'input': '30 15 * * 0,1,2,3,4,5,6',
        'timezone': 'UTC',
        'expected': 'cron(30 15 ? * * *)',
        'description': 'All days specified should convert to wildcard'
    },
    {
        'name': 'Single day (Sunday as 0)',
        'input': '00 12 * * 0',
        'timezone': 'UTC',
        'expected': 'cron(0 12 ? * 7 *)',
        'description': 'Sunday (0) converts to 7'
    },
    {
        'name': 'Already formatted EventBridge expression',
        'input': 'cron(30 14 ? * 1,2,3 *)',
        'timezone': 'UTC',
        'expected': 'cron(30 14 ? * 1,2,3 *)',
        'description': 'Already formatted expression passes through'
    },
    
    # Frontend typical use cases
    {
        'name': 'Quick preset: Weekday evenings',
        'input': '00 18 * * 1,2,3,4,5',
        'timezone': 'America/New_York',
        'expected': 'cron(0 23 ? * 1,2,3,4,5 *)',
        'description': 'Weekday evenings 6 PM EST = 11 PM UTC'
    },
    {
        'name': 'Quick preset: Weekend all day',
        'input': '00 08 * * 6,0',
        'timezone': 'America/Los_Angeles',
        'expected': 'cron(0 16 ? * 6,7 *)',
        'description': 'Weekend 8 AM PST = 4 PM UTC'
    },
    {
        'name': 'Bug fix: 4:00 PM PST Mon-Fri',
        'input': '00 16 * * 1,2,3,4,5',
        'timezone': 'America/Los_Angeles',
        'expected': 'cron(0 0 ? * 1,2,3,4,5 *)',
        'description': '4:00 PM PST = 12:00 AM UTC next day (midnight)'
    },
    
    # Invalid cases
    {
        'name': 'Empty expression',
        'input': '',
        'timezone': 'UTC',
        'expected': None,
        'description': 'Empty string should return None'
    },
    {
        'name': 'Invalid field count',
        'input': '30 14 * *',
        'timezone': 'UTC',
        'expected': None,
        'description': 'Too few fields should return None'
    },
]


def run_tests():
    """Run all test cases and report results."""
    print("=" * 80)
    print("CRON EXPRESSION CONVERSION TEST SUITE")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"  Description: {test['description']}")
        print(f"  Input:       {test['input']}")
        print(f"  Timezone:    {test['timezone']}")
        print(f"  Expected:    {test['expected']}")
        
        result = _format_schedule_expression(test['input'], test['timezone'])
        print(f"  Result:      {result}")
        
        if result == test['expected']:
            print("  ✓ PASSED")
            passed += 1
        else:
            print("  ✗ FAILED")
            failed += 1
        
        print()
    
    print("=" * 80)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
