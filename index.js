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
 * Install Python package
 * @returns {Promise<void>}
 */
async function installPythonPackage() {
  return new Promise((resolve, reject) => {
    console.log('Setting up Python dependencies...');

    const installCmd = spawn(pythonCmd, ['-m', 'pip', 'install', '-e', __dirname], {
      stdio: 'inherit'
    });

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
