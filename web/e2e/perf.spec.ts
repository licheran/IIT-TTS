import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const ROWS = 5000 // extra teachers; L6 adds 57 more

// NFR-8: the table editor stays responsive with 5,000 rows. The method is described in
// docs/STATUS.md (P7.10): scroll the grid as fast as the browser lets us and record every frame
// time, then time a sort and a cell edit.
test(`the table editor stays responsive with ${ROWS} rows`, async ({ page }) => {
  const dir = mkdtempSync(join(tmpdir(), 'tts-perf-'))
  const workbook = join(dir, 'big.xlsx')
  execFileSync('uv', ['run', 'python', 'tests/scale/editor_workbook.py', workbook, String(ROWS)], {
    cwd: resolve(import.meta.dirname, '../../backend'),
    stdio: 'ignore',
    shell: process.platform === 'win32',
  })

  await page.goto('/')
  await expect(page.getByRole('option', { name: 'academic_weekly' })).toBeAttached()
  await page.getByLabel('Name').fill('Perf')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'Perf' }).click()
  await page.getByRole('link', { name: 'Import / export' }).click()
  await page.getByLabel('Workbook file').setInputFiles(workbook)
  await page.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(page.getByText('Imported.')).toBeVisible({ timeout: 60_000 })

  // Loading the sheet.
  const loadStart = Date.now()
  await page.getByRole('link', { name: 'Tables' }).click()
  await page.getByRole('tab', { name: 'Teachers', exact: true }).click()
  await expect(page.getByText(/^\d+ rows$/)).toContainText(String(ROWS + 57), { timeout: 30_000 })
  const loadMs = Date.now() - loadStart

  // Scrolling: 2 seconds of steady scrolling, every frame timed.
  const frames = await page.evaluate(async () => {
    const grid = document.querySelector('[role=grid]') as HTMLElement
    const times: number[] = []
    let last = performance.now()
    const end = last + 2000
    await new Promise<void>((done) => {
      const step = (now: number) => {
        times.push(now - last)
        last = now
        grid.scrollTop += 600
        if (now < end) requestAnimationFrame(step)
        else done()
      }
      requestAnimationFrame(step)
    })
    return times.slice(1)
  })
  const sorted = [...frames].sort((a, b) => a - b)
  const p95 = sorted[Math.floor(sorted.length * 0.95)] ?? 0
  const worst = sorted[sorted.length - 1] ?? 0

  // Sorting 5,000 rows.
  const sortStart = Date.now()
  await page.getByRole('button', { name: /^code/ }).click()
  await page.getByRole('button', { name: /^code/ }).click()
  await expect(page.locator('[role=row][data-key]').first()).toHaveAttribute(
    'data-key',
    /^T|^E|^[A-Z]/,
  )
  const sortMs = Date.now() - sortStart

  // Editing a cell: from Enter to the new value on screen.
  await page.getByRole('button', { name: /^code/ }).click() // ascending again
  await page.evaluate(() => {
    ;(document.querySelector('[role=grid]') as HTMLElement).scrollTop = 0
  })
  const cell = page.locator('[role=row][data-key]').first().locator('[data-column=name]')
  await cell.dblclick()
  const editor = page.getByLabel(/^name of /)
  await editor.fill('Renamed in the perf test')
  const editStart = Date.now()
  await editor.press('Enter')
  await expect(cell).toHaveText('Renamed in the perf test')
  const editMs = Date.now() - editStart

  console.log(
    `PERF rows=${ROWS} load=${loadMs}ms scroll: frames=${frames.length} p95=${p95.toFixed(1)}ms ` +
      `worst=${worst.toFixed(1)}ms sort=${sortMs}ms edit=${editMs}ms`,
  )
  expect(p95).toBeLessThan(50)
  expect(worst).toBeLessThan(250)
  expect(sortMs).toBeLessThan(1500)
  expect(editMs).toBeLessThan(500)
  expect(loadMs).toBeLessThan(8000)
})
