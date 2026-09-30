import { expect, test } from '@playwright/test'

test('rows are typed into the entry row with the keyboard only', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('option', { name: 'academic_weekly' })).toBeAttached()
  await page.getByLabel('Name').fill('Quick entry')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'Quick entry' }).click()

  await page.getByRole('tab', { name: 'Teachers', exact: true }).click()
  const code = page.getByLabel('New code (required)')
  await expect(code).toBeVisible()

  await code.click()
  for (const [c, name] of [
    ['AB', 'Ada B'],
    ['CD', 'Cy D'],
    ['EF', 'Eve F'],
  ]) {
    await expect(code).toBeFocused()
    await page.keyboard.type(c!)
    await page.keyboard.press('Tab')
    await page.keyboard.type(name!)
    await page.keyboard.press('Enter')
    await expect(page.locator(`[role=row][data-key="${c}"]`)).toBeVisible()
  }
  await expect(code).toBeFocused()
  await expect(code).toHaveValue('')
  await expect(page.getByText('3 rows')).toBeVisible()

  // A duplicate code is refused, what was typed stays, and the message shows.
  await page.keyboard.type('AB')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(code).toHaveValue('AB')
})
