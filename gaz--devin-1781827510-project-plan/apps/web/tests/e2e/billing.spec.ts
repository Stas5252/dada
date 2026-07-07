import { test, expect } from '@playwright/test';

test.describe('Billing Flow', () => {
  test.setTimeout(90000);

  test('should allow user to navigate to billing and initiate checkout', async ({ page }) => {
    // 1. Navigate to Register
    await page.goto('http://localhost:3000/register');
    
    // 2. Fill out registration form
    const uniqueEmail = `billing_${Date.now()}@example.com`;
    await page.fill('input[name="owner_name"]', 'Billing Test');
    await page.fill('input[name="company_name"]', 'Billing Inc');
    await page.fill('input[name="owner_email"]', uniqueEmail);
    await page.fill('input[name="password"]', 'password123');
    
    // 3. Submit
    await page.click('text="Создать аккаунт"');
    
    // 4. Wait for redirect to Dashboard
    await page.waitForURL('http://localhost:3000/dashboard', { timeout: 90000 });
    
    // 5. Navigate to Billing page via side menu
    await page.goto('http://localhost:3000/billing');
    
    // 6. Verify Billing page loaded
    await expect(page.locator('h1')).toContainText('Тарифные планы и оплата');
    
    // 7. Click on "Перейти" for Pro plan
    // We can use a locator that finds the Pro plan card and clicks its action link
    const proCard = page.locator('.p-6.rounded-2xl', { hasText: 'Pro' });
    const upgradeButton = proCard.locator('a', { hasText: 'Перейти' });
    await upgradeButton.click();
    
    // 8. Wait for redirect to checkout
    await page.waitForURL('**/billing/checkout*', { timeout: 90000 });
    
    // 9. Check checkout page text (Assuming it shows a confirmation or redirects)
    // Note: The /billing/checkout page in Next.js might be a server action or another page
    // Let's just verify we landed on checkout URL correctly
    expect(page.url()).toContain('/billing/checkout');
  });
});
