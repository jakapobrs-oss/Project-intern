// API client — fetch wrapper รองรับทั้ง bearer + cookie auth modes
//
// Phase 7 — dual auth:
//   - bearer (default): JWT in localStorage + Authorization header (เหมือนเดิม)
//   - cookie:           httpOnly cookies + CSRF token + credentials: include
//
// เปิด cookie mode ด้วย `NEXT_PUBLIC_AUTH_MODE=cookie` ใน .env.local
//
// อ้างอิง backend/app/api/v1/*

const API_BASE = "/api/v1"; // proxy ใน next.config.mjs

// ===== Auth mode =====
type AuthMode = "bearer" | "cookie";
const AUTH_MODE: AuthMode =
  (process.env.NEXT_PUBLIC_AUTH_MODE as AuthMode) === "cookie" ? "cookie" : "bearer";

export function getAuthMode(): AuthMode {
  return AUTH_MODE;
}

// ===== Bearer mode token storage =====
const ACCESS_KEY = "signage_access_token";
const REFRESH_KEY = "signage_refresh_token";

function getAccessToken(): string | null {
  if (AUTH_MODE !== "bearer" || typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

function getRefreshToken(): string | null {
  if (AUTH_MODE !== "bearer" || typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  if (AUTH_MODE !== "bearer" || typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

/**
 * In bearer mode: เช็คว่ามี access token ใน localStorage
 * In cookie mode: ไม่รู้ — return true แล้วให้ /me เป็นคนตัดสิน
 */
export function hasToken(): boolean {
  if (AUTH_MODE === "cookie") return true;
  return !!getAccessToken();
}

// ===== CSRF token (cookie mode) =====
let csrfTokenCache: string | null = null;

function readCsrfFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

async function getCsrfToken(): Promise<string | null> {
  if (AUTH_MODE !== "cookie") return null;
  if (csrfTokenCache) return csrfTokenCache;

  // อ่านจาก cookie ก่อน (มาจาก /auth/csrf หรือ middleware)
  const fromCookie = readCsrfFromCookie();
  if (fromCookie) {
    csrfTokenCache = fromCookie;
    return fromCookie;
  }

  // fetch ใหม่
  try {
    const res = await fetch(`${API_BASE}/auth/csrf`, { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      csrfTokenCache = data.csrf_token;
      return csrfTokenCache;
    }
  } catch {
    /* ignore */
  }
  return null;
}

// ===== Error class =====
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ===== Refresh logic (single-flight) =====
let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const body: { refresh_token?: string } = {};
        if (AUTH_MODE === "bearer") {
          const rt = getRefreshToken();
          if (!rt) return false;
          body.refresh_token = rt;
        }
        // cookie mode: body ว่าง → backend อ่านจาก cookie
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) return false;
        const data = await res.json();
        if (AUTH_MODE === "bearer") {
          setTokens(data.access_token, data.refresh_token);
        }
        // cookie mode: cookies ถูก rotate ผ่าน Set-Cookie แล้ว
        return true;
      } catch {
        return false;
      } finally {
        setTimeout(() => { refreshPromise = null; }, 0);
      }
    })();
  }
  return refreshPromise;
}

// ===== Core fetch wrapper =====
interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipRefresh?: boolean;
  formData?: boolean;
}

const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { body, skipRefresh, formData, headers, method = "GET", ...rest } = opts;

  const buildHeaders = async (): Promise<HeadersInit> => {
    const h: Record<string, string> = { ...(headers as Record<string, string>) };

    if (AUTH_MODE === "bearer") {
      const token = getAccessToken();
      if (token) h["Authorization"] = `Bearer ${token}`;
    } else {
      // cookie mode: เพิ่ม CSRF header ใน mutation
      if (MUTATION_METHODS.has(method.toUpperCase())) {
        const csrf = await getCsrfToken();
        if (csrf) h["X-CSRF-Token"] = csrf;
      }
    }

    if (body !== undefined && !formData) h["Content-Type"] = "application/json";
    return h;
  };

  const buildBody = (): BodyInit | undefined => {
    if (body === undefined) return undefined;
    if (formData) return body as BodyInit;
    return JSON.stringify(body);
  };

  const doFetch = async () =>
    fetch(`${API_BASE}${path}`, {
      ...rest,
      method,
      credentials: AUTH_MODE === "cookie" ? "include" : "same-origin",
      headers: await buildHeaders(),
      body: buildBody(),
    });

  let res = await doFetch();

  // auto-refresh ถ้า 401 (ครั้งเดียว)
  if (res.status === 401 && !skipRefresh) {
    const ok = await tryRefresh();
    if (ok) {
      res = await doFetch();
    } else {
      clearTokens();
      csrfTokenCache = null;
    }
  }

  if (!res.ok) {
    let errDetail: unknown = null;
    let errMsg = res.statusText || "API error";
    let errCode = `HTTP_${res.status}`;
    try {
      errDetail = await res.json();
      const d = errDetail as { detail?: unknown };
      if (typeof d.detail === "string") {
        errMsg = d.detail;
      } else if (d.detail && typeof d.detail === "object") {
        const dd = d.detail as { code?: string; message?: string };
        if (dd.message) errMsg = dd.message;
        if (dd.code) errCode = dd.code;
      }
    } catch {
      /* body ไม่ใช่ json */
    }
    throw new ApiError(res.status, errCode, errMsg, errDetail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ===== Public API =====
export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form, formData: true }),

  // ===== Auth =====
  async login(username: string, password: string) {
    // backend OAuth2 password form (application/x-www-form-urlencoded)
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      credentials: AUTH_MODE === "cookie" ? "include" : "same-origin",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, `HTTP_${res.status}`, body.detail || "Login failed");
    }
    const data = (await res.json()) as {
      access_token: string;
      refresh_token: string;
    };
    if (AUTH_MODE === "bearer") {
      setTokens(data.access_token, data.refresh_token);
    } else {
      // cookie mode: ดึง CSRF token ใหม่หลัง login (กรณี cookie หมุน)
      csrfTokenCache = null;
      await getCsrfToken();
    }
    return data;
  },

  async logout() {
    // เรียก backend ก่อนเสมอ — cookie mode ต้องให้ backend clear cookies
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: AUTH_MODE === "cookie" ? "include" : "same-origin",
        headers:
          AUTH_MODE === "bearer" && getAccessToken()
            ? { Authorization: `Bearer ${getAccessToken()}` }
            : {},
      });
    } catch {
      /* ignore — proceed ลบ local state อยู่ดี */
    }
    clearTokens();
    csrfTokenCache = null;
  },

  me: () => request<import("./types").User>("/auth/me"),
};
