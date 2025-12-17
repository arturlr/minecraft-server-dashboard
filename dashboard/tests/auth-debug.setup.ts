import { test as setup, expect } from '@playwright/test';
import { mkdir, writeFile } from 'fs/promises';
import { dirname } from 'path';

const authFile = 'playwright/.auth/user.json';

setup('DEBUG: authenticate with Google via Amplify', async ({ page }) => {
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

  console.log('🚀 Starting authentication flow...');
  console.log('📧 Using email:', googleEmail);

  // Navigate to the application
  await page.goto('/');
  console.log('📱 Navigated to application');

  // Wait for the auth view to load
  await expect(page.locator('text=Minecraft Dashboard by GeckoByte')).toBeVisible();
  console.log('✅ Auth view loaded');

  // Take a screenshot before clicking
  try {
    await page.screenshot({ path: 'playwright/.auth/01-before-click.png' });
  } catch (error) {
    console.log('Could not take before-click screenshot');
  }

  // Click the Google sign-in button
  await page.getByRole('button', { name: /sign in with google/i }).click();
  console.log('🔘 Clicked Google sign-in button');

  // Wait for redirect and take screenshot
  await page.waitForLoadState('networkidle');
  try {
    await page.screenshot({ path: 'playwright/.auth/02-after-redirect.png' });
  } catch (error) {
    console.log('Could not take after-redirect screenshot - page may have changed');
  }
  
  const currentUrl = page.url();
  console.log('🌐 Current URL after redirect:', currentUrl);

  // For debugging, let's pause here and see what happens
  console.log('⏸️  Pausing for manual inspection...');
  console.log('Current page title:', await page.title());
  console.log('Current URL:', page.url());
  
  // Save a screenshot and page content for debugging
  try {
    await page.screenshot({ path: 'playwright/.auth/debug-current-state.png' });
  } catch (error) {
    console.log('Could not take debug screenshot - page may be closed');
  }
  
  // Create an empty storage state for now
  const emptyStorageState = {
    cookies: [],
    origins: []
  };
  await writeFile(authFile, JSON.stringify(emptyStorageState, null, 2));
  
  console.log('💾 Created empty storage state for debugging');
});