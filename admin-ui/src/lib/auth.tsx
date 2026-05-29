"use client";
// AuthProvider — context global เก็บ user ปัจจุบัน + helper logout/refresh
//
// Phase 7 dual-mode:
//   - bearer: hasToken() อ่าน localStorage → ถ้ามี token ลอง /me
//   - cookie: hasToken() คืน true เสมอ → /me เป็นคนตัดสิน (401 = ยังไม่ login)
//
// ใน cookie mode logout เรียก backend /auth/logout ให้ backend clear cookies

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api, hasToken } from "./api";
import type { User, Role } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    if (!hasToken()) {
      // Bearer mode + no token → ไม่ต้องเรียก
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      // 401 ใน cookie mode = ยังไม่ login (no fallback)
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
    router.push("/login");
  }, [router]);

  // protect routes: ถ้าไม่มี user + ไม่ใช่ /login → redirect
  useEffect(() => {
    if (loading) return;
    if (!user && pathname !== "/login") {
      router.push("/login");
    } else if (user && pathname === "/login") {
      router.push("/");
    }
  }, [user, loading, pathname, router]);

  return (
    <AuthCtx.Provider value={{ user, loading, refresh: fetchMe, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// helper — เช็คสิทธิ์เปิด/ปิด UI
export function hasRole(user: User | null, ...roles: Role[]): boolean {
  if (!user) return false;
  return roles.includes(user.role);
}
