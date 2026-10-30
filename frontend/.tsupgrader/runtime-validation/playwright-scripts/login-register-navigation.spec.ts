import { test, expect } from '@playwright/test';

test.use({ channel: 'msedge' });

test('login-register-navigation', async ({ page }) => {
  await page.route("**/*", async route => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.origin === "http://127.0.0.1:4173") {
      await route.continue();
    } else {
      await route.abort("blockedbyclient");
    }
  });
  await page.goto('http://127.0.0.1:4173');
  await page.getByRole('link', { name: 'Create an account' }).click();
  await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible();
});
