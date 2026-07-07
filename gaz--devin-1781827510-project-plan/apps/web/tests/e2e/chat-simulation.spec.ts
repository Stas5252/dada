import { test, expect } from '@playwright/test';

test.describe('Chat Simulation Flow', () => {
  test.setTimeout(90000);

  test('should allow user to send a mock chat message from the test console', async ({ page }) => {
    // 1. Navigate to Register
    await page.goto('http://localhost:3000/register');
    
    // 2. Fill out registration form
    const uniqueEmail = `chat_${Date.now()}@example.com`;
    await page.fill('input[name="owner_name"]', 'Chat Test');
    await page.fill('input[name="company_name"]', 'Chat Inc');
    await page.fill('input[name="owner_email"]', uniqueEmail);
    await page.fill('input[name="password"]', 'password123');
    
    // 3. Submit
    await page.click('text="Создать аккаунт"');
    
    // 4. Wait for redirect to Dashboard
    await page.waitForURL('http://localhost:3000/dashboard');
    
    // 5. Navigate to Agents List and Create an Agent
    await page.goto('http://localhost:3000/agents/new');
    await page.fill('input[name="name"]', 'Test Console Agent');
    await page.fill('textarea[name="goal"]', 'Help customers.');
    await page.fill('textarea[name="prompt"]', 'You are a test agent.');
    await page.click('text="Сохранить draft"');
    await page.waitForURL('**/agents*');
    
    // 5. Navigate to Test Console page
    await page.goto('http://localhost:3000/test-console');
    
    // 6. Verify Test Console page loaded
    await expect(page.locator('h1')).toContainText('Тестовый диалог');
    
    // 7. Verify we have an agent in the dropdown
    const selectLocator = page.locator('select[name="agent_id"]');
    await expect(selectLocator).toBeVisible();
    
    // 8. Submit the mock chat form
    await page.fill('textarea[name="message"]', 'E2E Test Message: Hello AI!');
    // Use precise text locator for the correct submit button in test console
    await Promise.all([
      page.waitForURL('**/conversations/*', { timeout: 90000 }),
      page.click('button:has-text("Запустить тест")'),
    ]);
    
    // 9. The server action redirects to the created conversation on success.
    await expect(page.url()).toContain('/conversations/');
  });
});
