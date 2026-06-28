import { test, expect } from '@playwright/test';

test.describe('CallForce Smoke Tests', () => {
  test('should load landing page and display main title', async ({ page }) => {
    await page.goto('/');
    const title = page.locator('h1');
    await expect(title).toBeVisible();
    await expect(page).toHaveTitle(/CallForce/);
  });

  test('should display login page form elements', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should display register page form elements', async ({ page }) => {
    await page.goto('/register');
    await expect(page.locator('input[name="owner_name"]')).toBeVisible();
    await expect(page.locator('input[name="owner_email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should load legal pages', async ({ page }) => {
    await page.goto('/privacy');
    await expect(page.locator('h1')).toContainText(/политика/i);

    await page.goto('/terms');
    await expect(page.locator('h1')).toContainText(/оферта|условия/i);

    await page.goto('/docs');
    await expect(page.locator('h1')).toContainText(/документация|guide/i);
  });

  test('should load ROI calculator', async ({ page }) => {
    await page.goto('/roi-calculator');
    await expect(page.locator('h1')).toContainText(/сэкономите/i);
    await expect(page.getByText(/Рассчитайте выгоду|Введите/i).first()).toBeVisible();
  });
});
