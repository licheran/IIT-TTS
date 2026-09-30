import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const L6 = resolve(import.meta.dirname, '../../backend/tests/fixtures/l6/l6.xlsx')

test('L6: import, edit a room, pre-flight, solve, view a grid and export it', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('API: ok')).toBeVisible()
  await expect(page.getByRole('option', { name: 'academic_weekly' })).toBeAttached()

  // A dataset from the academic preset.
  await page.getByLabel('Name').fill('L6 SE + CS')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'L6 SE + CS' }).click()

  // Import the workbook.
  await page.getByRole('link', { name: 'Import / export' }).click()
  await page.getByLabel('Workbook file').setInputFiles(L6)
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(page.getByText('Imported.')).toBeVisible()

  // Edit a room's capacity in the table.
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Rooms' }).click()
  const firstRow = page.locator('[role=row][data-key]').first()
  await firstRow.locator('[data-column=capacity]').dblclick()
  const editor = page.getByLabel(/^capacity of /)
  await editor.fill('321')
  await editor.press('Enter')
  await expect(firstRow.locator('[data-column=capacity]')).toHaveText('321')

  // Pre-flight finds nothing.
  await page.getByRole('link', { name: 'Pre-flight' }).click()
  await expect(page.getByText('No problems found')).toBeVisible()

  // Start a run and wait for the timetable.
  await page.getByRole('link', { name: 'Run', exact: true }).click()
  await page.getByLabel('Time limit (seconds)').fill('30')
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByRole('status').filter({ hasText: /^succeeded$/ })).toBeVisible({
    timeout: 90_000,
  })

  // The week of one group.
  await page.getByRole('link', { name: 'Open the timetable' }).click()
  await page.getByLabel('Resource', { exact: true }).selectOption('L6 SE / G1')
  const week = page.getByRole('table', { name: 'Week of L6 SE / G1' })
  await expect(week).toBeVisible()
  expect(await week.getByRole('cell').count()).toBeGreaterThan(3)

  // Export it as HTML.
  const download = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Export this grid (HTML)' }).click()
  const file = await (await download).path()
  const html = readFileSync(file, 'utf-8')
  expect(html).toContain('L6 SE / G1')
  expect(html).toContain('class="event"')
})
