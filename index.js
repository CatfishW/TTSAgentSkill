#!/usr/bin/env node
/**
 * Text2Speech Skill - Node.js wrapper for Python CLI
 *
 * This module provides a Node.js interface to the Text2Speech Python backend.
 */

const { spawn } = require('child_process');
const path = require('path');

/**
 * Execute text2speech command
 * @param {string[]} args - Command line arguments
 * @returns {Promise<{stdout: string, stderr: string, exitCode: number}>}
 */
function text2speech(args = []) {
  return new Promise((resolve, reject) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const cliPath = path.join(__dirname, 'text2speech_skill', 'cli.py');

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

/**
 * Check if Python skill is installed
 * @returns {Promise<boolean>}
 */
async function isInstalled() {
  try {
    const { spawn } = require('child_process');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

    return new Promise((resolve) => {
      const child = spawn(pythonCmd, ['-m', 'text2speech_skill.cli', '--help'], {
        stdio: 'ignore'
      });

      child.on('close', (code) => {
        resolve(code === 0);
      });

      child.on('error', () => {
        resolve(false);
      });

      // Timeout after 5 seconds
      setTimeout(() => {
        child.kill();
        resolve(false);
      }, 5000);
    });
  } catch {
    return false;
  }
}

module.exports = {
  text2speech,
  isInstalled
};
