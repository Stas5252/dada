import { test, expect } from '@playwright/test';

test.describe('Billing & Subscriptions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'owner@demo-pizza.example.com');
    await page.fill('input[name="password"]', 'safe-local-password');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*\/dashboard/);
  });

  test('Billing page structure', async ({ page }) => {
    await page.goto('/billing');
    
    await expect(page.locator('text=Тарифы').or(page.locator('text=Подписка')).first()).toBeVisible();
    await expect(page.locator('text=Business').first()).toBeVisible();
  });
});
