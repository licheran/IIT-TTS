import { expect, test } from '@playwright/test'

test('the home page reports the API as ok', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('API: ok')).toBeVisible()
})
