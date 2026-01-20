# Server Creation Integration - Manual Test Guide

This document provides a manual testing guide to verify that the server creation integration works correctly with the existing dashboard functionality.

## Prerequisites

1. Dashboard application is running (`npm run dev`)
2. Backend services are deployed and accessible
3. User has admin privileges
4. AWS credentials are properly configured

## Test Scenarios

### Scenario 1: Basic Server Creation Flow

**Steps:**
1. Open the dashboard in a browser
2. Verify the "Add Server" button is visible in the toolbar (admin users only)
3. Click the "Add Server" button
4. Verify the CreateServerDialog opens
5. Fill in server details:
   - Server Name: `test-integration-server`
   - Instance Type: `t3.small`
   - Shutdown Method: `CPUUtilization`
   - CPU Threshold: `5`
   - Evaluation Period: `30`
6. Click "Create Server"
7. Verify loading state is shown with status updates
8. Wait for server creation to complete
9. Verify success message is displayed
10. Verify dialog closes automatically
11. Verify server list refreshes and shows the new server
12. Verify new server appears with "pending" state initially

**Expected Results:**
- ✅ Server creation dialog works correctly
- ✅ Real-time status updates are displayed during creation
- ✅ Server list automatically refreshes after creation
- ✅ New server appears in the server table
- ✅ Success notification is shown

### Scenario 2: Real-time State Updates

**Steps:**
1. After creating a server in Scenario 1
2. Monitor the server state in the dashboard
3. Verify server state transitions are reflected in real-time:
   - `pending` → `running`
   - Public IP appears when server is running
   - Running time starts counting

**Expected Results:**
- ✅ Server state updates automatically without page refresh
- ✅ Public IP appears when server becomes running
- ✅ All server information is updated in real-time

### Scenario 3: Integration with Existing Features

**Steps:**
1. With the newly created server from Scenario 1
2. Test existing server management features:
   - Click the power button to open PowerControlDialog
   - Verify server can be started/stopped
   - Click the actions menu and select "Configuration"
   - Verify ServerConfigDialog opens with server details
   - Click the actions menu and select "Statistics"
   - Verify ServerStatsDialog opens
   - Test server name editing by clicking on the server name
   - Test IP address copying by clicking the copy button

**Expected Results:**
- ✅ All existing server management features work with newly created servers
- ✅ Power control works correctly
- ✅ Configuration dialog loads server settings
- ✅ Statistics dialog displays server metrics
- ✅ Server name editing works
- ✅ IP address copying works

### Scenario 4: Error Handling

**Steps:**
1. Try to create a server with invalid data:
   - Empty server name
   - Invalid characters in server name
   - Invalid threshold values
2. Verify validation errors are displayed
3. Try to create a server when AWS services are unavailable (if possible)
4. Verify error messages are displayed appropriately

**Expected Results:**
- ✅ Validation errors prevent form submission
- ✅ Clear error messages are displayed
- ✅ Network errors are handled gracefully
- ✅ User is informed of any issues

### Scenario 5: Multiple Server Management

**Steps:**
1. Create multiple servers with different configurations
2. Verify all servers appear in the server list
3. Test server list functionality:
   - Search/filter servers
   - Sort servers by different columns
   - Verify pagination works (if many servers)
4. Test managing multiple servers simultaneously

**Expected Results:**
- ✅ Multiple servers can be created and managed
- ✅ Server list handles multiple servers correctly
- ✅ Search and filtering work with new servers
- ✅ All servers can be managed independently

## Verification Checklist

After completing all scenarios, verify:

- [ ] Server creation dialog opens and closes correctly
- [ ] Form validation works for all input fields
- [ ] Real-time status updates are displayed during creation
- [ ] Server list automatically refreshes after creation
- [ ] New servers appear with correct initial state
- [ ] Real-time state updates work for new servers
- [ ] All existing server management features work with new servers
- [ ] Error handling works correctly
- [ ] Multiple servers can be created and managed
- [ ] No console errors or warnings
- [ ] Performance is acceptable (no significant delays)

## Troubleshooting

### Common Issues

1. **"Add Server" button not visible**
   - Verify user has admin privileges
   - Check browser console for authentication errors

2. **Server creation fails**
   - Check network connectivity
   - Verify AWS credentials and permissions
   - Check browser console for GraphQL errors

3. **Server list doesn't refresh**
   - Check if ec2Discovery GraphQL query is working
   - Verify server store is properly updating
   - Check for subscription connection issues

4. **Real-time updates not working**
   - Verify AppSync subscriptions are connected
   - Check browser console for subscription errors
   - Ensure WebSocket connections are allowed

### Debug Information

To debug issues, check:
- Browser Developer Tools Console
- Network tab for GraphQL requests
- Application tab for local storage/session data
- Vue DevTools for component state

## Success Criteria

The integration is successful if:
1. All test scenarios pass without errors
2. Server creation works end-to-end
3. Real-time updates function correctly
4. Existing features work with new servers
5. Error handling is robust
6. User experience is smooth and intuitive