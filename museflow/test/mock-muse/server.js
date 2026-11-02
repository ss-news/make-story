// Mock Muse chat page for testing MuseFlow Desktop without a real account.
// Run: node test/mock-muse/server.js  then start the app with MUSEFLOW_MUSE_HOME=http://127.0.0.1:4777/
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const page = fs.readFileSync(path.join(__dirname, 'index.html'));
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(page);
}).listen(Number(process.env.PORT) || 4777, '127.0.0.1', () => console.log('mock muse on http://127.0.0.1:4777/'));
