import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'

const CONFIG = resolve(import.meta.dirname, '../../backend/tests/fixtures/l6-config/l6-config.xlsx')

test('configured L6: plan, solve, edit a session, rebuild and keep the edit', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('API: ok')).toBeVisible()
  await expect(page.getByRole('option', { name: 'academic_weekly' })).toBeAttached()

  await page.getByLabel('Name').fill('L6 configured')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'L6 configured' }).click()

  await page.getByRole('link', { name: 'Import / export' }).click()
  await page.getByLabel('Workbook file').setInputFiles(CONFIG)
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(page.getByText('Imported.')).toBeVisible()

  // The configuration has Session types, and the Activities tab has nothing to show yet.
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Session types' }).click()
  await expect(page.locator('[role=row][data-key="LEC"]')).toBeVisible()
  await expect(page.locator('[role=row][data-key="TUT"]')).toBeVisible()
  await page.getByRole('tab', { name: 'Activities' }).click()
  await expect(page.getByText(/Nothing solved yet/)).toBeVisible()

  // Pre-flight finds nothing and lists the sessions the solver will make.
  await page.getByRole('link', { name: 'Pre-flight' }).click()
  await expect(page.getByText('No problems found')).toBeVisible()
  await expect(page.getByRole('heading', { name: /Sessions to schedule \(\d+\)/ })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Sessions to schedule' })).toBeVisible()

  // Solve.
  await page.getByRole('link', { name: 'Run', exact: true }).click()
  await page.getByLabel('Time limit (seconds)').fill('60')
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByRole('status').filter({ hasText: /^succeeded$/ })).toBeVisible({
    timeout: 120_000,
  })

  // The sessions are there. Move one tutorial to another day.
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Activities' }).click()
  const row = page.locator('[role=row][data-key$="-TUT-01"]').first()
  await expect(row).toBeVisible()
  const code = (await row.getAttribute('data-key'))!
  const before = (await row.locator('[data-column=day]').innerText()).replace('✎', '').trim()
  await row.locator('[data-column=day]').dblclick()
  const editor = page.getByLabel(`Day of ${code}`)
  const days = await editor.locator('option').evaluateAll((o) => o.map((x) => x.textContent ?? ''))
  const other = days.filter((d) => d !== '' && d !== before).at(-1)!
  await editor.selectOption(other)
  await editor.press('Enter')
  await expect(row.locator('[data-column=day]')).toHaveAttribute('data-edited', 'true')
  await expect(row.locator('[data-column=day]')).toContainText(other)
  await expect(page.getByText('1 edit waiting: press Rebuild.')).toBeVisible()

  // The Run tab offers a rebuild, and it keeps the edit.
  await page.getByRole('link', { name: 'Run', exact: true }).click()
  await page.getByLabel('Time limit (seconds)').fill('60')
  await page.getByRole('button', { name: 'Rebuild' }).click()
  await expect(page.getByRole('status').filter({ hasText: /^succeeded$/ })).toBeVisible({
    timeout: 120_000,
  })
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Activities' }).click()
  const kept = page.locator(`[role=row][data-key="${code}"]`)
  await expect(kept.locator('[data-column=day]')).toContainText(other)
  await expect(kept.locator('[data-column=day]')).toHaveAttribute('data-edited', 'true')

  // Undo forgets the edit.
  await page.getByRole('button', { name: `Undo edit of ${code}` }).click()
  await expect(page.getByText(/edits? waiting/)).toBeHidden()
})
