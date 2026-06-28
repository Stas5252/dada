import { test, expect } from '@playwright/test';

test.describe('User Onboarding Flow', () => {
  test('should allow a new user to register and create an agent', async ({ page }) => {
    // 1. Navigate to Register
    await page.goto('http://localhost:3000/register');
    
    // 2. Fill out registration form
    const uniqueEmail = `testuser_${Date.now()}@example.com`;
    await page.fill('input[name="owner_name"]', 'E2E Test User');
    await page.fill('input[name="company_name"]', 'E2E Test Company');
    await page.fill('input[name="owner_email"]', uniqueEmail);
    await page.fill('input[name="password"]', 'password123');
    
    // 3. Submit
    await page.click('text="Создать аккаунт"');
    
    // 4. Wait for redirect to Dashboard
    await page.waitForURL('http://localhost:3000/dashboard');
    await expect(page.locator('h1')).toContainText('Панель Управления');
    
    // 5. Navigate to Agents List
    await page.click('text="AI-Агенты"');
    await page.waitForURL('http://localhost:3000/agents');
    
    // 6. Navigate to New Agent Builder
    // If the list is empty, there is a "Создать первого агента" button. Otherwise, "Создать агента"
    const newAgentButton = page.locator('text="Создать первого агента"').or(page.locator('text="Создать агента"'));
    await newAgentButton.first().click();
    await page.waitForURL('http://localhost:3000/agents/new');
    
    // 7. Fill out agent details
    await page.fill('input[name="name"]', 'E2E Test Agent');
    await page.fill('textarea[name="goal"]', 'Help customers via E2E test.');
    await page.fill('textarea[name="prompt"]', 'You are a test agent.');
    
    // 8. Submit agent draft
    await page.click('text="Сохранить draft"');
    
    // 9. Wait for redirect back to Agents list
    await page.waitForURL('**/agents*');
    
    // 10. Verify agent was created
    await expect(page.locator('text="E2E Test Agent"')).toBeVisible();
  });
});
