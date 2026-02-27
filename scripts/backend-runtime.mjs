import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptFile = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(scriptFile);
export const ROOT_DIR = path.resolve(scriptDir, '..');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const BACKEND_VENV_DIR = path.join(BACKEND_DIR, '.venv');
const BACKEND_REQUIREMENTS = path.join(BACKEND_DIR, 'requirements.txt');
const REQUIREMENTS_HASH_MARKER = path.join(BACKEND_VENV_DIR, '.requirements.sha256');
const SUPPORTED_PYTHON_MINORS = new Set([10, 11, 12]);

function runOrThrow(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT_DIR,
    stdio: 'inherit',
    ...options,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(`Command failed: ${command} ${args.join(' ')}`);
  }
}

function canRun(command, args) {
  const result = spawnSync(command, args, {
    cwd: ROOT_DIR,
    stdio: 'pipe',
    encoding: 'utf8',
  });
  return result.status === 0;
}

function readPythonVersion(command, args) {
  const result = spawnSync(command, [...args, '-c', 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")'], {
    cwd: ROOT_DIR,
    stdio: 'pipe',
    encoding: 'utf8',
  });

  if (result.status !== 0 || result.error) {
    return null;
  }

  const text = result.stdout.trim();
  const parts = text.split('.');
  if (parts.length !== 2) {
    return null;
  }

  const major = Number.parseInt(parts[0], 10);
  const minor = Number.parseInt(parts[1], 10);
  if (Number.isNaN(major) || Number.isNaN(minor)) {
    return null;
  }

  return { major, minor };
}

function isSupportedVersion(version) {
  return version.major === 3 && SUPPORTED_PYTHON_MINORS.has(version.minor);
}

export function resolvePythonCommand() {
  const envPython = process.env.QKNOT_PYTHON?.trim();
  const candidates = [];

  if (envPython) {
    candidates.push({ command: envPython, prefixArgs: [] });
  } else {
    if (process.platform === 'win32') {
      candidates.push({ command: 'py', prefixArgs: ['-3.12'] });
      candidates.push({ command: 'py', prefixArgs: ['-3.11'] });
      candidates.push({ command: 'py', prefixArgs: ['-3.10'] });
      candidates.push({ command: 'py', prefixArgs: ['-3'] });
      candidates.push({ command: 'python', prefixArgs: [] });
    } else {
      candidates.push({ command: 'python3.12', prefixArgs: [] });
      candidates.push({ command: 'python3.11', prefixArgs: [] });
      candidates.push({ command: 'python3.10', prefixArgs: [] });
      candidates.push({ command: 'python3', prefixArgs: [] });
      candidates.push({ command: 'python', prefixArgs: [] });
    }
  }

  const seen = new Set();
  const discoveredVersions = [];

  for (const candidate of candidates) {
    const key = `${candidate.command} ${candidate.prefixArgs.join(' ')}`.trim();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);

    if (!canRun(candidate.command, [...candidate.prefixArgs, '--version'])) {
      continue;
    }

    const version = readPythonVersion(candidate.command, candidate.prefixArgs);
    if (!version) {
      continue;
    }

    discoveredVersions.push(`${key} -> ${version.major}.${version.minor}`);
    if (isSupportedVersion(version)) {
      return {
        ...candidate,
        version,
      };
    }
  }

  if (discoveredVersions.length > 0) {
    throw new Error(
      `Supported Python versions are 3.10, 3.11, and 3.12. Found: ${discoveredVersions.join(', ')}. ` +
      'Install a supported version or set QKNOT_PYTHON to one.',
    );
  }

  throw new Error(
    'Python was not found. Install Python 3.10 to 3.12, or set QKNOT_PYTHON to a Python executable.',
  );
}

function resolveVirtualEnvironmentPython(venvDir) {
  if (process.platform === 'win32') {
    return path.join(venvDir, 'Scripts', 'python.exe');
  }
  return path.join(venvDir, 'bin', 'python');
}

function hashFile(filePath) {
  const content = readFileSync(filePath);
  return createHash('sha256').update(content).digest('hex');
}

export function ensureBackendRuntime({ forceInstall = false } = {}) {
  const python = resolvePythonCommand();
  const existingVenvPython = resolveVirtualEnvironmentPython(BACKEND_VENV_DIR);

  if (existsSync(BACKEND_VENV_DIR) && existsSync(existingVenvPython)) {
    const venvVersion = readPythonVersion(existingVenvPython, []);
    if (!venvVersion || !isSupportedVersion(venvVersion)) {
      console.log('Recreating backend virtual environment with a supported Python version...');
      rmSync(BACKEND_VENV_DIR, { recursive: true, force: true });
    }
  }

  if (!existsSync(BACKEND_VENV_DIR)) {
    console.log('Creating backend virtual environment...');
    runOrThrow(python.command, [...python.prefixArgs, '-m', 'venv', BACKEND_VENV_DIR]);
  }

  const venvPython = resolveVirtualEnvironmentPython(BACKEND_VENV_DIR);
  if (!existsSync(venvPython)) {
    throw new Error(`Python virtual environment is missing executable at ${venvPython}`);
  }

  const requirementsHash = hashFile(BACKEND_REQUIREMENTS);
  const installedHash = existsSync(REQUIREMENTS_HASH_MARKER)
    ? readFileSync(REQUIREMENTS_HASH_MARKER, 'utf8').trim()
    : '';

  if (forceInstall || requirementsHash !== installedHash) {
    console.log('Installing backend dependencies...');
    runOrThrow(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip']);
    runOrThrow(venvPython, ['-m', 'pip', 'install', '-r', BACKEND_REQUIREMENTS]);
    writeFileSync(REQUIREMENTS_HASH_MARKER, requirementsHash);
  } else {
    console.log('Backend dependencies are up to date.');
  }

  return {
    backendDir: BACKEND_DIR,
    venvPython,
  };
}

export function runInRoot(command, args, options = {}) {
  runOrThrow(command, args, options);
}
