import { test, expect } from '@playwright/test';

/**
 * Tests main app navigation after a complete onboarding.
 * Registers a fresh user, completes onboarding via UI, then verifies
 * that sidebar links navigate to key pages.
 */
test.describe('App navigation', () => {
  test.beforeEach(async ({ page }) => {
    const email = `e2e.nav.${Date.now()}@example.com`;

    await page.goto('/register');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Name').fill('Nav User');
    await page.getByLabel('Password').fill('testpass123');
    await page.getByRole('button', { name: 'Create account' }).click();

    await expect(page).toHaveURL('/setup');

    // Step 1
    await page.getByLabel('Tracking start date').fill('2026-01-01');
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 2
    await page.getByLabel('Account name').fill('My Bank');
    await page.getByLabel('Current balance (€)').fill('1000');
    await page.getByRole('button', { name: 'Next' }).last().click();

    // Steps 3-6: skip
    for (let i = 0; i < 4; i++) {
      await page.getByRole('button', { name: 'Next' }).last().click();
    }

    // Step 7: skip salary
    await page.getByRole('button', { name: 'Skip' }).click();

    // Step 8: confirm
    await page.getByRole('button', { name: 'Confirm & start' }).click();
    await expect(page).toHaveURL('/');
  });

  test('sidebar links navigate to correct pages', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();

    await page.getByRole('link', { name: 'Transactions' }).click();
    await expect(page).toHaveURL('/transactions');

    await page.getByRole('link', { name: 'Summary' }).click();
    await expect(page).toHaveURL('/summary');

    await page.getByRole('link', { name: 'Transfers' }).click();
    await expect(page).toHaveURL('/transfers');

    await page.getByRole('link', { name: 'Assets' }).click();
    await expect(page).toHaveURL('/assets');
  });

  test('sign out redirects to login', async ({ page }) => {
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page).toHaveURL('/login');
  });
});
