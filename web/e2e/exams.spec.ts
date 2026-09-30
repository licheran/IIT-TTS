import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'

const EXAMS = resolve(import.meta.dirname, '../../backend/tests/fixtures/exams/exams.xlsx')

test('the exams preset shows its own words and timetables', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('option', { name: 'exams' })).toBeAttached()
  await page.getByLabel('Name').fill('June exams')
  await page.getByLabel('Preset').selectOption('exams')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'June exams' }).click()

  // The tables are the exams preset's sheets, with its labels.
  for (const tab of ['Exam days', 'Sessions', 'Cohorts', 'Halls', 'Invigilators', 'Exams']) {
    await expect(page.getByRole('tab', { name: tab, exact: true })).toBeVisible()
  }
  await expect(page.getByRole('tab', { name: 'Rooms' })).toHaveCount(0)

  await page.getByRole('link', { name: 'Import / export' }).click()
  await page.getByLabel('Workbook file').setInputFiles(EXAMS)
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(page.getByText('Imported.')).toBeVisible()

  await page.getByRole('link', { name: 'Run', exact: true }).click()
  await page.getByLabel('Time limit (seconds)').fill('20')
  await page.getByRole('button', { name: 'Start' }).click()
  await expect(page.getByRole('status').filter({ hasText: /^succeeded$/ })).toBeVisible({
    timeout: 90_000,
  })

  await page.getByRole('link', { name: 'Open the timetable' }).click()
  await expect(page.getByLabel('Resource type')).toHaveValue('Cohort')
  await expect(page.getByRole('option', { name: 'Invigilator' })).toBeAttached()
  await page.getByLabel('Resource', { exact: true }).selectOption('BSC-CS-1')
  const week = page.getByRole('table', { name: 'Week of BSC-CS-1' })
  await expect(week.getByRole('columnheader', { name: 'Mon 01 Jun' })).toBeVisible()
  await expect(week.getByRole('cell')).toHaveCount(5)
  await expect(week.getByText(/^Exam · /).first()).toBeVisible()
})
