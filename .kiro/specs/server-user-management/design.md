# Design Document

## Overview

This feature adds user management capabilities to the ServerTable component, allowing administrators to view and manage user access permissions for individual Minecraft servers. The implementation will consist of a new action button in the ServerActionsMenu component and a new UserManagementDialog component that handles the user interface for listing and adding users.

The feature leverages existing GraphQL infrastructure (`getServerUsers` query and `addUserToServer` mutation) and follows established patterns in the codebase for dialog-based interactions.

## Architecture

### Component Structure

```
ServerTable.vue (existing)
  └── ServerActionsMenu.vue (modified)
        └── UserManagementDialog.vue (new)
```

### Data Flow

1. **User clicks user management button** → Event emitted from ServerActionsMenu
2. **ServerTable receives event** → Opens UserManagementDialog with server ID
3. **Dialog opens** → Fetches users via getServerUsers GraphQL query
4. **User adds new user** → Calls addUserToServer GraphQL mutation
5. **Mutation succeeds** → Refreshes user list and displays success message

### Integration Points

- **GraphQL API**: Uses existing AppSync queries and mutations
- **Amplify SDK**: Handles authentication and GraphQL requests
- **Vuetify Components**: Uses v-dialog, v-list, v-text-field, v-btn for UI
- **ServerActionsMenu**: Extended to include user management button
- **ServerTable**: Manages dialog state and passes server context

## Components and Interfaces

### 1. ServerActionsMenu.vue (Modified)

**Purpose**: Add user management action button to existing menu

**Props**:
- `serverId` (String, required): EC2 instance ID

**New Emit**:
- `open-users`: Emitted when user management button is clicked

**Changes**:
- Add new v-tooltip with v-btn for user management
- Use `mdi-account-multiple` icon
- Emit `open-users` event on click
- User management functionality relies on Cognito groups, not IAM or server state

### 2. UserManagementDialog.vue (New Component)

**Purpose**: Display and manage users with access to a server

**Props**:
```javascript
{
  modelValue: Boolean,      // Dialog visibility (v-model)
  serverId: String,         // EC2 instance ID
  serverName: String        // Display name for the server
}
```

**Emits**:
```javascript
{
  'update:modelValue': Boolean  // Two-way binding for dialog visibility
}
```

**Data**:
```javascript
{
  users: [],                    // Array of user objects
  loading: false,               // Loading state for initial fetch
  addingUser: false,            // Loading state for add operation
  newUserEmail: '',             // Email input value
  errorMessage: '',             // Error message display
  successMessage: '',           // Success message display
  emailRules: []                // Validation rules for email input
}
```

**Methods**:
```javascript
async fetchUsers()            // Fetch users from GraphQL
async addUser()               // Add user via GraphQL mutation
validateEmail(email)          // Email format validation
closeDialog()                 // Close dialog and reset state
```

### 3. ServerTable.vue (Modified)

**Purpose**: Manage UserManagementDialog state

**New Data**:
```javascript
{
  userManagementDialog: false,     // Dialog visibility
  selectedServerId: null,          // Currently selected server ID
  selectedServerName: null         // Currently selected server name
}
```

**New Methods**:
```javascript
openUserManagement(serverId)     // Open dialog for specific server
```

**New Event Handlers**:
- Handle `open-users` event from ServerActionsMenu
- Pass server context to UserManagementDialog

## Data Models

### User Object (from GraphQL)

```javascript
{
  id: String,           // Cognito user sub (unique identifier)
  email: String,        // User's email address (AWSEmail type)
  fullName: String      // User's full name (given_name + family_name)
}
```

### GraphQL Query Response (getServerUsers)

```javascript
{
  data: {
    getServerUsers: [
      {
        id: "cognito-sub-uuid",
        email: "user@example.com",
        fullName: "John Doe"
      }
    ]
  }
}
```

### GraphQL Mutation Input (addUserToServer)

```javascript
{
  instanceId: String,    // EC2 instance ID
  userEmail: String      // Email address of user to add
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: User display completeness
*For any* user object in the user list, the rendered output should contain both the user's email address and full name.
**Validates: Requirements 2.1**

### Property 2: Email validation correctness
*For any* string input, the email validation function should correctly identify valid email formats according to RFC 5322 standards and reject invalid formats.
**Validates: Requirements 3.2**

### Property 3: Error message extraction
*For any* GraphQL error response, the system should extract and return a non-empty, human-readable error message.
**Validates: Requirements 5.4**

## Error Handling

### GraphQL Query Errors
- **Network failures**: Display "Unable to connect to server. Please check your connection and try again."
- **Authentication errors**: Display "Session expired. Please log in again."
- **Server errors**: Extract error message from GraphQL response or display generic "An error occurred while loading users."
- **Timeout errors**: Display "Request timed out. Please try again."

### GraphQL Mutation Errors
- **User already exists**: Display "User already has access to this server."
- **Invalid email**: Display "Please enter a valid email address."
- **User not found**: Display "No user found with that email address."
- **Permission denied**: Display "You don't have permission to add users to this server."
- **Network failures**: Display "Unable to add user. Please check your connection and try again."

### Input Validation Errors
- **Empty email**: Display "Email address is required."
- **Invalid format**: Display "Please enter a valid email address."
- **Whitespace only**: Treat as empty and display "Email address is required."

### Component Error Boundaries
- Wrap GraphQL operations in try-catch blocks
- Use Vue's error handling for component lifecycle errors
- Provide user-friendly error messages with actionable next steps
- Include retry mechanisms for transient failures

## Testing Strategy

### Unit Testing

**Framework**: Vitest (existing test framework in the project)

**Test Coverage**:

1. **UserManagementDialog Component Tests**
   - Verify dialog opens and closes correctly
   - Verify users are fetched on dialog open
   - Verify loading state is displayed during fetch
   - Verify error state is displayed on fetch failure
   - Verify empty state is displayed when no users exist
   - Verify add user form submission with valid email
   - Verify add user form validation prevents empty submission
   - Verify success message after successful user addition
   - Verify error message after failed user addition
   - Verify user list refreshes after successful addition

2. **ServerActionsMenu Component Tests**
   - Verify user management button is rendered
   - Verify correct icon is used (mdi-account-multiple)
   - Verify click event emits 'open-users' event

3. **ServerTable Component Tests**
   - Verify dialog state management
   - Verify correct server context is passed to dialog
   - Verify event handling from ServerActionsMenu

4. **Email Validation Tests**
   - Test valid email formats (standard, with plus sign, with subdomain)
   - Test invalid email formats (missing @, missing domain, special characters)
   - Test edge cases (empty string, whitespace only, very long emails)

5. **Error Message Extraction Tests**
   - Test extraction from various GraphQL error response formats
   - Test fallback to generic message when extraction fails
   - Test handling of nested error structures

### Property-Based Testing

**Framework**: fast-check (JavaScript property-based testing library)

**Configuration**: Each property test should run a minimum of 100 iterations to ensure comprehensive coverage across the input space.

**Test Tagging**: Each property-based test must include a comment explicitly referencing the correctness property from this design document using the format: `// Feature: server-user-management, Property {number}: {property_text}`

**Property Tests**:

1. **Property 1: User display completeness**
   - Generate random user objects with varying email and fullName values
   - Render the user list component
   - Verify that for each user, both email and fullName appear in the rendered output
   - **Tag**: `// Feature: server-user-management, Property 1: User display completeness`

2. **Property 2: Email validation correctness**
   - Generate random strings including valid emails, invalid emails, and edge cases
   - Run each through the email validation function
   - Verify that valid emails pass and invalid emails fail according to RFC 5322
   - **Tag**: `// Feature: server-user-management, Property 2: Email validation correctness`

3. **Property 3: Error message extraction**
   - Generate random GraphQL error response structures
   - Extract error messages using the error handling function
   - Verify that the extracted message is non-empty and human-readable
   - **Tag**: `// Feature: server-user-management, Property 3: Error message extraction`

### Integration Testing

While not required for core functionality, integration tests can verify:
- End-to-end flow from button click to user addition
- GraphQL query and mutation integration with mocked AppSync
- Authentication token handling through Amplify SDK

### Test Utilities

Create reusable test utilities:
- Mock GraphQL responses for getServerUsers and addUserToServer
- Mock Amplify API client
- Factory functions for generating test user objects
- Helper functions for mounting Vue components with Vuetify

## Implementation Notes

### Vue 3 Composition API
- Use `<script setup>` syntax for cleaner component code
- Use `ref` and `reactive` for reactive state management
- Use `computed` for derived state
- Use `watch` for side effects when needed

### Vuetify Components
- `v-dialog`: Main dialog container with `v-model` for visibility
- `v-card`: Dialog content container
- `v-card-title`: Dialog header with server name
- `v-card-text`: Main content area for user list and form
- `v-list`: Display users in a list format
- `v-list-item`: Individual user items
- `v-text-field`: Email input with validation
- `v-btn`: Action buttons (Add, Cancel, Close)
- `v-progress-circular`: Loading indicator
- `v-alert`: Error and success messages

### GraphQL Integration
```javascript
import { API } from 'aws-amplify'
import { getServerUsers } from '@/graphql/queries'
import { addUserToServer } from '@/graphql/mutations'

// Fetch users
const response = await API.graphql({
  query: getServerUsers,
  variables: { instanceId: serverId }
})

// Add user
const response = await API.graphql({
  query: addUserToServer,
  variables: { 
    instanceId: serverId,
    userEmail: email
  }
})
```

### Email Validation
Use a robust email validation regex or library:
```javascript
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
```

Or use a more comprehensive validation library like `validator.js` if already in dependencies.

### Responsive Design
- Use Vuetify's responsive breakpoints
- Ensure dialog is full-screen on mobile devices
- Make touch targets at least 44x44px on mobile
- Use appropriate spacing and padding for different screen sizes

### Accessibility
- Ensure dialog has proper ARIA labels
- Provide keyboard navigation support
- Use semantic HTML elements
- Ensure sufficient color contrast
- Provide clear focus indicators

## Security Considerations

### Authorization
- User management operations are protected by `@aws_cognito_user_pools` directive
- Only authenticated users can access the GraphQL operations
- Backend validates that the requesting user has permission to manage the server

### Input Sanitization
- Email addresses are validated on the frontend before submission
- Backend performs additional validation through GraphQL schema (AWSEmail type)
- No direct user input is rendered without proper escaping (Vue handles this automatically)

### Error Messages
- Error messages should not expose sensitive system information
- Generic messages for authentication/authorization failures
- Specific messages only for user-actionable errors

## Performance Considerations

### Lazy Loading
- UserManagementDialog component can be lazy-loaded to reduce initial bundle size
- Only load when user clicks the user management button

### Caching
- Consider caching user lists for a short duration to reduce API calls
- Invalidate cache after successful user addition

### Debouncing
- If implementing search/filter functionality in the future, debounce input to reduce API calls

### Optimistic Updates
- Consider showing the newly added user immediately in the UI before the refresh completes
- Revert if the refresh shows the user wasn't actually added

## Future Enhancements

While not part of this initial implementation, consider these future improvements:
- Remove user functionality
- Search/filter users in large lists
- Bulk user addition
- User role management (if roles are added to the system)
- Audit log of user additions/removals
- Email invitation system for users not yet in Cognito
