// ถ่ายรูปเล่มรายงาน บทที่ 4 — Player 2 รูป
//   รูป 4.11 player แสดงผลปกติ (paired + render content ตาม schedule)
//   รูป 4.12 player แสดง emergency overlay
// เตรียมการ: สร้าง device ชื่อไทย → เข้ากลุ่ม "ทุกจอใน demo" (มี schedule active อยู่แล้ว)
//   → pair ผ่านหน้า pairing จริง → ถ่ายปกติ → สร้าง+activate emergency → reload (บังคับดึง manifest)
//   → ถ่าย overlay → cancel emergency ทิ้ง (device เก็บไว้ ให้หน้า Devices มีจอ online)
// ต้องมี: stack รันอยู่ (:8000) + http.server เสิร์ฟ player/web ที่ :8080
import puppeteer from 'puppeteer-core';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const API = 'http://localhost:8000';
const OUT_DIR = 'E:\\Claude-WorkSpace\\Project-intern\\project-book-prep\\assets\\ch4';
const DEVICE_NAME = 'จอประชาสัมพันธ์ OPD';
const log = (...a) => console.log(...a);

async function api(method, path, body, token, form = false) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (body !== undefined) {
    if (form) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
      payload = new URLSearchParams(body).toString();
    } else {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
  }
  const r = await fetch(API + path, { method, headers, body: payload });
  const text = await r.text();
  const data = text ? JSON.parse(text) : null;
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status} ${text.slice(0, 200)}`);
  return data;
}

let browser;
try {
  // ── 1) เตรียมข้อมูลผ่าน API ──
  const login = await api('POST', '/api/v1/auth/login',
    { username: 'admin', password: 'ChangeMe123!' }, null, true);
  const T = login.access_token;
  log('[1] login ok');

  // ลบ device ชื่อเดิมถ้ามี (ให้สคริปต์รันซ้ำได้ ไม่ทิ้ง device ขยะ)
  const devs = await api('GET', '/api/v1/devices?page_size=100', undefined, T);
  for (const d of devs.items ?? devs) {
    if (d.name === DEVICE_NAME) {
      await api('DELETE', `/api/v1/devices/${d.id}`, undefined, T);
      log('    ลบ device เก่า:', d.id);
    }
  }
  const dev = await api('POST', '/api/v1/devices', {
    name: DEVICE_NAME, location: 'อาคารผู้ป่วยนอก ชั้น 1',
    platform: 'web_browser', tv_brand: 'samsung',
  }, T);
  log('[2] device created, pair code =', dev.pairing_code);

  // เข้ากลุ่ม "ทุกจอใน demo" → ได้ manifest จาก "schedule demo" ที่ active อยู่
  const groups = await api('GET', '/api/v1/groups?page_size=100', undefined, T);
  const grp = (groups.items ?? groups).find((g) => g.name === 'ทุกจอใน demo');
  if (!grp) throw new Error('ไม่พบกลุ่ม "ทุกจอใน demo" — รัน seed_demo ก่อน');
  const cur = (grp.devices ?? []).map((d) => d.id);
  await api('PATCH', `/api/v1/groups/${grp.id}`,
    { device_ids: [...new Set([...cur, dev.id])] }, T);
  log('[3] เพิ่มเข้ากลุ่ม:', grp.name);

  // ── 2) pair ผ่านหน้า player จริง ──
  browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });

  await page.goto('http://localhost:8080', { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForSelector('#server-url', { timeout: 10000 });
  await page.evaluate(() => {
    document.getElementById('server-url').value = '';
    document.getElementById('pair-code').value = '';
  });
  await page.type('#server-url', 'http://localhost:8000');
  await page.type('#pair-code', dev.pairing_code);
  await page.click('#btn-pair');
  log('[4] pairing...');

  await page.waitForFunction(() => {
    const e = document.getElementById('player-screen');
    return e && getComputedStyle(e).display !== 'none';
  }, { timeout: 25000 });
  await new Promise((r) => setTimeout(r, 8000)); // ให้ manifest + iframe โหลดจนนิ่ง

  const info = await page.evaluate(() => document.getElementById('info-bar')?.textContent || '');
  await page.screenshot({ path: `${OUT_DIR}\\fig-4-11-player-normal.png` });
  log('[5] SHOT 4.11 player normal | info-bar:', info);

  // ── 3) emergency overlay ──
  const em = await api('POST', '/api/v1/emergency/', {
    title: 'ประกาศซ้อมอพยพหนีไฟ',
    kind: 'text',
    payload: {
      message: 'ขณะนี้มีการซ้อมอพยพหนีไฟ อาคารผู้ป่วยนอก\nขอให้ทุกท่านออกจากอาคารทางบันไดหนีไฟที่ใกล้ที่สุด และไปรวมกันที่จุดรวมพล',
    },
    target: { all: true }, // จำเป็น — target ว่าง = ไม่เข้าจอไหนเลย (manifest_service เช็ค all:true ตรงๆ)
    priority: 1000,
  }, T);
  await api('POST', `/api/v1/emergency/${em.id}/activate`, {}, T);
  log('[6] emergency activated:', em.id);

  // reload → player ดึง manifest ใหม่ทันทีตอน boot (ไม่ต้องรอ heartbeat 30s)
  await page.reload({ waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForFunction(() => {
    const e = document.getElementById('emergency-overlay');
    return e && getComputedStyle(e).display !== 'none';
  }, { timeout: 90000 });
  await new Promise((r) => setTimeout(r, 2000));
  await page.screenshot({ path: `${OUT_DIR}\\fig-4-12-player-emergency.png` });
  log('[7] SHOT 4.12 player emergency overlay');

  await api('POST', `/api/v1/emergency/${em.id}/cancel`, {}, T);
  log('[8] emergency cancelled — เก็บ record ไว้โชว์ในหน้า Emergency');

  // --hold N: ค้าง browser เปิดไว้ N วินาที (player heartbeat ต่อเนื่อง → device โชว์ "ออนไลน์"
  // ระหว่างสคริปต์ถ่าย Admin UI รันซ้อน) — ให้ dashboard/หน้า Devices มีจอ online จริง
  const holdIdx = process.argv.indexOf('--hold');
  if (holdIdx !== -1) {
    const sec = Number(process.argv[holdIdx + 1] || 120);
    log(`PLAYER_HOLDING ${sec}s`);
    await new Promise((r) => setTimeout(r, sec * 1000));
  }

  await browser.close();
  log('PLAYER_SHOTS: PASS');
  process.exit(0);
} catch (e) {
  log('PLAYER_SHOTS ERROR:', e.message);
  if (browser) await browser.close();
  process.exit(1);
}
