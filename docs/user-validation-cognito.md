# User Validation for Server Access

## Overview
This document describes the implementation of user validation when adding users to Minecraft servers. The system now validates that users exist in Amazon Cognito before granting them access to servers.

## Problem Statement
Previously, the system allowed adding any email address to a server without checking if the user had created an account. This could lead to confusion when users were "added" but couldn't actually access the server because they hadn't logged in to create their Cognito profile.

## Solution
The system now validates that users exist in Cognito before adding them to server access groups. If a user hasn't logged in yet, a clear error message instructs the admin to have the user log in first.

## Implementation Details

### Backend Changes

#### 1. AuthHelper Layer (`layers/authHelper/authHelper.py`)
Added a new method `find_user_by_email()` to search for users in Cognito by email address:

```python
def find_user_by_email(self, email):
    """
    Find a user in Cognito by their email address.
    
    Returns:
        dict: User information if found, None if not found
        Format: {'username': str, 'email': str, 'fullName': str, 'sub': str}
    """
```

This method:
- Uses Cognito's `list_users` API with email filter
- Returns user information if found
- Returns `None` if user doesn't exist
- Handles rate limiting and errors gracefully

#### 2. ec2ActionValidator Lambda (`lambdas/ec2ActionValidator/index.py`)
Added a new handler `handle_add_user_to_server()` that:

1. **Validates user exists**: Calls `find_user_by_email()` to check if user has a Cognito profile
2. **Returns specific error codes**:
   - `USER_NOT_FOUND` (404): User hasn't logged in yet
   - `USER_ALREADY_EXISTS` (409): User already has access
   - `GROUP_CREATION_FAILED` (500): Failed to create server group
   - `ADD_USER_FAILED` (500): Failed to add user to group
3. **Creates group if needed**: Ensures the server's Cognito group exists
4. **Adds user to group**: Grants access by adding user to instance-specific group

The handler is called synchronously (not queued) for immediate feedback.

### Frontend Changes

#### UserManagementDialog Component (`dashboard/src/components/UserManagementDialog.vue`)

1. **Enhanced error handling**: Updated `extractUserFriendlyErrorMessage()` to detect and display specific error messages:
   - "User not found. They must log in to the dashboard at least once before being added to a server."
   - "User already has access to this server."
   - Other standard error messages for network, auth, and server errors

2. **User guidance**: Added an info alert above the email input field:
   ```
   Note: Users must log in to the dashboard at least once before they can be added to a server.
   ```

## Error Responses

### USER_NOT_FOUND (404)
```json
{
  "error": "USER_NOT_FOUND",
  "message": "No user found with email user@example.com. The user must log in to the dashboard at least once before they can be added to a server."
}
```

**User sees**: "User not found. They must log in to the dashboard at least once before being added to a server."

### USER_ALREADY_EXISTS (409)
```json
{
  "error": "USER_ALREADY_EXISTS",
  "message": "User user@example.com already has access to this server"
}
```

**User sees**: "User already has access to this server."

### Success (200)
```json
{
  "message": "Successfully added user@example.com to the server",
  "user": {
    "email": "user@example.com",
    "fullName": "John Doe"
  }
}
```

**User sees**: "Successfully added user@example.com to the server" (green success message)

## User Workflow

### Admin Adding a New User
1. Admin opens User Management dialog for a server
2. Admin enters user's email address
3. System validates email format (frontend)
4. Admin clicks "Add User"
5. Backend checks if user exists in Cognito
6. **If user doesn't exist**: Error message displayed with clear instructions
7. **If user exists**: User added to server group, success message displayed
8. User list refreshes to show the newly added user

### New User First-Time Setup
1. User logs in to dashboard using Google OAuth
2. Cognito creates user profile with email, name, and sub (user ID)
3. User can now be added to servers by admins

## Testing

### Manual Testing Steps
1. **Test user not found**:
   - Try adding an email that hasn't logged in
   - Verify error message: "User not found. They must log in..."

2. **Test user already exists**:
   - Add a user successfully
   - Try adding the same user again
   - Verify error message: "User already has access..."

3. **Test successful addition**:
   - Have a user log in once
   - Add that user to a server
   - Verify success message and user appears in list

4. **Test invalid email**:
   - Enter invalid email format
   - Verify frontend validation prevents submission

## Benefits

1. **Clear user guidance**: Admins know exactly what to do when a user can't be added
2. **Prevents confusion**: No "ghost users" that appear added but can't access
3. **Better error messages**: Specific, actionable error messages instead of generic failures
4. **Improved UX**: Proactive info message sets expectations upfront

## Future Enhancements

Potential improvements for future iterations:
- Email invitation system that sends login link to new users
- Bulk user import functionality
- User role management (viewer vs. admin per server)
- Audit log of user additions/removals
