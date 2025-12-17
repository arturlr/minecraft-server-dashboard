import { test, expect } from '@playwright/test';

test.describe('Authenticated User Tests', () => {
  test('should access dashboard after authentication', async ({ page }) => {
    // Navigate to the application (authentication state is already loaded)
    await page.goto('/');

    // Check if we have authentication credentials
    if (!process.env.GOOGLE_TEST_EMAIL || !process.env.GOOGLE_TEST_PASSWORD) {
      console.log('Skipping authenticated test - no credentials provided');
      test.skip();
      return;
    }

    // Verify we're authenticated and can see the dashboard
    await expect(page.locator('text=Sign in with Google')).not.toBeVisible();
    
    // Add more specific tests based on your dashboard content
    // For example:
    // await expect(page.locator('[data-testid="server-list"]')).toBeVisible();
    // await expect(page.locator('text=Welcome')).toBeVisible();
  });

  test('should be able to interact with server controls', async ({ page }) => {
    // Check if we have authentication credentials
    if (!process.env.GOOGLE_TEST_EMAIL || !process.env.GOOGLE_TEST_PASSWORD) {
      console.log('Skipping authenticated test - no credentials provided');
      test.skip();
      return;
    }

    await page.goto('/');

    // Wait for the dashboard to load
    await page.waitForLoadState('networkidle');

    // Test server-related functionality
    // This will depend on your specific UI
    // For example:
    // await expect(page.locator('[data-testid="server-card"]')).toBeVisible();
    // await page.click('[data-testid="start-server-button"]');
  });

  test('should maintain authentication across page reloads', async ({ page }) => {
    // Check if we have authentication credentials
    if (!process.env.GOOGLE_TEST_EMAIL || !process.env.GOOGLE_TEST_PASSWORD) {
      console.log('Skipping authenticated test - no credentials provided');
      test.skip();
      return;
    }

    await page.goto('/');
    
    // Reload the page
    await page.reload();
    
    // Verify we're still authenticated
    await expect(page.locator('text=Sign in with Google')).not.toBeVisible();
  });
});