// ============================================================================
// Service Worker — Signage Player
//
// Cache strategy (§25):
//   - SHELL (HTML/CSS/JS/manifest): cache-first, version bump → ลบ cache เก่า
//   - MEDIA (image/video):           network-first → cache fallback (offline)
//   - API:                           network-only (ห้าม cache — มี token sensitive)
//
// LRU-ish eviction:
//   - shell: bump SHELL_CACHE version → activate ลบของเก่า
//   - media: ตอน fetch สำเร็จใหม่ → enforce cache size cap (FIFO ≈ LRU)
// ============================================================================

// v3 = แก้ app.js (ลิงก์สื่อผ่าน backend + โหลดรูปแบบ CORS) — ไม่ bump แล้วเครื่องเล่นเก่า
// จะใช้ app.js เดิมใน cache ต่อไปเรื่อยๆ ทั้งที่ deploy ใหม่แล้ว
const SHELL_CACHE = 'signage-shell-v3';      // bump เมื่อแก้ styles.css/app.js
const MEDIA_CACHE = 'signage-media-v1';      // sync กับ app.js
const SHELL = ['./', './index.html', './app.js', './styles.css', './manifest.json'];

// ขนาด cap (ต้อง sync กับ app.js MEDIA_CACHE_MAX_BYTES)
const MEDIA_MAX_BYTES = 500 * 1024 * 1024;   // 500 MB

// ===== Install — pre-cache shell =====
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(SHELL_CACHE)
            .then((c) => c.addAll(SHELL))
            .then(() => self.skipWaiting())
    );
});

// ===== Activate — ลบ cache version เก่า =====
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k !== SHELL_CACHE && k !== MEDIA_CACHE)
                    .map((k) => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

// ===== Fetch =====
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API → network only (ห้าม cache token-bearing requests)
    if (url.pathname.startsWith('/api/')) return;

    // shell — cache-first
    if (sameOrigin(url) && isShellPath(url.pathname)) {
        event.respondWith(
            caches.match(event.request)
                .then((r) => r || fetch(event.request))
        );
        return;
    }

    // media — network-first, cache fallback (+ enforce size cap)
    event.respondWith(handleMediaFetch(event.request));
});

function sameOrigin(url) {
    return url.origin === self.location.origin;
}

function isShellPath(pathname) {
    return SHELL.some((s) => pathname.endsWith(s.replace('./', '/'))) || pathname === '/' || pathname.endsWith('/index.html');
}

async function handleMediaFetch(request) {
    try {
        const resp = await fetch(request);
        if (resp.ok && resp.type !== 'opaque') {
            const copy = resp.clone();
            const cache = await caches.open(MEDIA_CACHE);
            await cache.put(request, copy);
            // fire-and-forget eviction
            evictMediaIfOversize(cache);
        }
        return resp;
    } catch (e) {
        // network ล่ม → ลอง cache
        const cached = await caches.match(request, { cacheName: MEDIA_CACHE });
        if (cached) return cached;
        throw e;
    }
}

// LRU/FIFO eviction — ลบ entry เก่าจนกว่าจะอยู่ใน budget
async function evictMediaIfOversize(cache) {
    try {
        const keys = await cache.keys();
        if (keys.length === 0) return;
        // คำนวณ total size (เฉพาะ Response ที่ blob มีอยู่)
        let total = 0;
        const sizes = [];
        for (const req of keys) {
            const resp = await cache.match(req);
            if (!resp) continue;
            const blob = await resp.blob();
            sizes.push({ req, size: blob.size });
            total += blob.size;
        }
        if (total <= MEDIA_MAX_BYTES) return;

        const target = MEDIA_MAX_BYTES * 0.8;
        for (const { req, size } of sizes) {
            if (total <= target) break;
            await cache.delete(req);
            total -= size;
        }
    } catch (e) {
        // ignore — eviction เป็น best-effort
    }
}
