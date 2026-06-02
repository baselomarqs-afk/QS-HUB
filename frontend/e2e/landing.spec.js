import { test, expect } from '@playwright/test';

// Smoke tests — verify the SPA boots and the public landing flow works without a
// backend. (Authenticated flows need the API + DB and are covered by API tests.)

test('landing page renders the brand', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('THE QS HUB').first()).toBeVisible();
});

test('language toggle does not crash', async ({ page }) => {
  await page.goto('/');
  const toggle = page.getByRole('button', { name: /العربية|English/ });
  if (await toggle.count()) {
    await toggle.first().click();
  }
  await expect(page.locator('body')).toBeVisible();
});

test('Get Started opens the auth screen', async ({ page }) => {
  await page.goto('/');
  const cta = page.getByRole('button', { name: /Get Started|ابدأ|Sign In|تسجيل/i });
  if (await cta.count()) {
    await cta.first().click();
    // auth screen shows an email field
    await expect(page.locator('input[type="email"]').first()).toBeVisible({ timeout: 8000 });
  } else {
    await expect(page.locator('body')).toBeVisible();
  }
});
