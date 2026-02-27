const REQUIRED_NODE_MAJOR = 22;
const RECOMMENDED_NODE_VERSION = '22.19.0';

function parseMajor(version) {
  const [majorToken] = version.split('.');
  return Number.parseInt(majorToken, 10);
}

const currentNodeVersion = process.versions.node;
const currentMajor = parseMajor(currentNodeVersion);
const commandName = process.argv[2] ?? 'this command';

if (Number.isNaN(currentMajor)) {
  console.error(`Unable to parse current Node.js version '${currentNodeVersion}'.`);
  process.exit(1);
}

if (process.env.QKNOT_SKIP_NODE_CHECK === '1') {
  process.exit(0);
}

if (currentMajor !== REQUIRED_NODE_MAJOR) {
  console.error(
    [
      `Unsupported Node.js version ${currentNodeVersion} for ${commandName}.`,
      `Q-Knot requires Node.js ${REQUIRED_NODE_MAJOR}.x to avoid front end toolchain instability.`,
      `Run 'nvm use ${RECOMMENDED_NODE_VERSION}' or install Node.js ${REQUIRED_NODE_MAJOR}.x.`,
      'Set QKNOT_SKIP_NODE_CHECK=1 to bypass this guard if you accept unsupported behavior.',
    ].join('\n'),
  );
  process.exit(1);
}
