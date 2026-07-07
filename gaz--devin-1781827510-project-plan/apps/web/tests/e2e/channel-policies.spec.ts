import { test, expect } from '@playwright/test';

test.describe('Channel Policy Settings', () => {
  test.setTimeout(90000);

  test('should save and reload channel policy controls', async ({ page }) => {
    await page.goto('/register');

    const uniqueEmail = `channel_policy_${Date.now()}@example.com`;
    await page.fill('input[name="owner_name"]', 'Channel Policy User');
    await page.fill('input[name="company_name"]', 'Channel Policy Company');
    await page.fill('input[name="owner_email"]', uniqueEmail);
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard', { timeout: 90000 });

    await page.goto('/settings/channels');
    await expect(page.locator('label', { hasText: 'Opt-out notice' })).toHaveCount(5);
    await expect(page.locator('label', { hasText: 'Consent required' })).toHaveCount(5);
    await expect(page.getByRole('heading', { name: 'Production launch readiness' })).toBeVisible();
    const readinessSection = page.locator('section', {
      has: page.getByRole('heading', { name: 'Production launch readiness' }),
    });
    await expect(readinessSection.getByText('Web widget', { exact: true })).toBeVisible();
    await expect(readinessSection.getByText('LLM provider', { exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Webhook diagnostics' })).toBeVisible();
    await expect(page.locator('input[name="whatsapp_app_secret"]')).toBeVisible();
    await expect(page.locator('input[name="vk_secret_key"]')).toBeVisible();

    await page.locator('select[name="telegram_mode"]').selectOption('autopilot');
    await page.locator('input[name="telegram_require_opt_out_notice"][type="checkbox"]').check();
    await page.locator('input[name="telegram_require_contact_consent_for_outbound"][type="checkbox"]').check();
    await page.locator('input[name="telegram_max_auto_replies_per_conversation"]').fill('3');

    const channelPolicyForm = page.locator('form', {
      has: page.locator('select[name="telegram_mode"]'),
    });
    await channelPolicyForm.locator('button[type="submit"]').click();
    await page.waitForURL('**/settings/channels?notice=channel-policies-updated', {
      timeout: 90000,
    });

    await page.reload({ waitUntil: 'networkidle' });
    await expect(
      page.locator('input[name="telegram_require_opt_out_notice"][type="checkbox"]'),
    ).toBeChecked();
    await expect(
      page.locator('input[name="telegram_require_contact_consent_for_outbound"][type="checkbox"]'),
    ).toBeChecked();
    await expect(page.locator('input[name="telegram_max_auto_replies_per_conversation"]')).toHaveValue('3');
  });
});
