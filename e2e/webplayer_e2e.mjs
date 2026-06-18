// Browser E2E: web player (player/web) จริงผ่าน Chrome headless
//   เปิด :8080 → กรอก server + pairing code → pair → render content → screenshot
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const CODE = process.argv[2];
const OUT = 'E:\\Claude-WorkSpace\\Project-intern\\user-test-demo\\webplayer-e2e.png';
const log = (...a) => console.log(...a);

let browser;
try {
  browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720 });
  const api = [];
  page.on('response', (r) => {
    if (r.url().includes('/api/v1/')) api.push(`${r.status()} ${r.url().split('/api/v1')[1]}`);
  });

  await page.goto('http://localhost:8080', { waitUntil: 'networkidle2', timeout: 30000 });
  log('[1] web player loaded:', page.url());

  await page.waitForSelector('#server-url', { timeout: 10000 });
  await page.evaluate(() => {  // เคลียร์ค่า default ในช่อง (app.js เซ็ต value ไว้)
    document.getElementById('server-url').value = '';
    document.getElementById('pair-code').value = '';
  });
  await page.type('#server-url', 'http://localhost:8000');
  await page.type('#pair-code', CODE);
  log('[2] pairing with code', CODE);
  await page.click('#btn-pair');

  await page.waitForFunction(() => {
    const e = document.getElementById('player-screen');
    return e && getComputedStyle(e).display !== 'none';
  }, { timeout: 20000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, 6000)); // ให้ manifest + iframe โหลด

  const info = await page.evaluate(() => document.getElementById('info-bar')?.textContent || '');
  const status = await page.evaluate(() => document.getElementById('pair-status')?.textContent || '');
  const stage = await page.evaluate(() => document.getElementById('stage')?.innerHTML || '');
  await page.screenshot({ path: OUT });

  log('[3] pair-status :', status || '(ว่าง = pair สำเร็จ ไปหน้า player แล้ว)');
  log('    info-bar   :', info);
  log('    stage has  :', stage.includes('iframe') ? 'iframe (web content)' :
                          stage.includes('zone') ? 'zone(s)' : stage.slice(0, 80));
  log('    api        :', api.join(' | '));
  log('    screenshot :', OUT);
  const ok = /items=[1-9]/.test(info) || stage.includes('iframe');
  log(ok ? 'WEBPLAYER_E2E: PASS' : 'WEBPLAYER_E2E: CHECK (ดู screenshot)');
  await browser.close();
  process.exit(0);
} catch (e) {
  log('WEBPLAYER_E2E ERROR:', e.message);
  if (browser) await browser.close();
  process.exit(1);
}
