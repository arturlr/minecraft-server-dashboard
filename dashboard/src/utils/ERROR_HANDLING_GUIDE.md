# Error Handling Implementation Guide

## Overview

This document describes the comprehensive error handling and notification system implemented across the Minecraft Server Dashboard application.

## Components

### 1. Error Handler Utility (`utils/errorHandler.js`)

A centralized utility module for parsing and handling errors consistently across the application.

#### Functions:

- **`parseGraphQLError(error)`**: Extracts user-friendly error messages from GraphQL and network errors
  - Handles GraphQL error arrays
  - Identifies common network errors (timeout, unauthorized, forbidden, not found)
  - Returns user-friendly messages

- **`retryOperation(operation, maxRetries, baseDelay)`**: Implements retry logic with exponential backoff
  - Default: 2 retries with 1000ms base delay
  - Skips retry for authorization errors (401, 403)
  - Uses exponential backoff (delay doubles each attempt)

- **`isRetryableError(error)`**: Determines if an error should trigger a retry
  - Checks for network-related errors
  - Returns boolean

- **`createErrorNotification(error, defaultMessage)`**: Creates standardized error notification objects
  - Returns object with text, color, and timeout properties

- **`createSuccessNotification(message)`**: Creates standardized success notification objects

### 2. Error Boundary Component (`components/ErrorBoundary.vue`)

A Vue component that catches errors from child components and displays a fallback UI.

#### Features:
- Catches component-level errors using `onErrorCaptured`
- Displays user-friendly error alert
- Provides "Try Again" and "Reload Page" buttons
- Emits error events to parent components
- Prevents error propagation

#### Usage:
```vue
<ErrorBoundary @error="handleComponentError">
  <YourComponent />
</ErrorBoundary>
```

## Implementation Details

### HomeView.vue

**Enhanced Error Handling:**
- Server list loading with error notifications
- GraphQL subscription error handling with automatic reconnection
- IAM role fix operations with retry logic
- Clipboard operations with permission error handling
- Component error boundary wrapping for all major sections

**Subscription Reconnection:**
- Automatically attempts to reconnect after subscription errors
- 5-second delay before reconnection attempt
- Displays user notification on connection failure

### PowerControlDialog.vue

**Enhanced Error Handling:**
- All power actions (start/stop/restart) use retry logic
- IAM role fix operations with retry logic
- Parsed error messages displayed to users
- Loading states during operations

### ServerStatsDialog.vue

**Enhanced Error Handling:**
- Metrics subscription with automatic reconnection
- Exponential backoff for reconnection attempts (max 3 attempts)
- Error alert displayed in dialog
- Manual retry button after max attempts reached
- Proper cleanup on dialog close

### ServerSettings.vue

**Enhanced Error Handling:**
- Configuration loading with retry logic
- Configuration saving with retry logic
- Validation error notifications
- Success/error snackbars with appropriate colors
- Network error handling

### Server Store (`stores/server.js`)

**Enhanced Error Handling:**
- All GraphQL operations parse errors using `parseGraphQLError`
- Enhanced error objects with original error preserved
- Consistent error logging
- User-friendly error messages

## Error Types Handled

### 1. Network Errors
- Connection failures
- Timeouts
- DNS resolution failures
- Automatic retry with exponential backoff

### 2. GraphQL Errors
- Query/mutation failures
- Subscription errors
- Parsed into user-friendly messages

### 3. Authorization Errors
- 401 Unauthorized
- 403 Forbidden
- No retry attempted (requires re-authentication)

### 4. Component Errors
- Runtime errors in Vue components
- Caught by ErrorBoundary
- Fallback UI displayed

### 5. Validation Errors
- Form validation failures
- Displayed inline and via snackbar

## Notification System

### Snackbar Configuration

**Success Notifications:**
- Color: `success` (green)
- Timeout: 3500ms
- Used for: Successful operations

**Error Notifications:**
- Color: `error` (red)
- Timeout: 5000ms (longer than success)
- Used for: Failed operations, network errors

**Warning Notifications:**
- Color: `warning` (orange)
- Timeout: 3500ms
- Used for: Validation errors, non-critical issues

### Notification Placement
- Position: Left, centered
- Dismissible: Yes (close button provided)
- Outlined style for better visibility

## Best Practices

### 1. Always Use Try-Catch
```javascript
try {
  await someOperation();
} catch (error) {
  const errorMessage = parseGraphQLError(error);
  handleActionComplete(errorMessage, false);
}
```

### 2. Use Retry Logic for Network Operations
```javascript
const result = await retryOperation(async () => {
  return await client.graphql({ query, variables });
});
```

### 3. Provide User Feedback
```javascript
// Success
handleActionComplete('Operation completed successfully', true);

// Error
handleActionComplete(parseGraphQLError(error), false);
```

### 4. Log Errors for Debugging
```javascript
console.error('Operation failed:', error);
const errorMessage = parseGraphQLError(error);
console.error('Parsed error:', errorMessage);
```

### 5. Wrap Critical Components
```vue
<ErrorBoundary @error="handleComponentError">
  <CriticalComponent />
</ErrorBoundary>
```

## Testing Error Handling

### Manual Testing Scenarios

1. **Network Disconnection**
   - Disconnect network
   - Attempt server operations
   - Verify retry logic and error messages

2. **Invalid Server ID**
   - Use non-existent server ID
   - Verify error message displayed

3. **Subscription Failures**
   - Simulate subscription error
   - Verify reconnection attempts

4. **Component Errors**
   - Trigger component error
   - Verify ErrorBoundary catches and displays fallback

5. **Validation Errors**
   - Submit invalid form data
   - Verify validation messages

## Future Enhancements

1. **Error Reporting Service**
   - Integrate with error tracking service (e.g., Sentry)
   - Automatic error reporting for production

2. **Offline Mode**
   - Detect offline state
   - Queue operations for when connection restored

3. **Enhanced Retry Logic**
   - Configurable retry strategies per operation
   - Circuit breaker pattern for repeated failures

4. **User Error Feedback**
   - Allow users to report errors
   - Include context and reproduction steps

## Maintenance

### Adding New Error Handlers

1. Import error handler utilities:
```javascript
import { parseGraphQLError, retryOperation } from '../utils/errorHandler';
```

2. Wrap GraphQL operations:
```javascript
try {
  const result = await retryOperation(async () => {
    return await client.graphql({ query, variables });
  });
  // Handle success
} catch (error) {
  const errorMessage = parseGraphQLError(error);
  // Handle error
}
```

3. Display notifications:
```javascript
handleActionComplete(errorMessage, false);
```

### Updating Error Messages

Edit `parseGraphQLError` function in `utils/errorHandler.js` to add new error patterns or improve existing messages.

## Summary

The error handling system provides:
- ✅ Consistent error parsing and display
- ✅ Automatic retry with exponential backoff
- ✅ Component-level error boundaries
- ✅ User-friendly error messages
- ✅ Subscription reconnection logic
- ✅ Comprehensive logging for debugging
- ✅ Success and error notifications
- ✅ Graceful degradation on failures
