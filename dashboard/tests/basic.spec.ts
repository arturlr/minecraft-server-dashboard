import { test, expect } from '@playwright/test';

test.describe('Basic Application Tests', () => {
  test('should load the application successfully', async ({ page }) => {
    await page.goto('/');

    // Wait for the application to load
    await page.waitForLoadState('networkidle');

    // The application should load successfully (either login page or authenticated state)
    // Just verify the page loads without errors
    await expect(page).not.toHaveTitle('');
    console.log('✅ Application loaded successfully');
  });

  test('should have correct page title', async ({ page }) => {
    await page.goto('/');
    
    // Check that the page has the correct title
    await expect(page).toHaveTitle('Minecraft Dashboard');
  });

  test('should handle authentication state appropriately', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check if we're authenticated or not
    const isSignInVisible = await page.locator('text=Sign in with Google').isVisible();
    
    if (isSignInVisible) {
      // Not authenticated - should show login page
      await expect(page.locator('text=Minecraft Dashboard by GeckoByte')).toBeVisible();
      await expect(page.getByRole('button', { name: /sign in with google/i })).toBeVisible();
      console.log('✅ Showing login page for unauthenticated user');
    } else {
      // Authenticated - should not show login page
      await expect(page.locator('text=Sign in with Google')).not.toBeVisible();
      console.log('✅ User is authenticated, login page not shown');
    }
  });
});