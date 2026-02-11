#!/usr/bin/env node
// Start frontend directly without turbo
const { spawn } = require('child_process');

const frontendDir = `${__dirname}/apps/frontend`;

console.log('Starting Next.js frontend directly...');
console.log('Directory:', frontendDir);

const nextPath = `${frontendDir}/node_modules/.bin/next`;

spawn(nextPath, ['dev', '--port', '3000'], {
  cwd: frontendDir,
  stdio: 'inherit',
  env: { ...process.env, SKIP_TURBO: '1' }
});
