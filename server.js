const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const workspaceRoot = path.resolve(__dirname);
const defaultPython = path.join(workspaceRoot, '.venv-1', 'Scripts', 'python.exe');
const pythonExecutable = process.env.PYTHON || (fs.existsSync(defaultPython) ? defaultPython : 'python');

console.log('[server.js] Starting AgriVision live telemetry backend...');

const child = spawn(pythonExecutable, ['live_prediction.py'], {
  cwd: workspaceRoot,
  stdio: 'inherit',
  shell: false,
});

child.on('error', (error) => {
  console.error('[server.js] Failed to start telemetry backend:', error.message);
  process.exit(1);
});

child.on('exit', (code) => {
  console.log(`[server.js] Telemetry backend exited with code ${code}`);
  process.exit(code ?? 0);
});
