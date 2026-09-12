const { spawn } = require('child_process');
const path = require('path');

console.log("\x1b[34m%s\x1b[0m", "==================================================");
console.log("\x1b[32m%s\x1b[0m", "🚀 Starting Gap2Grow – Learning Resource Agent");
console.log("\x1b[34m%s\x1b[0m", "==================================================");

// Start Python Backend
const backend = spawn('python', ['-m', 'uvicorn', 'main:app', '--port', '8000', '--reload'], {
  cwd: path.join(__dirname, 'backend'),
  stdio: 'inherit',
  shell: true
});

// Start Frontend Dev Server
const frontend = spawn('npm', ['run', 'dev'], {
  cwd: path.join(__dirname, 'frontend'),
  stdio: 'inherit',
  shell: true
});

process.on('SIGINT', () => {
  backend.kill();
  frontend.kill();
  process.exit();
});
