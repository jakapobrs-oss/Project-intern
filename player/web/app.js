// ============================================================================
// Signage Player — Web PWA  (Phase 4 polish — Option F)
//
// New ใน rewrite นี้:
//  1) Zone renderer จริง — รองรับ layout templates (fullscreen / split_70_30 / main_ticker)
//  2) Plan carousel — เล่นไล่ items ตาม duration_sec (manifest.items)
//  3) Emergency overlay — render fullscreen ทับเมื่อ manifest.emergencies non-empty
//  4) Exponential backoff — heartbeat/manifest/commands ใช้ jittered backoff เมื่อ fail
//  5) Media LRU cache (Cache Storage) — pre-cache content URLs, evict เมื่อเกิน MAX_BYTES
//  6) Crash recovery — uncaught error → crash screen + auto-reload 10s
// ============================================================================

(() => {
'use strict';

// ── Config ─────────────────────────────────────────────────────────────────
const HEARTBEAT_BASE_MS = 30_000;       // 30s
const COMMAND_BASE_MS = 5_000;          // 5s
const MANIFEST_MIN_REFRESH_MS = 10_000; // กัน flap — ไม่ refresh ถี่กว่า 10s
const BACKOFF_MAX_MS = 5 * 60_000;      // เพดาน 5 นาที
const MEDIA_CACHE_NAME = 'signage-media-v1';
const MEDIA_CACHE_MAX_BYTES = 500 * 1024 * 1024;   // 500 MB
const CRASH_RELOAD_SEC = 10;

const ls = window.localStorage;

// ── State ──────────────────────────────────────────────────────────────────
const state = {
    serverUrl: ls.getItem('server_url') || '',
    deviceId: ls.getItem('device_id') || null,
    deviceToken: ls.getItem('device_token') || null,
    currentManifestVersion: null,
    manifest: null,
    serialPort: null,
    carouselTimer: null,
    lastManifestFetchAt: 0,
};

// ── DOM helpers ────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function showPairScreen() {
    $('pair-screen').style.display = 'flex';
    $('player-screen').style.display = 'none';
    $('server-url').value = state.serverUrl || 'http://192.168.1.10:8000';
}
function showPlayerScreen() {
    $('pair-screen').style.display = 'none';
    $('player-screen').style.display = 'flex';
    updateInfoBar();
}
function updateInfoBar(extra = '') {
    const dev = state.deviceId?.slice(0, 8) || '?';
    const ver = state.currentManifestVersion?.slice(0, 8) || '-';
    const items = state.manifest?.items?.length ?? 0;
    const emer = state.manifest?.emergencies?.length ?? 0;
    $('info-bar').textContent = `dev=${dev} ver=${ver} items=${items}${emer ? ` 🚨${emer}` : ''} ${extra}`;
}

// ── Backoff util ───────────────────────────────────────────────────────────
// สร้าง backoff state per-loop: รี่เซ็ตเมื่อ success, ทบเมื่อ fail
function createBackoff(baseMs) {
    let consecutiveFails = 0;
    return {
        success() { consecutiveFails = 0; },
        fail() { consecutiveFails++; },
        nextDelayMs() {
            if (consecutiveFails === 0) return baseMs;
            // 2^n * base + jitter (0-30%) — cap ที่ BACKOFF_MAX_MS
            const expo = Math.min(BACKOFF_MAX_MS, baseMs * Math.pow(2, consecutiveFails));
            const jitter = expo * 0.3 * Math.random();
            return Math.floor(expo + jitter);
        },
    };
}

// ── HTTP helper ────────────────────────────────────────────────────────────
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (options.auth !== false && state.deviceToken) {
        headers['Authorization'] = `Bearer ${state.deviceToken}`;
    }
    const resp = await fetch(state.serverUrl + path, { ...options, headers });
    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text}`);
    }
    return resp.headers.get('content-type')?.includes('json') ? resp.json() : resp.text();
}

// ── Pairing ────────────────────────────────────────────────────────────────
async function doPair() {
    const url = $('server-url').value.trim().replace(/\/+$/, '');
    const code = $('pair-code').value.trim().toUpperCase();
    if (!url || !code) {
        setPairStatus('กรุณากรอก server + code', true);
        return;
    }
    state.serverUrl = url;
    ls.setItem('server_url', url);
    setPairStatus('กำลัง pair...', false);

    try {
        const data = await api('/api/v1/player/pair', {
            method: 'POST', auth: false,
            body: JSON.stringify({
                pairing_code: code,
                platform: 'web_browser',
                app_version: '0.2.0',
            }),
        });
        state.deviceId = data.device_id;
        state.deviceToken = data.device_token;
        ls.setItem('device_id', state.deviceId);
        ls.setItem('device_token', state.deviceToken);
        showPlayerScreen();
        startLoops();
    } catch (e) {
        setPairStatus(`ผิดพลาด: ${e.message}`, true);
    }
}

function setPairStatus(msg, isErr) {
    $('pair-status').textContent = msg;
    $('pair-status').className = isErr ? 'status err' : 'status';
}

// ── Zone renderer ──────────────────────────────────────────────────────────
// Render presentation 1 หน้า — zones positioned ตาม layout_json.zones[]
function renderPresentation(presItem) {
    const stage = $('stage');
    stage.innerHTML = '';
    if (!presItem) {
        stage.innerHTML = `<div class="zone zone-empty" style="inset:0;position:absolute">📭 ไม่มี content ที่ schedule</div>`;
        return;
    }

    // layout_json.zones = [{key,x,y,w,h}] — percentage
    const layoutZones = presItem.layout?.zones || [];
    const zonesByKey = new Map();
    for (const z of (presItem.zones || [])) zonesByKey.set(z.zone_key, z);

    if (layoutZones.length === 0) {
        // fallback: เต็มจอ ใช้ zone แรก
        const first = presItem.zones?.[0];
        if (first) {
            const el = document.createElement('div');
            el.className = 'zone';
            el.style.cssText = 'inset:0;position:absolute';
            el.dataset.key = first.zone_key;
            el.appendChild(buildZoneContent(first));
            stage.appendChild(el);
        }
        return;
    }

    for (const layoutZone of layoutZones) {
        const el = document.createElement('div');
        el.className = 'zone';
        el.dataset.key = layoutZone.key;
        el.style.left = `${layoutZone.x}%`;
        el.style.top = `${layoutZone.y}%`;
        el.style.width = `${layoutZone.w}%`;
        el.style.height = `${layoutZone.h}%`;
        const contentZone = zonesByKey.get(layoutZone.key);
        el.appendChild(contentZone ? buildZoneContent(contentZone) : buildEmptyZone(layoutZone.key));
        stage.appendChild(el);
    }
}

function buildEmptyZone(key) {
    const d = document.createElement('div');
    d.className = 'zone-empty';
    d.style.cssText = 'width:100%;height:100%';
    d.textContent = `(${key})`;
    return d;
}

// ลิงก์สื่อจาก manifest ปกติเป็น URL เต็ม (backend ประกอบจาก host ที่เราเรียกเข้าไป)
// แต่ถ้าเป็น path แบบ relative ให้ต่อกับ server URL ที่ pair ไว้ — ห้าม resolve กับ origin
// ของหน้าเว็บ player เพราะไฟล์อยู่ที่ backend คนละที่กัน
function mediaUrl(u) {
    if (!u) return u;
    try { return new URL(u, state.serverUrl || location.origin).href; } catch { return u; }
}

function buildZoneContent(zone) {
    const url = mediaUrl(zone.content_url);
    const type = zone.content_type;

    // Special-case: ticker zone — text scroll แทน iframe
    if (zone.zone_key === 'ticker' && type === 'text') {
        const div = document.createElement('div');
        div.className = 'ticker-track';
        div.textContent = (zone.params?.text) || '— ไม่มีข้อความ —';
        return div;
    }

    if (!url) {
        const d = document.createElement('div');
        d.className = 'zone-empty';
        d.textContent = `(${zone.zone_key}: no url)`;
        return d;
    }

    if (type === 'image') {
        const img = document.createElement('img');
        // crossOrigin ต้องตั้งก่อน src — ให้โหลดแบบ CORS เหมือนกับที่ preCacheMedia ใช้ fetch
        // ไม่งั้นของใน browser cache จะเป็นคำตอบที่ไม่มี CORS header แล้ว fetch จะโดนบล็อก
        img.crossOrigin = 'anonymous';
        img.src = url; img.alt = '';
        // fit_mode ผ่าน params_json (cover/contain)
        if (zone.params?.fit_mode === 'cover') img.style.objectFit = 'cover';
        return img;
    }
    if (type === 'video') {
        const v = document.createElement('video');
        v.crossOrigin = 'anonymous';   // เหตุผลเดียวกับ img ด้านบน
        v.src = url;
        v.autoplay = true;
        v.muted = (zone.params?.mute !== false);
        v.loop = (zone.params?.loop !== false);
        v.playsInline = true;
        return v;
    }
    // web / stream → iframe (sandboxed)
    const f = document.createElement('iframe');
    f.src = url;
    f.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups');
    f.setAttribute('referrerpolicy', 'no-referrer');
    return f;
}

// ── Plan carousel ──────────────────────────────────────────────────────────
// เล่นไล่ manifest.items ทีละตัว ตาม duration_sec แล้วเริ่มใหม่
function startCarousel(items) {
    if (state.carouselTimer) {
        clearTimeout(state.carouselTimer);
        state.carouselTimer = null;
    }
    if (!items || items.length === 0) {
        renderPresentation(null);
        return;
    }
    let idx = 0;
    const tick = () => {
        const item = items[idx % items.length];
        renderPresentation(item);
        const dur = Math.max(1, item.duration_sec || 30);
        state.carouselTimer = setTimeout(() => { idx++; tick(); }, dur * 1000);
    };
    tick();
}

// ── Emergency overlay ─────────────────────────────────────────────────────
function applyEmergencies(emergencies) {
    const overlay = $('emergency-overlay');
    if (!emergencies || emergencies.length === 0) {
        overlay.style.display = 'none';
        overlay.innerHTML = '<h1 id="emergency-title">⚠ แจ้งเตือนฉุกเฉิน</h1><div class="msg" id="emergency-msg"></div>';
        return;
    }
    // priority สูงสุดอยู่ index 0 (backend sort แล้ว)
    const e = emergencies[0];
    overlay.style.display = 'flex';
    overlay.innerHTML = '';   // reset

    const title = document.createElement('h1');
    title.textContent = e.title || '⚠ แจ้งเตือนฉุกเฉิน';
    overlay.appendChild(title);

    if (e.kind === 'text') {
        const m = document.createElement('div');
        m.className = 'msg';
        m.textContent = e.payload?.message || '(no message)';
        if (e.payload?.bg_color) overlay.style.background = e.payload.bg_color;
        if (e.payload?.text_color) overlay.style.color = e.payload.text_color;
        overlay.appendChild(m);
    } else if (e.kind === 'url') {
        const f = document.createElement('iframe');
        f.src = e.payload?.url;
        overlay.appendChild(f);
        // auto-refresh ถ้าระบุ refresh_sec
        const sec = Number(e.payload?.refresh_sec || 0);
        if (sec > 0) {
            setTimeout(() => { f.src = f.src; }, sec * 1000);
        }
    } else if (e.kind === 'image' && e.payload?.url) {
        const img = document.createElement('img');
        img.src = e.payload.url;
        img.style.maxWidth = '90vw';
        img.style.maxHeight = '70vh';
        overlay.appendChild(img);
    }
}

// ── Media LRU cache (Cache Storage API) ────────────────────────────────────
// pre-cache content URLs ตอน manifest change → next render เร็ว + offline
async function preCacheMedia(items) {
    if (!('caches' in window)) return;
    try {
        const cache = await caches.open(MEDIA_CACHE_NAME);
        const urls = new Set();
        for (const it of items || []) {
            for (const z of (it.zones || [])) {
                if (z.content_url && (z.content_type === 'image' || z.content_type === 'video')) {
                    urls.add(mediaUrl(z.content_url));
                }
            }
        }
        // Add ที่ยังไม่มีใน cache
        await Promise.all(
            Array.from(urls).map(async (url) => {
                const existing = await cache.match(url);
                if (existing) return;
                try {
                    const resp = await fetch(url, { mode: 'cors' });
                    if (resp.ok) await cache.put(url, resp);
                } catch (e) { /* ข้าม URL ที่ fetch ไม่ได้ */ }
            })
        );
        await evictCacheIfOversize(cache);
    } catch (e) {
        console.warn('preCacheMedia error:', e);
    }
}

// LRU eviction — ถ้า cache > MAX_BYTES, ลบ entry เก่าก่อน
// Cache Storage API ไม่มี LRU built-in → ใช้ insertion order (FIFO ใกล้เคียง LRU)
async function evictCacheIfOversize(cache) {
    const keys = await cache.keys();
    let total = 0;
    const sizes = [];
    for (const req of keys) {
        const resp = await cache.match(req);
        const blob = await resp.blob();
        sizes.push({ req, size: blob.size });
        total += blob.size;
    }
    if (total <= MEDIA_CACHE_MAX_BYTES) return;

    // ลบจากตัวแรก (oldest insert) จนกว่าเหลือ ≤ 80% ของ MAX
    const target = MEDIA_CACHE_MAX_BYTES * 0.8;
    for (const { req, size } of sizes) {
        if (total <= target) break;
        await cache.delete(req);
        total -= size;
    }
    console.info(`media-cache evicted → ~${(total / 1024 / 1024).toFixed(1)}MB`);
}

// ── Manifest refresh ──────────────────────────────────────────────────────
async function refreshManifest() {
    // กัน refresh ถี่
    const now = Date.now();
    if (now - state.lastManifestFetchAt < MANIFEST_MIN_REFRESH_MS) return false;
    state.lastManifestFetchAt = now;

    const m = await api('/api/v1/player/manifest');
    state.manifest = m;
    state.currentManifestVersion = m.version;

    applyEmergencies(m.emergencies || []);
    startCarousel(m.items || []);
    preCacheMedia(m.items || []);   // fire-and-forget
    return true;
}

// ── Heartbeat loop (with backoff) ──────────────────────────────────────────
async function heartbeatLoop() {
    const backoff = createBackoff(HEARTBEAT_BASE_MS);
    while (true) {
        try {
            const resp = await api('/api/v1/player/heartbeat', {
                method: 'POST',
                body: JSON.stringify({
                    status: 'online',
                    app_version: '0.2.0',
                    uptime_sec: Math.floor(performance.now() / 1000),
                    current_manifest_version: state.currentManifestVersion,
                }),
            });
            backoff.success();
            if (resp.manifest_outdated) {
                await refreshManifest();
            }
            updateInfoBar();
        } catch (e) {
            backoff.fail();
            updateInfoBar(`⚠ ${e.message}`);
        }
        await sleep(backoff.nextDelayMs());
    }
}

// ── TV command loop (with backoff) ────────────────────────────────────────
// Routing:
//   brand=cec    → CEC helper (HTTP localhost:7600) — สำหรับ HDMI-CEC consumer TV
//   brand=other  → Web Serial API (RS-232 USB adapter)
async function commandLoop() {
    const backoff = createBackoff(COMMAND_BASE_MS);
    while (true) {
        try {
            const cmds = await api('/api/v1/player/commands');
            for (const cmd of cmds) {
                let ok = false;
                let errMsg = null;

                // ลอง CEC helper ก่อนถ้า brand=cec
                const cecResult = await sendViaCecHelper(cmd.brand, cmd.command_type);
                if (cecResult !== null) {
                    ok = cecResult;
                    errMsg = ok ? null : 'cec helper failed';
                } else {
                    // fallback Web Serial (RS-232)
                    ok = await sendSerialBytes(cmd.raw_bytes_hex);
                    errMsg = ok ? null : 'serial unavailable';
                }

                await api(`/api/v1/player/commands/${cmd.cmd_id}/ack`, {
                    method: 'POST',
                    body: JSON.stringify({ success: ok, error: errMsg }),
                });
            }
            backoff.success();
        } catch (e) {
            backoff.fail();
            // queue ว่างไม่ถือเป็น error สำคัญ — silent
        }
        await sleep(backoff.nextDelayMs());
    }
}

// ── CEC helper bridge (Linux RPi via localhost daemon) ─────────────────────
// ถ้า cec_helper.py ทำงานอยู่ที่ 127.0.0.1:7600 → ใช้ HDMI-CEC แทน Web Serial
// (Web Serial RS-232 อย่างเดียวไม่ครอบ TV ที่รองรับ CEC-only เช่น HDMI consumer TV)
const CEC_HELPER_URL = 'http://127.0.0.1:7600';
let cecHelperAvailable = null;     // null = ยังไม่ตรวจ, true/false = cached

async function checkCecHelper() {
    if (cecHelperAvailable !== null) return cecHelperAvailable;
    try {
        const resp = await fetch(`${CEC_HELPER_URL}/health`, { signal: AbortSignal.timeout(2000) });
        cecHelperAvailable = resp.ok;
    } catch { cecHelperAvailable = false; }
    return cecHelperAvailable;
}

// แปล brand="cec" + command_type → CEC helper API call
// ถ้า brand เป็น CEC → ใช้ helper, ถ้าเป็น serial brand (samsung/lg/...) → Web Serial
async function sendViaCecHelper(brand, commandType) {
    if (brand !== 'cec') return null;     // ไม่ใช่ CEC → ให้ Web Serial จัดการ
    if (!(await checkCecHelper())) return null;

    let endpoint = null;
    let body = {};
    if (commandType === 'power_on')   { endpoint = '/cec/power'; body = { on: true }; }
    else if (commandType === 'power_off') { endpoint = '/cec/power'; body = { on: false }; }
    else if (commandType === 'volume_up') { endpoint = '/cec/volume'; body = { direction: 'up' }; }
    else if (commandType === 'volume_down') { endpoint = '/cec/volume'; body = { direction: 'down' }; }
    else if (commandType === 'mute') { endpoint = '/cec/mute'; }
    else return null;     // command อื่น (input HDMI1/2/3) ไม่ map → fallback

    try {
        const resp = await fetch(`${CEC_HELPER_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        return !!data.ok;
    } catch (e) {
        console.warn('CEC helper request fail', e);
        return false;
    }
}

// ── Web Serial bridge ──────────────────────────────────────────────────────
async function sendSerialBytes(hex) {
    if (!('serial' in navigator)) {
        console.warn('Web Serial API not supported — command discarded');
        return false;
    }
    try {
        if (!state.serialPort) {
            state.serialPort = await navigator.serial.requestPort();
            await state.serialPort.open({ baudRate: 9600 });
        }
        const bytes = hexToBytes(hex);
        const writer = state.serialPort.writable.getWriter();
        await writer.write(bytes);
        writer.releaseLock();
        return true;
    } catch (e) {
        console.error('serial write fail', e);
        return false;
    }
}

function hexToBytes(hex) {
    const clean = hex.replace(/[\s:]/g, '');
    const out = new Uint8Array(clean.length / 2);
    for (let i = 0; i < out.length; i++) out[i] = parseInt(clean.substr(i * 2, 2), 16);
    return out;
}

// ── Crash recovery ────────────────────────────────────────────────────────
function setupCrashRecovery() {
    const onCrash = (msg) => {
        const screen = $('crash-screen');
        $('crash-detail').textContent = msg;
        screen.style.display = 'flex';
        let remain = CRASH_RELOAD_SEC;
        $('crash-countdown').textContent = `กำลัง reload ใน ${remain} วินาที...`;
        const tick = setInterval(() => {
            remain--;
            if (remain <= 0) { clearInterval(tick); location.reload(); }
            else $('crash-countdown').textContent = `กำลัง reload ใน ${remain} วินาที...`;
        }, 1000);
    };
    window.addEventListener('error', (e) => onCrash(`Uncaught: ${e.message}\n${e.error?.stack || ''}`));
    window.addEventListener('unhandledrejection', (e) => onCrash(`Promise: ${e.reason}`));
}

// ── Boot ──────────────────────────────────────────────────────────────────
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function startLoops() {
    // โหลด manifest ครั้งแรก (ถ้า fail — backoff ใน heartbeat จะรีลอง)
    try { await refreshManifest(); } catch (e) { console.warn('initial manifest fail', e); }
    heartbeatLoop();
    commandLoop();
}

document.addEventListener('DOMContentLoaded', () => {
    setupCrashRecovery();
    $('btn-pair').addEventListener('click', doPair);
    if (state.deviceToken && state.serverUrl) {
        showPlayerScreen();
        startLoops();
    } else {
        showPairScreen();
    }
});

})();
