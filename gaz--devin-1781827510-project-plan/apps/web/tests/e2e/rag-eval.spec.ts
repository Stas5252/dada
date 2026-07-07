import { test, expect } from '@playwright/test';

test.describe('RAG Eval Flow', () => {
  test.setTimeout(90000);

  test('should run a tenant-scoped golden RAG eval from the knowledge page', async ({ page }) => {
    await page.goto('http://localhost:3000/register');

    const uniqueEmail = `rag_eval_ui_${Date.now()}@example.com`;
    await page.fill('input[name="owner_name"]', 'RAG Eval User');
    await page.fill('input[name="company_name"]', 'RAG Eval Company');
    await page.fill('input[name="owner_email"]', uniqueEmail);
    await page.fill('input[name="password"]', 'password123');
    await page.locator('button[type="submit"]').click();

    await page.waitForURL('http://localhost:3000/dashboard', { timeout: 90000 });
    await page.goto('http://localhost:3000/knowledge');

    const sourceForm = page.locator('[data-testid="knowledge-source-form"]');
    await sourceForm.locator('input[name="title"]').fill('RAG E2E Delivery FAQ');
    await sourceForm.locator('textarea[name="content"]').fill(
      'Delivery takes 45 minutes. Free delivery starts from 1000 RUB.',
    );
    await page.locator('[data-testid="knowledge-source-submit"]').click();
    await page.waitForURL('**/knowledge?notice=knowledge-created', { timeout: 90000 });

    await page.fill('[data-testid="rag-eval-query"]', 'delivery minutes');
    await page.fill('[data-testid="rag-eval-terms"]', '45 minutes');
    await page.fill('[data-testid="rag-eval-negative-query"]', 'Do you repair laptops?');
    await page.locator('[data-testid="rag-eval-run"]').click();

    await expect(page.locator('[data-testid="rag-eval-result"]')).toBeVisible({ timeout: 90000 });
    await expect(page.locator('[data-testid="rag-eval-status"]')).toContainText('passed');
    await expect(page.locator('[data-testid="rag-eval-result"]')).toContainText('RAG E2E Delivery FAQ');
    await expect(page.locator('[data-testid="rag-eval-result"]')).toContainText('45 minutes');
  });
});
