import { expect, test, type Page } from '@playwright/test'
import { resolve } from 'node:path'

const FIXTURES = resolve(import.meta.dirname, '../../backend/tests/fixtures')

async function newDatasetWith(page: Page, name: string, file: string) {
  await page.goto('/')
  await expect(page.getByRole('option', { name: 'academic_weekly' })).toBeAttached()
  await page.getByLabel('Name').fill(name)
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name }).click()
  await page.getByRole('link', { name: 'Import / export' }).click()
  await page.getByLabel('Workbook file').setInputFiles(`${FIXTURES}/${file}`)
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(page.getByText('Imported.')).toBeVisible()
  await page.getByRole('link', { name: 'Tables' }).click()
}

test('a building is picked from the lookup while a room is typed', async ({ page }) => {
  await newDatasetWith(page, 'Lookup rooms', 'l6/l6.xlsx')
  await page.getByRole('tab', { name: 'Rooms', exact: true }).click()
  await page.getByLabel('New code (required)').fill('NEWROOM')

  // The lookup opens from the keyboard and shows the Buildings table, read-only.
  await page.getByLabel('New building', { exact: true }).focus()
  await page.keyboard.press('Control+Space')
  const drawer = page.getByRole('dialog', { name: 'New building' })
  await expect(drawer).toBeVisible()
  await expect(drawer.getByRole('columnheader', { name: 'campus' })).toBeVisible()
  await drawer.getByLabel('Search the table').fill('GP')
  await drawer.getByRole('row', { name: 'Choose GP' }).click()

  // A single field takes the code and the drawer closes. What was typed before is still there.
  await expect(drawer).toBeHidden()
  await expect(page.getByLabel('New building', { exact: true })).toHaveValue('GP')
  await expect(page.getByLabel('New code (required)')).toHaveValue('NEWROOM')

  await page.getByLabel('New room_type (required)').fill('lab')
  await page.getByLabel('New room_type (required)').press('Enter')
  const row = page.locator('[role=row][data-key="NEWROOM"]')
  await expect(row).toBeVisible()
  await expect(row.locator('[data-column=building]')).toHaveText('GP')
})

test('several modules are picked from the lookup for a teacher', async ({ page }) => {
  await newDatasetWith(page, 'Lookup teachers', 'l6-config/l6-config.xlsx')
  await page.getByRole('tab', { name: 'Teachers', exact: true }).click()
  await page.getByLabel('New code (required)').fill('LOOK1')

  await page.getByRole('button', { name: 'Look up New modules' }).click()
  const drawer = page.getByRole('dialog', { name: 'New modules' })
  await expect(drawer).toBeVisible()
  await drawer.getByRole('row', { name: 'Choose 6COSC020C' }).click()
  await drawer.getByRole('row', { name: 'Choose 6COSC021C' }).click()
  await expect(drawer).toBeVisible() // a list stays open for the next code
  await expect(page.getByRole('textbox', { name: 'New modules', exact: true })).toHaveValue(
    '6COSC020C;6COSC021C',
  )
  await expect(drawer.getByRole('row', { name: 'Choose 6COSC020C' })).toHaveAttribute(
    'aria-selected',
    'true',
  )

  // The first click again takes the code back out; Escape closes the drawer, not the entry row.
  await drawer.getByRole('row', { name: 'Choose 6COSC020C' }).click()
  await expect(page.getByRole('textbox', { name: 'New modules', exact: true })).toHaveValue(
    '6COSC021C',
  )
  await page.keyboard.press('Escape')
  await expect(drawer).toBeHidden()
  await expect(page.getByRole('textbox', { name: 'New modules', exact: true })).toHaveValue(
    '6COSC021C',
  )
  await expect(page.getByLabel('New code (required)')).toHaveValue('LOOK1')

  await page.getByRole('textbox', { name: 'New modules', exact: true }).press('Enter')
  await expect(page.locator('[role=row][data-key="LOOK1"]')).toBeVisible()
})
