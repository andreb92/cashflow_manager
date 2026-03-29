import { test, expect } from '@playwright/test';

/**
 * Full end-to-end flow: register → complete 8-step onboarding wizard → dashboard.
 * Uses a unique email per run so tests are idempotent against a running backend.
 */
test('complete onboarding wizard and reach dashboard', async ({ page }) => {
  const email = `e2e.onboarding.${Date.now()}@example.com`;

  // --- Register ---
  await page.goto('/register');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Name').fill('E2E User');
  await page.getByLabel('Password').fill('testpass123');
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL('/setup');
  await expect(page.getByRole('heading', { name: 'Setup your account' })).toBeVisible();

  // --- Step 1: Tracking start date ---
  await expect(page.getByRole('heading', { name: 'When do you want to start tracking?' })).toBeVisible();
  await page.getByLabel('Tracking start date').fill('2026-01-01');
  await page.getByRole('button', { name: 'Next' }).click();

  // --- Step 2: Main bank account ---
  await expect(page.getByRole('heading', { name: 'Main bank account' })).toBeVisible();
  await page.getByLabel('Account name').fill('My Bank');
  await page.getByLabel('Current balance (€)').fill('5000');
  // Step 2 has Back + Next buttons; click the last Next
  await page.getByRole('button', { name: 'Next' }).last().click();

  // --- Step 3: Additional banks (optional — skip) ---
  await expect(page.getByRole('heading', { name: 'Additional bank accounts (optional)' })).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).last().click();

  // --- Step 4: Payment methods (optional — skip) ---
  await expect(page.getByRole('heading', { name: 'Payment methods (optional)' })).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).last().click();

  // --- Step 5: Saving accounts (optional — skip) ---
  await expect(page.getByRole('heading', { name: 'Saving accounts (optional)' })).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).last().click();

  // --- Step 6: Investment accounts (optional — skip) ---
  await expect(page.getByRole('heading', { name: 'Investment accounts (optional)' })).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).last().click();

  // --- Step 7: Salary configuration (optional — skip) ---
  await expect(page.getByRole('heading', { name: 'Salary configuration (optional)' })).toBeVisible();
  await page.getByRole('button', { name: 'Skip' }).click();

  // --- Step 8: Review & confirm ---
  await expect(page.getByRole('heading', { name: 'Review & confirm' })).toBeVisible();
  await expect(page.getByText('My Bank')).toBeVisible();
  await expect(page.getByText('2026-01-01')).toBeVisible();
  await page.getByRole('button', { name: 'Confirm & start' }).click();

  // --- Dashboard ---
  await expect(page).toHaveURL('/');
  await expect(page.getByText('CashFlow')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
});
