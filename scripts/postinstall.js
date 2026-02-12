#!/usr/bin/env node
/**
 * Post-install script to set up Python dependencies
 */

const { spawn } = require('child_process');
const path = require('path');

const isWin = process.platform === 'win32';
const pythonCmd = isWin ? 'python' : 'python3';

function runCommand(cmd, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      stdio: 'inherit',
      ...options
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Command failed with code ${code}`));
      }
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
}

async function install() {
  const packageDir = path.join(__dirname, '..');

  console.log('Installing Python dependencies...');

  try {
    // Try installing with --user first
    await runCommand(pythonCmd, ['-m', 'pip', 'install', '-e', packageDir, '--user']);
    console.log('Python package installed successfully (user mode)');
  } catch (err) {
    console.log('User install failed, trying system install...');
    try {
      await runCommand(pythonCmd, ['-m', 'pip', 'install', '-e', packageDir]);
      console.log('Python package installed successfully (system mode)');
    } catch (err2) {
      console.error('Failed to install Python package. Please install manually:');
      console.error(`  cd "${packageDir}" && pip install -e .`);
      // Don't fail npm install, just warn
      process.exit(0);
    }
  }
}

install().catch((err) => {
  console.error('Warning: Python setup failed:', err.message);
  console.error('You may need to install manually.');
  process.exit(0); // Don't fail npm install
});
