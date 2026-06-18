// Browser E2E: login จริงผ่าน Chrome headless → admin-ui (localhost:3000)
// reuse puppeteer-core ที่มีอยู่ใน web-demos/node_modules
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const LOGIN_URL = 'http://localhost:3000/login';
const OUT = 'E:\\Claude-WorkSpace\\Project-intern\\user-test-demo\\login-e2e.png';
const log = (...a) => console.log(...a);

let browser;
try {
  browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  const apiResp = [];
  page.on('response', (r) => {
    if (r.url().includes('/api/v1/')) apiResp.push(`${r.status()} ${r.url().split('/api/v1')[1]}`);
  });

  await page.goto(LOGIN_URL, { waitUntil: 'networkidle2', timeout: 30000 });
  log('[1] login page:', page.url());

  await page.waitForSelector('#username', { timeout: 10000 });
  await page.type('#username', 'admin');
  await page.type('#password', 'ChangeMe123!');
  log('[2] typed credentials, submitting…');
  await page.click('button[type=submit]');

  let landed = false;
  try {
    await page.waitForFunction(() => location.pathname === '/', { timeout: 20000 });
    landed = true;
  } catch { landed = false; }
  await new Promise((r) => setTimeout(r, 1500)); // ให้ dashboard settle

  const token = await page.evaluate(() => localStorage.getItem('signage_access_token'));
  const errText = await page.evaluate(() => {
    const el = document.querySelector('[class*="rose-7"]');
    return el ? el.textContent.trim() : null;
  });
  const heading = await page.evaluate(() => (document.querySelector('h1,h2')?.textContent || '').trim());
  const finalUrl = page.url();

  await page.screenshot({ path: OUT, fullPage: true });

  log('[3] final url :', finalUrl);
  log('    pathname=/ :', landed);
  log('    token      :', token ? token.slice(0, 16) + '…' : 'NONE');
  log('    heading    :', heading);
  if (errText) log('    error shown:', errText);
  log('    api calls  :', apiResp.join(' | ') || '(none)');
  log('    screenshot :', OUT);

  const pass = landed && !!token && !finalUrl.endsWith('/login');
  log(pass ? 'LOGIN_E2E: PASS' : 'LOGIN_E2E: FAIL');
  await browser.close();
  process.exit(pass ? 0 : 2);
} catch (e) {
  log('LOGIN_E2E ERROR:', e.message);
  if (browser) await browser.close();
  process.exit(1);
}
