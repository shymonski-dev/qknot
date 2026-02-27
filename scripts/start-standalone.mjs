import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { ensureBackendRuntime, ROOT_DIR, runInRoot } from './backend-runtime.mjs';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const backendHost = process.env.QKNOT_BACKEND_HOST ?? '0.0.0.0';
const backendPort = process.env.QKNOT_BACKEND_PORT ?? '8000';
const distIndex = path.join(ROOT_DIR, 'dist', 'index.html');
const forceBuild = process.env.QKNOT_FORCE_FRONTEND_BUILD === '1';

let backendProcess;
let shuttingDown = false;

function shutdown(exitCode = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }

  setTimeout(() => {
    if (backendProcess && !backendProcess.killed) {
      backendProcess.kill();
    }
    process.exit(exitCode);
  }, 500).unref();
}

try {
  const { venvPython } = ensureBackendRuntime();

  if (forceBuild || !existsSync(distIndex)) {
    console.log('Building frontend distribution for standalone runtime...');
    runInRoot(npmCommand, ['run', 'build']);
  }

  console.log(`Starting standalone runtime on http://localhost:${backendPort}`);
  backendProcess = spawn(
    venvPython,
    [
      '-m',
      'uvicorn',
      'backend.main:app',
      '--host',
      backendHost,
      '--port',
      backendPort,
    ],
    {
      cwd: ROOT_DIR,
      stdio: 'inherit',
      env: {
        ...process.env,
        QKNOT_SERVE_FRONTEND: '1',
      },
    },
  );

  backendProcess.on('exit', (code, signal) => {
    if (shuttingDown) {
      return;
    }
    console.error(`Standalone backend exited with code ${code ?? 'null'} and signal ${signal ?? 'none'}.`);
    shutdown(code ?? 1);
  });

  process.on('SIGINT', () => shutdown(0));
  process.on('SIGTERM', () => shutdown(0));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Failed to start standalone runtime: ${message}`);
  process.exit(1);
}
