import { execSync, spawn } from 'node:child_process'
import { rmSync } from 'node:fs'
import { resolve } from 'node:path'

const backend = resolve(import.meta.dirname, '../../backend')

/**
 * Run the worker that solves the runs, on the run's own database (`E2E_DB`, see the config).
 */
export default function globalSetup() {
  const worker = spawn('uv', ['run', 'python', '-m', 'tts.worker.main'], {
    cwd: backend,
    env: { ...process.env, TT_DATABASE_URL: `sqlite:///${process.env.E2E_DB}` },
    stdio: 'ignore',
    shell: true,
  })
  return () => {
    if (worker.pid !== undefined) {
      if (process.platform === 'win32') {
        try {
          execSync(`taskkill /pid ${worker.pid} /T /F`, { stdio: 'ignore' })
        } catch {
          // already gone
        }
      } else {
        worker.kill()
      }
    }
    // The API may still hold the file for a moment, so a leftover is only a nuisance.
    for (const suffix of ['', '-wal', '-shm']) {
      try {
        rmSync(resolve(backend, `${process.env.E2E_DB}${suffix}`), { force: true })
      } catch {
        // still in use
      }
    }
  }
}
