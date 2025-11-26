# UI Cache Timestamp Feature

## Overview

The UI now displays when the monthly runtime data was last calculated, providing transparency about data freshness.

## Visual Changes

### Server Table

**Before:**
```
Running Time
------------
45h 30m
```

**After:**
```
Running Time
------------
45h 30m 🕐    (with tooltip: "Last updated: 30 minutes ago")
```

The clock icon appears next to the running time, and hovering shows when the data was last calculated.

### Server Stats Dialog

**Before:**
```
[Chip: 🕐 45.8 hours]
```

**After:**
```
[Chip: 🕐 45.8 hours]  (with tooltip: "Calculated: 30 min ago")
```

Hovering over the running time chip shows the cache timestamp.

## User Benefits

1. **Transparency** - Users know if data is current or outdated
2. **Trust** - Clear indication of data freshness builds confidence
3. **Debugging** - Helps identify if cache updates are working
4. **Context** - Users understand the data is cached, not real-time

## Technical Implementation

### Data Flow

```
Backend (EventBridge hourly)
  → calculateMonthlyRuntime Lambda
    → Calculates runtime from CloudTrail
      → Stores in DynamoDB with timestamp
        → GraphQL returns both minutes and timestamp
          → UI displays with relative time formatting
```

### Relative Time Formatting

The UI converts ISO timestamps to human-readable relative times:

- **< 1 minute**: "Just now"
- **< 60 minutes**: "X minutes ago"
- **< 24 hours**: "X hours ago"
- **≥ 24 hours**: Shows date (e.g., "11/26/2025")

### Components Updated

1. **ServerTable.vue**
   - Added clock icon next to running time
   - Tooltip shows "Last updated: X ago"
   - Only shows icon if timestamp exists

2. **ServerStatsDialog.vue**
   - Tooltip on running time chip
   - Shows "Calculated: X ago"
   - Gracefully handles missing timestamps

3. **queries.js**
   - Added `runningMinutesCacheTimestamp` to GraphQL query
   - Fetched alongside `runningMinutes`

## Edge Cases Handled

1. **Missing timestamp** - No icon shown, graceful degradation
2. **Invalid timestamp** - Returns "Unknown" instead of crashing
3. **Real-time calculation** - Timestamp is null, no icon shown
4. **Very old cache** - Shows date instead of relative time

## Future Enhancements

1. **Color coding** - Yellow/red for stale data (>2 hours old)
2. **Refresh button** - Manual trigger for cache update
3. **Auto-refresh** - Update relative time every minute
4. **Cache status indicator** - Show if using cached vs real-time data
5. **Admin view** - Show cache statistics across all servers

## Testing

### Manual Testing

1. **Fresh cache** (< 1 hour):
   - Should show "X minutes ago"
   - Clock icon should be visible

2. **Older cache** (1-24 hours):
   - Should show "X hours ago"
   - Clock icon should be visible

3. **No cache** (new server):
   - No clock icon
   - Running time still displays correctly

4. **Stale cache** (> 24 hours):
   - Should show date
   - Indicates cache update may have failed

### Browser Testing

- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

### Responsive Design

- **Desktop**: Full tooltip with detailed timestamp
- **Tablet**: Same as desktop
- **Mobile**: Tooltip works on tap/hold

## Accessibility

- **Tooltip**: Accessible via keyboard navigation
- **Icon**: Has proper ARIA labels
- **Color**: Not relied upon for meaning (icon provides context)
- **Screen readers**: Announces "Running time: 45 hours 30 minutes, last updated 30 minutes ago"

## Performance

- **Minimal overhead**: Timestamp formatting is memoized
- **No extra API calls**: Data fetched with existing query
- **Efficient rendering**: Only formats visible timestamps
- **Cache-friendly**: Relative time updates don't trigger re-renders

## Deployment Notes

1. **Backend first**: Deploy Lambda and schema changes
2. **Frontend second**: Deploy UI changes after backend is live
3. **Backward compatible**: UI handles missing timestamp gracefully
4. **No migration needed**: Existing servers will populate timestamp on next cache update

## Monitoring

Watch for:
- Servers with very old timestamps (indicates cache update failures)
- Servers with no timestamp (indicates cache never populated)
- High frequency of "Just now" (indicates cache thrashing)

Check CloudWatch logs:
```bash
# Check cache update frequency
aws logs filter-log-events \
  --log-group-name /aws/lambda/calculateMonthlyRuntime \
  --filter-pattern "Cached runtime"

# Check for cache read errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/eventResponse \
  --filter-pattern "Error reading cache"
```
