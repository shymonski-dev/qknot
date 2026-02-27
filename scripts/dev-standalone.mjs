import { spawn } from 'node:child_process';
import { ensureBackendRuntime, ROOT_DIR } from './backend-runtime.mjs';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const backendHost = process.env.QKNOT_BACKEND_HOST ?? '0.0.0.0';
const backendPort = process.env.QKNOT_BACKEND_PORT ?? '8000';

function spawnProcess(command, args) {
  return spawn(command, args, {
    cwd: ROOT_DIR,
    stdio: 'inherit',
    env: process.env,
  });
}

let backendProcess;
let frontendProcess;
let shuttingDown = false;

function shutdown(exitCode = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  if (frontendProcess && !frontendProcess.killed) {
    frontendProcess.kill('SIGTERM');
  }
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }

  setTimeout(() => {
    if (frontendProcess && !frontendProcess.killed) {
      frontendProcess.kill();
    }
    if (backendProcess && !backendProcess.killed) {
      backendProcess.kill();
    }
    process.exit(exitCode);
  }, 500).unref();
}

try {
  const { venvPython } = ensureBackendRuntime();

  backendProcess = spawnProcess(venvPython, [
    '-m',
    'uvicorn',
    'backend.main:app',
    '--host',
    backendHost,
    '--port',
    backendPort,
  ]);

  frontendProcess = spawnProcess(npmCommand, ['run', 'dev']);

  backendProcess.on('exit', (code, signal) => {
    if (shuttingDown) {
      return;
    }
    console.error(`Backend exited with code ${code ?? 'null'} and signal ${signal ?? 'none'}.`);
    shutdown(code ?? 1);
  });

  frontendProcess.on('exit', (code, signal) => {
    if (shuttingDown) {
      return;
    }
    console.error(`Frontend exited with code ${code ?? 'null'} and signal ${signal ?? 'none'}.`);
    shutdown(code ?? 1);
  });

  process.on('SIGINT', () => shutdown(0));
  process.on('SIGTERM', () => shutdown(0));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Failed to start standalone development environment: ${message}`);
  process.exit(1);
}
