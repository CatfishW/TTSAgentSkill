#!/usr/bin/env node
/**
 * Text2Speech Skill - Node.js wrapper for Python CLI
 *
 * This module provides a Node.js interface to the Text2Speech Python backend.
 */

const { spawn } = require('child_process');
const path = require('path');

const isWin = process.platform === 'win32';
const pythonCmd = isWin ? 'python' : 'python3';
const cliPath = path.join(__dirname, 'text2speech_skill', 'cli.py');

/**
 * Check if Python skill is installed
 * @returns {Promise<boolean>}
 */
async function isInstalled() {
  return new Promise((resolve) => {
    const child = spawn(pythonCmd, ['-c', 'import text2speech_skill'], {
      stdio: 'ignore'
    });

    child.on('close', (code) => {
      resolve(code === 0);
    });

    child.on('error', () => {
      resolve(false);
    });

    setTimeout(() => {
      child.kill();
      resolve(false);
    }, 3000);
  });
}

/**
 * Install Python package with fallback strategies
 * @returns {Promise<void>}
 */
async function installPythonPackage() {
  const strategies = [
    // Strategy 1: User install (works on most systems)
    ['-m', 'pip', 'install', '--user', '-e', __dirname],
    // Strategy 2: User install with break-system-packages (for PEP 668)
    ['-m', 'pip', 'install', '--user', '--break-system-packages', '-e', __dirname],
    // Strategy 3: Just break-system-packages (fallback)
    ['-m', 'pip', 'install', '--break-system-packages', '-e', __dirname],
  ];

  let lastError = null;

  for (let i = 0; i < strategies.length; i++) {
    const args = strategies[i];
    console.log(`Setting up Python dependencies (attempt ${i + 1}/${strategies.length})...`);

    try {
      await new Promise((resolve, reject) => {
        const installCmd = spawn(pythonCmd, args, { stdio: 'inherit' });

        installCmd.on('close', (code) => {
          if (code === 0) {
            resolve();
          } else {
            reject(new Error(`pip install failed with code ${code}`));
          }
        });

        installCmd.on('error', (err) => {
          reject(err);
        });
      });
      // Success!
      return;
    } catch (err) {
      lastError = err;
      // Try next strategy
    }
  }

  // All strategies failed
  console.error('\n⚠️  Could not auto-install Python package.');
  console.error('\nManual installation options:');
  console.error('1. Using pip with --break-system-packages:');
  console.error(`   ${pythonCmd} -m pip install --break-system-packages -e "${__dirname}"`);
  console.error('');
  console.error('2. Using a virtual environment:');
  console.error(`   ${pythonCmd} -m venv ~/.venv/text2speech`);
  console.error(`   source ~/.venv/text2speech/bin/activate`);
  console.error(`   pip install -e "${__dirname}"`);
  console.error('');
  console.error('3. On macOS with Homebrew Python, you may need to:');
  console.error('   brew install pipx');
  console.error(`   pipx run --spec "${__dirname}" text2speech`);
  console.error('');
  throw lastError;
}

/**
 * Execute text2speech command
 * @param {string[]} args - Command line arguments
 * @returns {Promise<{stdout: string, stderr: string, exitCode: number}>}
 */
async function text2speech(args = []) {
  // Check if installed, if not try to install
  const installed = await isInstalled();
  if (!installed) {
    try {
      await installPythonPackage();
    } catch (err) {
      console.error('Failed to auto-install Python package.');
      console.error('Please run: pip install -e ' + __dirname);
      throw err;
    }
  }

  return new Promise((resolve, reject) => {
    const child = spawn(pythonCmd, [cliPath, ...args], {
      stdio: ['inherit', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => {
      stdout += data.toString();
      process.stdout.write(data);
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
      process.stderr.write(data);
    });

    child.on('close', (exitCode) => {
      resolve({ stdout, stderr, exitCode });
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
}

// If run directly as CLI
const isMainModule = require.main === module;
const isBinEntry = require.main && require.main.filename && require.main.filename.includes('text2speech');
if (isMainModule || isBinEntry) {
  const args = process.argv.slice(2);
  text2speech(args).then((result) => {
    process.exit(result.exitCode);
  }).catch((err) => {
    console.error('Error:', err.message);
    process.exit(1);
  });
}

module.exports = {
  text2speech,
  isInstalled
};
