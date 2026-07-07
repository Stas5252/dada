import { test, expect } from '@playwright/test';

test.describe('Authentication Flows & Validation', () => {
  test('Login empty form validation', async ({ page }) => {
    await page.goto('/login');
    await page.click('button[type="submit"]');

    // Wait for native HTML5 validation or custom validation
    // Playwright evaluates the `:invalid` pseudo-class for native HTML5 validation
    const emailInput = page.locator('input[name="email"]');
    await expect(emailInput).toHaveCSS('border-color', /.*/); // Just wait for element

    const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBe(true);
  });

  test('Login with incorrect credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Expected: error message alert "Неверный логин или пароль"
    const errorMessage = page.locator('text=Неверный').or(page.locator('text=ошибка').or(page.locator('[role="alert"]')));
    await expect(errorMessage.first()).toBeVisible({ timeout: 5000 });
  });

  test('Password reset navigation', async ({ page }) => {
    await page.goto('/login');
    await page.click('text=Забыли пароль?');
    await expect(page).toHaveURL(/.*\/forgot-password/);
    
    // Check elements on forgot password
    await expect(page.locator('text=Восстановление пароля').first()).toBeVisible();
    await page.fill('input[type="email"]', 'test@example.com');
    await page.click('button[type="submit"]');
  });
});
