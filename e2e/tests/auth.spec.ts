import { test, expect } from '@playwright/test';

const uniqueEmail = () => `e2e.auth.${Date.now()}@example.com`;

test.describe('Authentication', () => {
  test('unauthenticated visit to / redirects to /login', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL('/login');
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
  });

  test('register creates account and redirects to setup wizard', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible();

    await page.getByLabel('Email').fill(uniqueEmail());
    await page.getByLabel('Name').fill('Test User');
    await page.getByLabel('Password').fill('testpass123');
    await page.getByRole('button', { name: 'Create account' }).click();

    await expect(page).toHaveURL('/setup');
    await expect(page.getByRole('heading', { name: 'Setup your account' })).toBeVisible();
  });

  test('login with wrong credentials shows error', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email').fill('nobody@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByRole('alert')).toContainText('Invalid email or password');
    await expect(page).toHaveURL('/login');
  });

  test('register page links back to login', async ({ page }) => {
    await page.goto('/register');
    await page.getByRole('link', { name: 'Sign in' }).click();
    await expect(page).toHaveURL('/login');
  });

  test('login page links to register', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('link', { name: 'Register' }).click();
    await expect(page).toHaveURL('/register');
  });
});
