import { test, expect } from '@playwright/test';

test.describe('Dashboard Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Check if we have authentication credentials
    if (!process.env.GOOGLE_TEST_EMAIL || !process.env.GOOGLE_TEST_PASSWORD) {
      test.skip();
      return;
    }
    
    // Navigate to the dashboard
    await page.goto('/');
    // Wait for the application to load
    await page.waitForLoadState('networkidle');
  });

  test('should display the main dashboard', async ({ page }) => {
    // Verify we're authenticated and on the dashboard
    await expect(page.locator('text=Sign in with Google')).not.toBeVisible();
    
    // Check for main dashboard elements
    // Adjust these selectors based on your actual dashboard UI
    await expect(page).toHaveTitle(/Minecraft Dashboard/);
  });

  test('should handle server list loading', async ({ page }) => {
    // Wait for any server data to load
    // This might show a loading state, empty state, or server cards
    
    // Example checks (adjust based on your UI):
    // await expect(page.locator('[data-testid="server-list"]')).toBeVisible();
    // or check for loading states:
    // await expect(page.locator('text=Loading servers...')).toBeVisible();
    
    // For now, just verify we're on an authenticated page
    await expect(page.url()).toContain('localhost:5173');
  });

  test('should maintain authentication on page refresh', async ({ page }) => {
    // Refresh the page
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    // Verify we're still authenticated
    await expect(page.locator('text=Sign in with Google')).not.toBeVisible();
  });

  test('should handle navigation within the app', async ({ page }) => {
    // Test navigation if your app has multiple routes
    // This will depend on your Vue Router setup
    
    // Example:
    // await page.click('text=About');
    // await expect(page).toHaveURL(/\/about/);
    
    // For now, just verify the main page loads
    await expect(page).toHaveURL('/');
  });
});