# Fix Server Settings Data Loading Issue

## Problem
The ServerSettings component was not displaying EC2 tag information correctly due to several issues:

1. **Outdated GraphQL Queries**: The queries didn't match the updated schema
2. **Missing Fields**: New fields like `stopScheduleExpression`, `startScheduleExpression` were missing
3. **Data Type Mismatches**: Component expected objects but received strings
4. **Separate User Data**: User data should come from a separate query, not server config

## Files Fixed

### 1. GraphQL Queries (`dashboard/src/graphql/queries.js`)
**Fixed Issues:**
- Updated `getServerConfig` query to include all new fields
- Updated `ec2Discovery` query to include validation fields
- Fixed `getServerUsers` query parameter name

**Changes:**
```javascript
// Added missing fields to getServerConfig
export const getServerConfig = /* GraphQL */ `
query GetServerConfig($id: String!) {
  getServerConfig(id: $id) {
    id
    runCommand
    workDir
    shutdownMethod
    stopScheduleExpression
    startScheduleExpression
    alarmThreshold
    alarmEvaluationPeriod
  }
}
`;

// Added validation fields to ec2Discovery
configStatus
configValid
configWarnings
configErrors
autoConfigured
```

### 2. GraphQL Mutations (`dashboard/src/graphql/mutations.js`)
**Fixed Issues:**
- Updated `putServerConfig` mutation to include new schedule fields

**Changes:**
```javascript
export const putServerConfig = /* GraphQL */ `
  mutation PutServerConfig($input: ServerConfigInput!) {
    putServerConfig(input: $input) {
      id
      runCommand
      workDir
      shutdownMethod
      stopScheduleExpression
      startScheduleExpression
      alarmThreshold
      alarmEvaluationPeriod
    }
  }
`;
```

### 3. Server Store (`dashboard/src/stores/server.js`)
**Fixed Issues:**
- Added `getServerUsers` method for separate user data loading

**Changes:**
```javascript
async getServerUsers(instanceId) {
    // Implementation to fetch server users separately
}
```

### 4. ServerSettings Component (`dashboard/src/components/ServerSettings.vue`)
**Fixed Issues:**
- Fixed data type handling for shutdown methods
- Separated user data loading from config loading
- Fixed form submission and validation
- Improved error handling

**Key Changes:**
- `selectedShutdownMethod` now properly handles object/string conversion
- `getServerUsers()` function added for separate user data loading
- Improved `onSubmit()` function with better error handling
- Fixed computed properties to use correct data sources

## Testing

### Debug Component
Created `ServerConfigDebug.vue` component to help test data loading:
- Test `getServerConfig` functionality
- Test `getServerUsers` functionality
- Display raw data for debugging

### Usage
1. Import the debug component in your view
2. Click "Test Get Config" to verify server configuration loading
3. Click "Test Get Users" to verify user data loading
4. Check console logs for detailed information

## Deployment Steps

1. **Update GraphQL Schema** (if needed):
   ```bash
   cd cfn
   sam build
   sam deploy
   ```

2. **Clear Browser Cache**: Clear browser cache to ensure new GraphQL queries are used

3. **Test Functionality**:
   - Open ServerSettings dialog
   - Verify all fields are populated correctly
   - Test form submission
   - Check user management functionality

## Expected Behavior After Fix

### Server Configuration Dialog
- ✅ Shutdown method dropdown shows correct selection
- ✅ Threshold and evaluation period fields populated
- ✅ Run command and working directory fields populated
- ✅ Schedule configuration works for schedule-based shutdown
- ✅ Form validation works correctly
- ✅ Save functionality works without errors

### User Management Dialog
- ✅ Current members list displays correctly
- ✅ Member count shows accurate number
- ✅ Add user functionality works
- ✅ User data loads separately from config data

## Common Issues and Solutions

### Issue: "Cannot read property of undefined"
**Solution**: Check that `selectedServerId` is set before calling `getServerConfig()`

### Issue: Dropdown shows empty or wrong values
**Solution**: Verify GraphQL query returns all expected fields and data types match

### Issue: Form submission fails
**Solution**: Check that all required fields are properly formatted before sending to backend

### Issue: Users not loading
**Solution**: Ensure `getServerUsers` is called separately and handles empty responses gracefully

## Verification Checklist

- [ ] Server configuration dialog opens without errors
- [ ] All form fields are populated with correct values
- [ ] Shutdown method dropdown shows correct selection
- [ ] Schedule configuration works (if applicable)
- [ ] Form validation prevents invalid submissions
- [ ] Save button updates configuration successfully
- [ ] User management dialog shows current members
- [ ] Add user functionality works
- [ ] No console errors during normal operation