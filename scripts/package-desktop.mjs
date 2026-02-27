import { chmodSync, existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { ensureBackendRuntime, ROOT_DIR, runInRoot } from './backend-runtime.mjs';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const releaseDir = path.join(ROOT_DIR, 'release');
const desktopDir = path.join(releaseDir, 'desktop');
const distDir = path.join(ROOT_DIR, 'dist');
const buildFrontend = process.env.QKNOT_PACKAGE_WITH_BUILD === '1';

const linuxLauncher = `#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_COMMAND="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND="python"
else
  echo "Python is required. Install Python 3.10, 3.11, or 3.12." >&2
  exit 1
fi

cd "$PROJECT_DIR"
exec "$PYTHON_COMMAND" scripts/start-standalone.py
`;

const macLauncher = `#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_COMMAND="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND="python"
else
  echo "Python is required. Install Python 3.10, 3.11, or 3.12." >&2
  exit 1
fi

cd "$PROJECT_DIR"
exec "$PYTHON_COMMAND" scripts/start-standalone.py
`;

const windowsLauncher = `@echo off
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\\..\\.."

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 scripts\\start-standalone.py
  goto :eof
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python scripts\\start-standalone.py
  goto :eof
)

echo Python is required. Install Python 3.10, 3.11, or 3.12.
exit /b 1
`;

const readme = `Q-Knot Desktop Launcher Bundle

Launch options:
- macOS: ./start-macos.command
- Linux: ./start-linux.sh
- Windows: start-windows.bat

The launchers call scripts/start-standalone.py from the project root.
`;

try {
  ensureBackendRuntime();
  if (buildFrontend) {
    runInRoot(npmCommand, ['run', 'build']);
  }
  if (!existsSync(distDir)) {
    throw new Error("Frontend distribution is missing. Run 'npm run build' first.");
  }

  rmSync(desktopDir, { recursive: true, force: true });
  mkdirSync(releaseDir, { recursive: true });
  mkdirSync(desktopDir, { recursive: true });
  writeFileSync(path.join(desktopDir, "start-linux.sh"), linuxLauncher);
  writeFileSync(path.join(desktopDir, "start-macos.command"), macLauncher);
  writeFileSync(path.join(desktopDir, "start-windows.bat"), windowsLauncher);
  writeFileSync(path.join(desktopDir, "README.txt"), readme);

  chmodSync(path.join(desktopDir, 'start-linux.sh'), 0o755);
  chmodSync(path.join(desktopDir, 'start-macos.command'), 0o755);

  console.log(`Desktop launchers created at ${desktopDir}`);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Failed to package desktop launchers: ${message}`);
  process.exit(1);
}
