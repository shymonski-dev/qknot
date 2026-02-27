import { spawnSync } from 'node:child_process';
import { ensureBackendRuntime, ROOT_DIR } from './backend-runtime.mjs';

try {
  const { venvPython } = ensureBackendRuntime();
  const result = spawnSync(
    venvPython,
    ['-m', 'unittest', 'discover', '-s', 'backend', '-p', 'test_*.py'],
    {
      cwd: ROOT_DIR,
      stdio: 'inherit',
    },
  );

  if (result.error) {
    throw result.error;
  }

  process.exit(result.status ?? 1);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Backend tests failed to start: ${message}`);
  process.exit(1);
}
