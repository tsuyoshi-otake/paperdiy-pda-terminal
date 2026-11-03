// Renders docs/images/render_*.png from the STLs in cad/out (three.js in headless Chromium).
//   cd docs/render && npm ci && npx playwright install chromium && npm run render
//   node render.js exploded      # just one view (open, closed, back, exploded, hinge)
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');

const HERE = __dirname;
const REPO = path.resolve(HERE, '..', '..');
const OUT = path.join(REPO, 'docs', 'images');

function resolve(url) {
  const p = decodeURIComponent(url.split('?')[0]);
  if (p === '/' || p === '/index.html') return path.join(HERE, 'index.html');
  if (p.startsWith('/models/')) return path.join(REPO, 'cad', 'out', path.basename(p));
  if (p.startsWith('/node_modules/')) return path.join(HERE, p);
  return null;
}
const types = { '.html': 'text/html', '.js': 'text/javascript', '.stl': 'application/octet-stream', '.json': 'application/json' };

(async () => {
  const server = http.createServer((req, res) => {
    const f = resolve(req.url);
    if (!f || !fs.existsSync(f)) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  }).listen(0, '127.0.0.1');
  await new Promise(r => server.once('listening', r));
  const port = server.address().port;

  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const sizes = { open: [1600, 1000], closed: [1600, 1000], back: [1600, 1000], exploded: [1500, 1500], hinge: [1600, 1000] };
  const views = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(sizes);
  for (const view of views) {
    const [w, h] = sizes[view];
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 });
    page.on('pageerror', e => console.error(view, e.message));
    await page.goto(`http://127.0.0.1:${port}/index.html?view=${view}`);
    await page.waitForFunction(() => document.title === 'ready', null, { timeout: 180000 });
    const file = path.join(OUT, `render_${view}_raw.png`);
    await page.screenshot({ path: file });
    console.log('wrote', file);
    await page.close();
  }
  await browser.close();
  server.close();
})();
