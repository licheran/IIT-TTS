import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'

// Not part of `pnpm e2e`. Run `pnpm wiki:shots` to redraw the pictures in docs/wiki/img/.
const FIXTURES = resolve(import.meta.dirname, '../../backend/tests/fixtures/l6')
const IMG = resolve(import.meta.dirname, '../../docs/wiki/img')

test.use({ viewport: { width: 1280, height: 800 } })

test('draw the wiki pictures', async ({ page }) => {
  const shot = (name: string) => page.screenshot({ path: `${IMG}/${name}.png` })
  const createDataset = async (name: string) => {
    await page.goto('/')
    await expect(page.getByRole('option', { name: 'academic_weekly' })).toBeAttached()
    await page.getByLabel('Name').fill(name)
    await expect(page.getByLabel('Name')).toHaveValue(name)
    await page.getByRole('button', { name: 'Create' }).click()
    await expect(page.getByRole('link', { name })).toBeVisible()
  }
  const importFile = async (file: string) => {
    await page.getByRole('link', { name: 'Import / export' }).click()
    await page.getByLabel('Workbook file').setInputFiles(`${FIXTURES}/${file}`)
    await page.getByRole('button', { name: 'Import', exact: true }).click()
    await expect(page.getByText('Imported.')).toBeVisible()
  }

  // Datasets
  await createDataset('L6 templates')
  await createDataset('L6 SE + CS')
  await shot('datasets')

  // Templates and Expand
  await page.getByRole('link', { name: 'L6 templates' }).click()
  await importFile('templates.xlsx')
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Templates', exact: true }).click()
  await page.getByRole('button', { name: 'Preview expansion' }).click()
  await expect(page.getByRole('dialog', { name: 'Expansion preview' })).toBeVisible()
  await shot('templates-expand')

  // The main dataset
  await page.goto('/')
  await page.getByRole('link', { name: 'L6 SE + CS' }).click()
  await importFile('l6.xlsx')
  await shot('import-export')

  // Tables, with the entry row
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Teachers', exact: true }).click()
  await expect(page.getByText(/^\d+ rows$/)).toBeVisible()
  await page.getByLabel('New code (required)').fill('NEW1')
  await page.keyboard.press('Tab')
  await page.keyboard.type('New teacher')
  await shot('tables')
  await page.keyboard.press('Escape')

  // Pre-flight
  await page.getByRole('link', { name: 'Pre-flight' }).click()
  await expect(page.getByText('No problems found')).toBeVisible()
  await shot('preflight')

  // Run
  await page.getByRole('link', { name: 'Run', exact: true }).click()
  await page.getByLabel('Time limit (seconds)').fill('30')
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByRole('status').filter({ hasText: /^succeeded$/ })).toBeVisible({
    timeout: 90_000,
  })
  await shot('run')

  // Timetable, with an event opened
  await page.getByRole('link', { name: 'Open the timetable' }).click()
  await page.getByLabel('Resource', { exact: true }).selectOption('L6 SE / G1')
  const week = page.getByRole('table', { name: 'Week of L6 SE / G1' })
  await expect(week).toBeVisible()
  await week.getByRole('cell').first().click()
  await expect(page.getByRole('complementary', { name: 'Event details' })).toBeVisible()
  await shot('timetable')

  // Runs, with the run published
  await page.getByRole('link', { name: 'Runs', exact: true }).click()
  await page.getByRole('button', { name: 'Publish' }).click()
  await expect(page.getByText('published')).toBeVisible()
  await shot('runs')
})
