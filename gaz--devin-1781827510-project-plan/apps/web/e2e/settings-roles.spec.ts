import { test, expect } from '@playwright/test';

test.describe('Settings & Roles', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'owner@demo-pizza.example.com');
    await page.fill('input[name="password"]', 'safe-local-password');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*\/dashboard/);
  });

  test('Settings: Team members and API Keys', async ({ page }) => {
    // Navigate to settings -> team
    await page.goto('/settings/team');
    await expect(page.locator('text=Команда').first()).toBeVisible();
    await expect(page.locator('text=Пригласить').first()).toBeVisible();

    // Navigate to API Keys
    await page.goto('/settings/api-keys');
    await expect(page.locator('text=API ключи').first()).toBeVisible();
    const createBtn = page.locator('text=Создать ключ').or(page.locator('text=Новый ключ'));
    await expect(createBtn.first()).toBeVisible();
  });
});
