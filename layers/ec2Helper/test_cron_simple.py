#!/usr/bin/env python3
"""
Simple test for cron expression formatting logic
"""

def strip_leading_zeros(field):
    """Strip leading zeros from cron field values."""
    if not field or field == '*' or field == '?':
        return field
    
    if ',' in field:
        values = field.split(',')
        return ','.join(strip_leading_zeros(v.strip()) for v in values)
    
    if '-' in field and '/' not in field:
        try:
            start, end = field.split('-', 1)
            return f"{strip_leading_zeros(start)}-{strip_leading_zeros(end)}"
        except ValueError:
            return field
    
    if '/' in field:
        try:
            base, step = field.split('/', 1)
            return f"{strip_leading_zeros(base)}/{step.lstrip('0') or '0'}"
        except ValueError:
            return field
    
    if field.isdigit():
        return field.lstrip('0') or '0'
    
    return field

def convert_day_of_week(day_of_week):
    """Convert day-of-week from standard cron (0-6) to EventBridge (1-7)."""
    if day_of_week == '*':
        return '*'
    
    if ',' in day_of_week:
        values = day_of_week.split(',')
        converted_values = []
        for val in values:
            if val.strip() == '0':
                converted_values.append('7')
            elif val.strip().isdigit() and 1 <= int(val.strip()) <= 6:
                converted_values.append(val.strip())
        return ','.join(converted_values)
    
    if day_of_week == '0':
        return '7'
    elif day_of_week.isdigit() and 1 <= int(day_of_week) <= 6:
        return day_of_week
    
    return None

def format_schedule_expression(cron_expression):
    """Format cron expression for EventBridge."""
    if not cron_expression:
        return None
    
    cron_expression = cron_expression.strip()
    
    # If already in EventBridge format, extract and clean it
    if cron_expression.startswith('cron(') and cron_expression.endswith(')'):
        cron_content = cron_expression[5:-1]
        fields = cron_content.split()
        if len(fields) == 6:
            minute, hour, day, month, day_of_week, year = fields
            minute = strip_leading_zeros(minute)
            hour = strip_leading_zeros(hour)
            day = strip_leading_zeros(day)
            month = strip_leading_zeros(month)
            return f"cron({minute} {hour} {day} {month} {day_of_week} {year})"
        return cron_expression
    
    # Handle standard 5-field cron expression
    fields = cron_expression.split()
    if len(fields) == 5:
        minute, hour, day, month, day_of_week = fields
        
        # Strip leading zeros
        minute = strip_leading_zeros(minute)
        hour = strip_leading_zeros(hour)
        day = strip_leading_zeros(day)
        month = strip_leading_zeros(month)
        
        # Convert day-of-week
        converted_dow = convert_day_of_week(day_of_week)
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
    ("30 14 * * 1,2,3", "cron(30 14 ? * 1,2,3 *)"),
    ("0 9 * * 0", "cron(0 9 ? * 7 *)"),
    ("00 03 * * 1,2,3,4,5,6,0", "cron(0 3 ? * * *)"),
    ("30 16 * * 1,2,3,4,5,6,0", "cron(30 16 ? * * *)"),
    ("cron(00 14 * * 1,2,3 *)", "cron(0 14 * * 1,2,3 *)"),
]

print("Testing cron expression formatting:")
print("=" * 80)

for input_expr, expected in test_cases:
    result = format_schedule_expression(input_expr)
    status = "✅ PASS" if result == expected else "❌ FAIL"
    print(f"{status}")
    print(f"  Input:    '{input_expr}'")
    print(f"  Expected: '{expected}'")
    print(f"  Got:      '{result}'")
    print()

print("=" * 80)
