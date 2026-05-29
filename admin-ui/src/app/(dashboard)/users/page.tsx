"use client";
// User management — super_admin เท่านั้น
// minimal: list + create user + lock/unlock

import { useEffect, useState } from "react";
import { Plus, Lock, Unlock, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { User, Role } from "@/lib/types";
import { ROLE_LABELS } from "@/lib/types";
import {
  Button,
  Input,
  Modal,
  Select,
  StatusBadge,
  TBody,
  TD,
  TH,
  THead,
  Table,
  Empty,
  Spinner,
  Badge,
} from "@/components/ui";
import { useToast } from "@/components/toast";

const ROLES: Role[] = ["super_admin", "admin", "editor", "approver", "viewer", "operator"];

export default function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const load = async () => {
    try {
      const list = await api.get<User[]>("/users");
      setUsers(list);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "โหลดไม่สำเร็จ");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleToggleLock = async (u: User) => {
    try {
      const updated = await api.patch<User>(`/users/${u.id}`, {
        is_locked: !u.is_locked,
      });
      setUsers((prev) => prev?.map((x) => (x.id === u.id ? updated : x)) ?? null);
      toast.success(updated.is_locked ? `ล็อก ${u.username}` : `ปลดล็อก ${u.username}`);
    } catch (e) {
      toast.error("อัปเดตไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">จัดการผู้ใช้งานระบบ admin (ดู §21 RBAC 7 roles)</p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" /> เพิ่ม user
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {users === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-5 w-5 text-brand-600" />
        </div>
      ) : users.length === 0 ? (
        <Empty title="ยังไม่มี user" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>Username</TH>
              <TH>ชื่อ-นามสกุล</TH>
              <TH>Email</TH>
              <TH>Role</TH>
              <TH>สถานะ</TH>
              <TH>Login ล่าสุด</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50">
                <TD className="font-mono text-xs">{u.username}</TD>
                <TD>{u.full_name || "—"}</TD>
                <TD className="text-xs">{u.email}</TD>
                <TD>
                  <Badge variant={u.role === "super_admin" ? "info" : "neutral"}>
                    {ROLE_LABELS[u.role]}
                  </Badge>
                </TD>
                <TD>
                  {u.is_locked ? (
                    <StatusBadge status="error" />
                  ) : u.is_active ? (
                    <StatusBadge status="active" />
                  ) : (
                    <StatusBadge status="offline" />
                  )}
                </TD>
                <TD className="text-xs text-slate-500">
                  {u.last_login_at ? new Date(u.last_login_at).toLocaleString("th-TH") : "—"}
                </TD>
                <TD className="text-right">
                  <Button size="sm" variant="ghost" onClick={() => handleToggleLock(u)}>
                    {u.is_locked ? (
                      <><Unlock className="h-3.5 w-3.5" /> ปลดล็อก</>
                    ) : (
                      <><Lock className="h-3.5 w-3.5" /> ล็อก</>
                    )}
                  </Button>
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <CreateUserModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(u) => setUsers((prev) => (prev ? [u, ...prev] : [u]))}
      />
    </div>
  );
}

function CreateUserModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (u: User) => void;
}) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setUsername(""); setEmail(""); setFullName(""); setPassword(""); setRole("viewer"); setError(null);
  };

  const handleSubmit = async () => {
    setError(null);
    if (!username.trim() || !email.trim() || !password) {
      setError("กรอกข้อมูลให้ครบ");
      return;
    }
    if (password.length < 8) {
      setError("รหัสผ่านอย่างน้อย 8 ตัวอักษร");
      return;
    }
    setLoading(true);
    try {
      const u = await api.post<User>("/users", {
        username: username.trim(),
        email: email.trim(),
        full_name: fullName.trim(),
        password,
        role,
      });
      onCreated(u);
      reset();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "สร้างไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => { reset(); onClose(); }}
      title="เพิ่ม user ใหม่"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>ยกเลิก</Button>
          <Button onClick={handleSubmit} loading={loading}>สร้าง</Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">Username *</label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Email *</label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">ชื่อ-นามสกุล</label>
          <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">รหัสผ่าน *</label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
          <p className="mt-0.5 text-xs text-slate-500">อย่างน้อย 8 ตัวอักษร</p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Role *</label>
          <Select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]} ({r})
              </option>
            ))}
          </Select>
        </div>
        {error && <div className="text-sm text-rose-600">{error}</div>}
      </div>
    </Modal>
  );
}
