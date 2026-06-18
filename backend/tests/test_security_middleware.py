"""
Phase 7 tests — security headers + rate limit middleware
"""
import pytest

# ─── Security headers ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_headers_present_on_root(client):
    """ทุก response ต้องมี security headers"""
    res = await client.get("/")
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "no-referrer"
    assert "permissions-policy" in res.headers


@pytest.mark.asyncio
async def test_csp_present_on_api(client):
    """API routes ต้องมี Content-Security-Policy"""
    res = await client.get("/api/v1/ping")
    assert "content-security-policy" in res.headers
    assert "frame-ancestors 'none'" in res.headers["content-security-policy"]


@pytest.mark.asyncio
async def test_hsts_not_set_in_development(client):
    """HSTS ต้องไม่ใส่ตอน development (app_env=development → is_production=False)"""
    res = await client.get("/")
    # ถ้า settings.app_env != "development" → จะมี HSTS — ใน test เราใช้ env=development
    # default settings ใน config มี app_env="development" → ไม่ใส่ HSTS
    # (ถ้าเทสตัวนี้ fail ตรวจ env var ใน test setup)
    assert "strict-transport-security" not in res.headers


# ─── Rate limit ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_rate_limit_blocks_after_max_requests(client):
    """พยายาม login เกิน max ใน window → 429 + Retry-After"""
    # default settings: 10 requests / 60s — ลอง 15 ครั้งติด
    statuses = []
    for _ in range(15):
        res = await client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "wrong"},
        )
        statuses.append(res.status_code)

    # อย่างน้อย 5 ครั้งสุดท้ายต้อง 429
    last_5 = statuses[-5:]
    assert 429 in last_5, f"expected 429 in last 5, got {last_5}"

    # ตอนที่ blocked → ต้องมี Retry-After + body code=RATE_LIMITED
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "x", "password": "x"},
    )
    if res.status_code == 429:
        assert res.headers.get("retry-after") is not None
        body = res.json()
        assert body.get("detail", {}).get("code") == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_non_protected_paths_not_rate_limited(client):
    """ping/healthz ต้องไม่โดน rate limit"""
    # ลอง 20 ครั้ง — ต้องผ่านหมด
    for _ in range(20):
        res = await client.get("/api/v1/ping")
        assert res.status_code == 200, f"got {res.status_code}"


# ─── Rate limit backends (memory + redis-fallback) ──────────────────

@pytest.mark.asyncio
async def test_memory_backend_check_and_record():
    """unit test ของ _MemoryBucket — sliding window logic"""
    from app.core.middleware import _MemoryBucket
    bucket = _MemoryBucket(max_requests=3, window_sec=60)

    # 3 ครั้งแรกผ่าน
    for i in range(3):
        allowed, _ = bucket.check_and_record("1.2.3.4")
        assert allowed, f"request {i} ควรผ่าน"

    # ครั้งที่ 4 บล็อก
    allowed, retry_after = bucket.check_and_record("1.2.3.4")
    assert not allowed
    assert retry_after > 0

    # IP อื่นไม่กระทบ
    allowed2, _ = bucket.check_and_record("9.9.9.9")
    assert allowed2


@pytest.mark.asyncio
async def test_redis_backend_fallback_when_no_client():
    """backend=redis แต่ redis_client=None → middleware ใช้ memory fallback"""
    from starlette.applications import Starlette

    from app.core.middleware import RateLimitMiddleware
    starlette_app = Starlette()
    mw = RateLimitMiddleware(starlette_app, backend="redis", redis_client=None)
    # ตรวจว่า fallback ไป _MemoryBucket
    from app.core.middleware import _MemoryBucket
    assert isinstance(mw.bucket, _MemoryBucket)


@pytest.mark.asyncio
async def test_redis_backend_fail_open_on_error():
    """Redis error → fail-open (allow request) — กัน Redis down ทำ login ใช้ไม่ได้"""
    from app.core.middleware import _RedisBucket

    class _BrokenPipeline:
        def incr(self, *a): pass
        def expire(self, *a): pass
        async def execute(self):
            raise RuntimeError("redis exploded")

    class _BrokenRedis:
        def pipeline(self):
            return _BrokenPipeline()

    bucket = _RedisBucket(_BrokenRedis(), max_requests=3, window_sec=60)
    allowed, retry_after = await bucket.check_and_record("1.2.3.4")
    # fail-open
    assert allowed
    assert retry_after == 0
