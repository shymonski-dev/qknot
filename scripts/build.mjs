import { build } from 'vite';

const startTime = Date.now();

try {
  await build();
  const durationSeconds = ((Date.now() - startTime) / 1000).toFixed(2);
  console.log(`Build completed in ${durationSeconds}s.`);
  process.exitCode = 0;
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  // Work around leaked watcher handles in the local toolchain.
  setTimeout(() => {
    process.exit(process.exitCode ?? 0);
  }, 0);
}
