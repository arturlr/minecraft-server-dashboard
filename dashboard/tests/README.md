# Playwright Testing with Google OAuth Authentication

This directory contains Playwright tests for the Minecraft Dashboard application, including automated Google OAuth authentication through AWS Amplify/Cognito federation.

## Setup

### 1. Environment Variables

You can set environment variables in several ways:

**Option 1: Create a `.env.test` file** (recommended)
```bash
# Test Google account credentials
GOOGLE_TEST_EMAIL=your-test-email@gmail.com
GOOGLE_TEST_PASSWORD=your-test-password
```

**Option 2: Set environment variables directly**
```bash
export GOOGLE_TEST_EMAIL=your-test-email@gmail.com
export GOOGLE_TEST_PASSWORD=your-test-password
npx playwright test
```

**Option 3: Pass environment variables inline**
```bash
GOOGLE_TEST_EMAIL=your-test-email@gmail.com GOOGLE_TEST_PASSWORD=your-test-password npx playwright test
```

**Important Security Notes:**
- Use a dedicated test Google account, not your personal account
- Consider using Google App Passwords if you have 2FA enabled
- Never commit these credentials to version control
- Add `.env.test` to your `.gitignore` file

### 2. Google Account Setup

For reliable testing, your test Google account should:
- Have 2FA disabled (or use App Passwords)
- Be added to your Cognito User Pool's Google OAuth configuration
- Have appropriate permissions in your AWS Cognito setup

### 3. Running Tests

```bash
# Install dependencies
npm install

# Run all tests (includes authentication setup)
npm run test:e2e

# Run with visible browser
npm run test:e2e:headed

# Debug authentication
npm run test:auth -- --debug

# Or run directly with environment variables
GOOGLE_TEST_EMAIL=test@gmail.com GOOGLE_TEST_PASSWORD=password npm run test:e2e

# Run specific tests
npx playwright test authenticated.spec.ts

# Run only basic tests (no authentication required)
npx playwright test basic.spec.ts
```

### Running Without Credentials

If you don't have Google test credentials set up, you can still run basic tests:

```bash
# Run basic application tests only
npm run test:e2e basic.spec.ts

# All authenticated tests will be automatically skipped
npm run test:e2e
```

## Authentication Flow

The authentication setup (`auth.setup.ts`) handles:

1. **Navigation**: Goes to the application root
2. **Login Trigger**: Clicks the "Sign in with Google" button
3. **OAuth Flow**: Handles both direct Google OAuth and Cognito Hosted UI flows
4. **Credential Entry**: Automatically fills in Google credentials
5. **Consent Handling**: Manages OAuth consent screens if they appear
6. **State Persistence**: Saves authentication state for subsequent tests

## Test Structure

### `auth.setup.ts`
- Handles the complete Google OAuth authentication flow
- Saves authentication state to `playwright/.auth/user.json`
- Runs before all other tests that require authentication
- Creates empty storage state if credentials aren't provided

### `basic.spec.ts`
- Basic application tests that don't require authentication
- Tests login page, application loading, etc.
- Always runs regardless of credential availability

### `authenticated.spec.ts`
- Contains tests that require user authentication
- Uses the saved authentication state
- Automatically skips if credentials aren't provided
- Tests dashboard functionality, server controls, etc.

### `dashboard.spec.ts`
- Dashboard-specific functionality tests
- Requires authentication to run
- Automatically skips if credentials aren't provided

### `example.spec.ts`
- Basic Playwright examples (can be removed)

## Configuration

### `playwright.config.ts`
- Configured with a setup project that runs authentication
- Main test projects depend on the setup project
- Uses saved authentication state for authenticated tests

## Troubleshooting

### Common Issues

1. **Authentication Fails**
   - Verify Google credentials are correct
   - Check if 2FA is disabled or use App Passwords
   - Ensure test account has access to the application

2. **Timeout Errors**
   - Google OAuth can be slow; timeouts are set to 30 seconds
   - Network issues can cause delays
   - Try running with `--headed` to see what's happening

3. **Consent Screen Issues**
   - First-time OAuth may require consent
   - The setup handles basic consent screens
   - Complex consent flows may need manual handling

4. **Cognito Configuration**
   - Ensure your Cognito User Pool has Google OAuth properly configured
   - Check redirect URLs match your test environment
   - Verify the Google OAuth client is properly set up

### Debug Mode

Run tests in debug mode to step through the authentication flow:

```bash
npx playwright test auth.setup.ts --debug
```

### Headed Mode

Run tests with a visible browser to see the authentication flow:

```bash
npx playwright test --headed
```

## Best Practices

1. **Dedicated Test Account**: Always use a separate Google account for testing
2. **Environment Isolation**: Keep test credentials separate from production
3. **State Management**: The authentication state is saved and reused across tests
4. **Error Handling**: The setup includes error handling for common OAuth scenarios
5. **Timeouts**: Generous timeouts account for OAuth redirect delays

## Extending Tests

To add new authenticated tests:

1. Create a new test file in the `tests/` directory
2. Import `{ test, expect }` from `@playwright/test`
3. Your tests will automatically use the saved authentication state
4. Focus on testing application functionality, not authentication

Example:
```typescript
import { test, expect } from '@playwright/test';

test('should display server list', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('[data-testid="server-list"]')).toBeVisible();
});
```