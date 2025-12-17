import { test, expect } from '@playwright/test';

// These tests specifically test the unauthenticated state
test.describe('Unauthenticated User Tests', () => {
  test.use({ 
    // Don't use any stored authentication state for these tests
    storageState: { cookies: [], origins: [] }
  });

  test('should show login page when not authenticated', async ({ page }) => {
    await page.goto('/');

    // Wait for the application to load
    await page.waitForLoadState('networkidle');

    // Should show the login page
    await expect(page.locator('text=Minecraft Dashboard by GeckoByte')).toBeVisible();
    await expect(page.locator('text=Sign in with Google')).toBeVisible();
  });

  test('should have correct page title', async ({ page }) => {
    await page.goto('/');
    
    // Check that the page has the correct title
    await expect(page).toHaveTitle('Minecraft Dashboard');
  });

  test('should display the Google sign-in button', async ({ page }) => {
    await page.goto('/');
    
    // Check that the Google sign-in button is present and clickable
    const signInButton = page.getByRole('button', { name: /sign in with google/i });
    await expect(signInButton).toBeVisible();
    await expect(signInButton).toBeEnabled();
  });

  test('should show login form elements', async ({ page }) => {
    await page.goto('/');
    
    // Verify login page elements
    await expect(page.locator('text=This application requires you to login')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in with google/i })).toBeVisible();
  });
});