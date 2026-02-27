import { ensureBackendRuntime } from './backend-runtime.mjs';

const forceInstall = process.argv.includes('--force-install');

try {
  const { venvPython } = ensureBackendRuntime({ forceInstall });
  console.log(`Backend runtime is ready. Python executable: ${venvPython}`);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Failed to prepare backend runtime: ${message}`);
  process.exit(1);
}
