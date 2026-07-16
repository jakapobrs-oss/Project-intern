// ถ่ายรูปเล่มรายงาน บทที่ 4 — Admin UI 10 หน้า (รูป 4.1–4.10)
//   login admin → ไล่ถ่ายทีละหน้า viewport 1440x900 @2x (คมพอสำหรับงานพิมพ์)
// ต้องมี: stack รันอยู่ (:3000/:8000) + ควรรัน book_player_shots.mjs ก่อน
//   เพื่อให้หน้า Devices มีจอ online และหน้า Emergency มีประวัติประกาศ
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE = 'http://localhost:3000';
const OUT_DIR = 'E:\\Claude-WorkSpace\\Project-intern\\project-book-prep\\assets\\ch4';
const log = (...a) => console.log(...a);

// [เลขรูป, path, ชื่อไฟล์]
const PAGES = [
  ['4.3', '/contents', 'fig-4-03-contents'],
  ['4.4', '/presentations', 'fig-4-04-presentations'],
  ['4.5', '/plans', 'fig-4-05-plans'],
  ['4.6', '/schedules', 'fig-4-06-schedules'],
  ['4.7', '/devices', 'fig-4-07-devices'],
  ['4.8', '/tv-control', 'fig-4-08-tv-control'],
  ['4.9', '/emergency', 'fig-4-09-emergency'],
  ['4.10', '/audit', 'fig-4-10-audit'],
];

let browser;
try {
  browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });

  // ── 4.1 หน้า login (กรอกฟอร์มแล้ว ก่อน submit) ──
  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle2', timeout: 60000 });
  await page.waitForSelector('#username', { timeout: 15000 });
  await page.type('#username', 'admin');
  await page.type('#password', 'ChangeMe123!');
  await page.screenshot({ path: `${OUT_DIR}\\fig-4-01-login.png` });
  log('SHOT 4.1 login');

  // ── 4.2 dashboard ──
  await page.click('button[type=submit]');
  await page.waitForFunction(() => location.pathname === '/', { timeout: 30000 });
  await new Promise((r) => setTimeout(r, 3000)); // ให้การ์ด/ตัวเลขบน dashboard โหลดครบ
  await page.screenshot({ path: `${OUT_DIR}\\fig-4-02-dashboard.png` });
  const heading = await page.evaluate(() => (document.querySelector('h1,h2')?.textContent || '').trim());
  log('SHOT 4.2 dashboard | heading:', heading);

  // ── 4.3–4.10 ไล่ทีละหน้า ──
  for (const [num, path, name] of PAGES) {
    await page.goto(BASE + path, { waitUntil: 'networkidle2', timeout: 60000 });
    await new Promise((r) => setTimeout(r, 2500)); // ให้ตาราง/ข้อมูล settle
    const h = await page.evaluate(() => (document.querySelector('h1,h2')?.textContent || '').trim());
    await page.screenshot({ path: `${OUT_DIR}\\${name}.png` });
    log(`SHOT ${num} ${path} | heading: ${h}`);
  }

  await browser.close();
  log('ADMIN_SHOTS: PASS (10 รูป)');
  process.exit(0);
} catch (e) {
  log('ADMIN_SHOTS ERROR:', e.message);
  if (browser) await browser.close();
  process.exit(1);
}
