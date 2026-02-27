import { chmodSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { ensureBackendRuntime, ROOT_DIR, runInRoot } from './backend-runtime.mjs';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const releaseDir = path.join(ROOT_DIR, 'release');
const desktopDir = path.join(releaseDir, 'desktop');
const buildFrontend = process.env.QKNOT_PACKAGE_WITH_BUILD === '1';

const linuxLauncher = `#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"
npm install
npm run start:standalone
`;

const macLauncher = `#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"
npm install
npm run start:standalone
`;

const windowsLauncher = `@echo off
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\\..\\.."
call npm install
call npm run start:standalone
`;

const readme = `Q-Knot Desktop Launcher Bundle

This folder contains launcher scripts that start Q-Knot with automatic backend setup.

Before first launch:
1. Install Node.js 22.x
2. Open a terminal in the project root once and run: npm install

Launch options:
- macOS: ./start-macos.command
- Linux: ./start-linux.sh
- Windows: start-windows.bat

The launcher starts the standalone runtime on http://localhost:8000
`;

try {
  ensureBackendRuntime();
  if (buildFrontend) {
    runInRoot(npmCommand, ['run', 'build']);
  }

  mkdirSync(desktopDir, { recursive: true });
  writeFileSync(path.join(desktopDir, 'start-linux.sh'), linuxLauncher);
  writeFileSync(path.join(desktopDir, 'start-macos.command'), macLauncher);
  writeFileSync(path.join(desktopDir, 'start-windows.bat'), windowsLauncher);
  writeFileSync(path.join(desktopDir, 'README.txt'), readme);

  chmodSync(path.join(desktopDir, 'start-linux.sh'), 0o755);
  chmodSync(path.join(desktopDir, 'start-macos.command'), 0o755);

  console.log(`Desktop launchers created at ${desktopDir}`);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Failed to package desktop launchers: ${message}`);
  process.exit(1);
}
