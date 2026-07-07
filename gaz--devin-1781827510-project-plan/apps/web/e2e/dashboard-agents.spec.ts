import { test, expect } from '@playwright/test';

test.describe('Dashboard & Agents', () => {
  test.beforeEach(async ({ page }) => {
    // Log in before each test
    await page.goto('/login');
    await page.fill('input[name="email"]', 'owner@demo-pizza.example.com');
    await page.fill('input[name="password"]', 'safe-local-password');
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*\/dashboard/, { timeout: 15000 });
  });

  test('Create a new AI Agent flow', async ({ page }) => {
    await page.click('text=Агенты');
    await page.waitForURL(/.*\/agents/);
    
    // Empty state or existing agents list
    await expect(page.locator('text=Создать агента').first()).toBeVisible();
    await page.click('text=Создать агента');
    await page.waitForURL(/.*\/agents\/new/);

    // Fill agent creation form
    await page.fill('input[name="name"]', 'QA Test Agent');
    await page.fill('textarea[name="prompt"]', 'You are a helpful QA assistant.');
    
    // Test that the form submits
    await page.click('button[type="submit"]');

    // Expected to redirect to agent pathway/details or back to agents
    await page.waitForURL(/.*\/agents(\/.*)?/);
    
    // Check if agent appears in the list
    if (page.url().endsWith('/agents')) {
      await expect(page.locator('text=QA Test Agent').first()).toBeVisible();
    }
  });

  test('Dashboard UI Audit', async ({ page }) => {
    // Check for correct typography and layout structure
    await expect(page.locator('text=Обзор').first()).toBeVisible();
    await expect(page.locator('text=Аналитика').first()).toBeVisible();

    // The background should remain dark inside the dashboard
    const body = page.locator('body');
    await expect(body).toHaveCSS('background-color', /rgb\(5,\s*5,\s*5\)|rgb\(5,\s*5,\s*6\)/);
  });
});
