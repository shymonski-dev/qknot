import { expect } from 'vitest';
import * as matchers from '@testing-library/jest-dom/matchers';

expect.extend(matchers);

function createMemoryStorage(): Storage {
  const store = new Map<string, string>();

  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key)! : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(String(key), String(value));
    },
  };
}

function installStorageShim(storageName: 'localStorage' | 'sessionStorage') {
  const candidate = (globalThis as Record<string, unknown>)[storageName] as Partial<Storage> | undefined;
  if (
    candidate
    && typeof candidate.getItem === 'function'
    && typeof candidate.setItem === 'function'
    && typeof candidate.removeItem === 'function'
    && typeof candidate.clear === 'function'
  ) {
    return;
  }

  const shim = createMemoryStorage();
  try {
    Object.defineProperty(globalThis, storageName, {
      configurable: true,
      value: shim,
    });
  } catch {
    (globalThis as Record<string, unknown>)[storageName] = shim;
  }
}

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

installStorageShim('localStorage');
installStorageShim('sessionStorage');

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = ResizeObserverMock as typeof ResizeObserver;
}
