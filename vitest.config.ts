import { defineConfig } from 'vitest/config';

const REQUIRED_NODE_MAJOR = 22;
const detectedNodeMajor = Number.parseInt(process.versions.node.split('.')[0] ?? '', 10);

if (
  process.env.QKNOT_SKIP_NODE_CHECK !== '1'
  && (Number.isNaN(detectedNodeMajor) || detectedNodeMajor !== REQUIRED_NODE_MAJOR)
) {
  throw new Error(
    [
      `Unsupported Node.js version ${process.versions.node} for vitest.`,
      `Q-Knot front end tests require Node.js ${REQUIRED_NODE_MAJOR}.x.`,
      "Run 'nvm use 22.19.0' before invoking vitest directly.",
      'Set QKNOT_SKIP_NODE_CHECK=1 to bypass this guard if needed.',
    ].join('\n'),
  );
}

export default defineConfig({
  esbuild: {
    target: 'es2022',
    jsx: 'automatic',
    tsconfigRaw: {
      compilerOptions: {
        target: 'ES2022',
        module: 'ESNext',
        moduleResolution: 'Node',
        jsx: 'react-jsx',
        types: ['vitest/globals', '@testing-library/jest-dom'],
      },
    },
  },
  test: {
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['backend/**', 'dist/**'],
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
      },
    },
    clearMocks: true,
    restoreMocks: true,
    unstubGlobals: true,
    testTimeout: 15_000,
    hookTimeout: 15_000,
  },
});
