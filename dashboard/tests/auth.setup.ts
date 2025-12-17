import { test as setup, expect } from '@playwright/test';
import { mkdir, writeFile } from 'fs/promises';
import { dirname } from 'path';

const authFile = 'playwright/.auth/user.json';

setup('authenticate with Google via Amplify', async ({ page }) => {
  // Ensure the auth directory exists
  await mkdir(dirname(authFile), { recursive: true });

  // Get credentials from environment variables
  const googleEmail = process.env.GOOGLE_TEST_EMAIL;
  const googlePassword = process.env.GOOGLE_TEST_PASSWORD;

  if (!googleEmail || !googlePassword) {
    console.log('Skipping authentication setup - GOOGLE_TEST_EMAIL and GOOGLE_TEST_PASSWORD environment variables not set');
    console.log('To enable authentication testing, create a .env.test file with your test credentials');
    
    // Create an empty storage state file so dependent tests don't fail
    const emptyStorageState = {
      cookies: [],
      origins: []
    };
    await writeFile(authFile, JSON.stringify(emptyStorageState, null, 2));
    return;
  }

  // Navigate to the application
  await page.goto('/');

  // Wait for the auth view to load
  await expect(page.locator('text=Minecraft Dashboard by GeckoByte')).toBeVisible();

  // Click the Google sign-in button
  await page.getByRole('button', { name: /sign in with google/i }).click();

  // Wait for redirect to Google OAuth (could be accounts.google.com or cognito domain)
  await page.waitForLoadState('networkidle');
  
  // Check if we're redirected to Google or Cognito hosted UI
  const currentUrl = page.url();
  console.log('Redirected to:', currentUrl);
  
  if (currentUrl.includes('accounts.google.com')) {
    console.log('Handling direct Google OAuth flow');
    await handleGoogleDirectAuth(page, googleEmail, googlePassword);
  } else if (currentUrl.includes('amazoncognito.com')) {
    console.log('Handling Cognito Hosted UI flow');
    await handleCognitoHostedUI(page, googleEmail, googlePassword);
  } else {
    console.log('Unexpected redirect URL:', currentUrl);
    // Take a screenshot for debugging (only if page is still available)
    try {
      await page.screenshot({ path: 'playwright/.auth/unexpected-redirect-debug.png' });
    } catch (screenshotError) {
      console.log('Could not take screenshot - page may be closed');
    }
    throw new Error(`Unexpected redirect URL: ${currentUrl}`);
  }

  // Wait for redirect back to the application with more flexible URL matching
  try {
    await page.waitForURL(/localhost:5173/, { timeout: 30000 });
  } catch (error) {
    console.log('Timeout waiting for redirect. Current URL:', page.url());
    // Take a screenshot for debugging (only if page is still available)
    try {
      await page.screenshot({ path: 'playwright/.auth/auth-timeout-debug.png' });
    } catch (screenshotError) {
      console.log('Could not take screenshot - page may be closed');
    }
    throw error;
  }

  // Wait for the application to process the authentication
  await page.waitForLoadState('networkidle');

  // Verify authentication was successful
  // Check that we're no longer seeing the login button
  try {
    await expect(page.locator('text=Sign in with Google')).not.toBeVisible({ timeout: 10000 });
  } catch (error) {
    console.log('Authentication may have failed. Current page content:');
    console.log(await page.content());
    throw error;
  }

  // Additional verification - check for authenticated content
  // This might be a user menu, dashboard content, etc.
  // Adjust based on your app's post-login UI
  try {
    // Wait for some authenticated content to appear
    await page.waitForSelector('[data-testid="authenticated-content"]', { timeout: 5000 });
  } catch (error) {
    // If no specific test ID, just ensure we're not on auth page
    console.log('No specific authenticated content selector found, proceeding with basic verification');
  }

  // Save authentication state
  await page.context().storageState({ path: authFile });
});

async function handleGoogleDirectAuth(page: any, email: string, password: string) {
  console.log('Filling in Google credentials...');
  
  // Handle direct Google OAuth flow
  await page.fill('input[type="email"]', email);
  await page.click('#identifierNext');

  // Wait for password field
  await page.waitForSelector('input[type="password"]', { state: 'visible' });
  await page.fill('input[type="password"]', password);
  await page.click('#passwordNext');

  // Handle potential consent screen
  try {
    await page.waitForSelector('text=Continue', { timeout: 5000 });
    console.log('Consent screen detected, clicking Continue...');
    await page.click('text=Continue');
  } catch (error) {
    console.log('No consent screen detected, continuing...');
  }

  // Handle potential "This browser or app may not be secure" warning
  try {
    await page.waitForSelector('text=Advanced', { timeout: 3000 });
    console.log('Security warning detected, clicking Advanced...');
    await page.click('text=Advanced');
    await page.click('text=Go to');
  } catch (error) {
    console.log('No security warning detected');
  }
}

async function handleCognitoHostedUI(page: any, email: string, password: string) {
  // Handle Cognito Hosted UI flow
  // Look for Google sign-in button in Cognito UI
  await page.click('button:has-text("Google"), a:has-text("Google"), [data-provider="Google"]');
  
  // Now handle the Google authentication
  await page.waitForURL(/accounts\.google\.com/);
  await handleGoogleDirectAuth(page, email, password);
}

