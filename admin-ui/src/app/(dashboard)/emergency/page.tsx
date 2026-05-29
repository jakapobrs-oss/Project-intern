"use client";
// Emergency Broadcast — สร้าง / activate / cancel
// roles: super_admin, admin, operator มี mutate, role อื่นอ่านอย่างเดียว

import { useEffect, useState } from "react";
import { AlertTriangle, Plus, RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { EmergencyBroadcast, EmergencyKind, Device, PlayerGroup } from "@/lib/types";
import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  CardBody,
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
  Textarea,
} from "@/components/ui";

export default function EmergencyPage() {
  const { user } = useAuth();
  const toast = useToast();
  const canMutate = hasRole(user, "super_admin", "admin", "operator");

  const [items, setItems] = useState<EmergencyBroadcast[] | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [groups, setGroups] = useState<PlayerGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const load = async () => {
    try {
      const [list, d, g] = await Promise.all([
        api.get<EmergencyBroadcast[]>("/emergency/"),
        api.get<Device[]>("/devices"),
        api.get<PlayerGroup[]>("/groups"),
      ]);
      setItems(list); setDevices(d); setGroups(g);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "โหลดไม่สำเร็จ");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleActivate = async (b: EmergencyBroadcast) => {
    if (!confirm(`Activate broadcast "${b.title}" ? — จะถูก override schedule ทุกจอที่ตรง target`)) return;
    try {
      const updated = await api.post<EmergencyBroadcast>(`/emergency/${b.id}/activate`);
      setItems((prev) => prev?.map((x) => (x.id === b.id ? updated : x)) ?? null);
      toast.success(`Activated: ${b.title}`);
    } catch (e) {
      toast.error("activate ไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const handleCancel = async (b: EmergencyBroadcast) => {
    if (!confirm(`Cancel broadcast "${b.title}" ?`)) return;
    try {
      const updated = await api.post<EmergencyBroadcast>(`/emergency/${b.id}/cancel`);
      setItems((prev) => prev?.map((x) => (x.id === b.id ? updated : x)) ?? null);
      toast.success(`Cancelled: ${b.title}`);
    } catch (e) {
      toast.error("cancel ไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const activeCount = items?.filter((x) => x.status === "active").length ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-600">
            แจ้งเตือนฉุกเฉิน — override schedule ปกติ (priority สูงสุด)
          </p>
          {activeCount > 0 && (
            <Badge variant="danger" className="mt-1">
              <AlertTriangle className="mr-1 h-3 w-3" />
              มี {activeCount} broadcast ที่กำลัง active
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canMutate && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> สร้าง broadcast
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {items === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-5 w-5 text-brand-600" />
        </div>
      ) : items.length === 0 ? (
        <Empty title="ยังไม่มี broadcast" description="กด 'สร้าง broadcast' เพื่อเตรียมแจ้งเตือน" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>หัวข้อ</TH>
              <TH>ประเภท</TH>
              <TH>เป้าหมาย</TH>
              <TH>Priority</TH>
              <TH>สถานะ</TH>
              <TH>ช่วงเวลา</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {items.map((b) => (
              <tr key={b.id} className="hover:bg-slate-50">
                <TD>
                  <div className="font-medium">{b.title}</div>
                </TD>
                <TD className="text-xs uppercase">{b.kind}</TD>
                <TD className="text-xs">{summarizeTarget(b.target)}</TD>
                <TD>{b.priority}</TD>
                <TD>
                  <StatusBadge status={b.status} />
                </TD>
                <TD className="text-xs text-slate-500">
                  {b.starts_at ? new Date(b.starts_at).toLocaleString("th-TH") : "—"}
                  {b.ends_at && (
                    <div>ถึง: {new Date(b.ends_at).toLocaleString("th-TH")}</div>
                  )}
                </TD>
                <TD className="text-right">
                  {canMutate && b.status === "draft" && (
                    <Button size="sm" variant="danger" onClick={() => handleActivate(b)}>
                      <AlertTriangle className="h-3.5 w-3.5" /> Activate
                    </Button>
                  )}
                  {canMutate && b.status === "active" && (
                    <Button size="sm" variant="secondary" onClick={() => handleCancel(b)}>
                      Cancel
                    </Button>
                  )}
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <CreateEmergencyModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        devices={devices}
        groups={groups}
        onCreated={(b) => setItems((prev) => (prev ? [b, ...prev] : [b]))}
      />
    </div>
  );
}

function summarizeTarget(target: Record<string, unknown>): string {
  if (target.all === true) return "ทุกจอ";
  if (Array.isArray(target.device_ids) && target.device_ids.length > 0) {
    return `${target.device_ids.length} จอ (เจาะจง)`;
  }
  if (Array.isArray(target.group_ids) && target.group_ids.length > 0) {
    return `${target.group_ids.length} กลุ่ม`;
  }
  return "(ไม่ระบุ)";
}

type TargetMode = "all" | "groups" | "devices";

function CreateEmergencyModal({
  open,
  onClose,
  devices,
  groups,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  devices: Device[];
  groups: PlayerGroup[];
  onCreated: (b: EmergencyBroadcast) => void;
}) {
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<EmergencyKind>("text");
  const [message, setMessage] = useState("");
  const [url, setUrl] = useState("");
  const [priority, setPriority] = useState(1500);
  const [endsInMinutes, setEndsInMinutes] = useState<string>("60");
  const [targetMode, setTargetMode] = useState<TargetMode>("all");
  const [targetGroups, setTargetGroups] = useState<Set<string>>(new Set());
  const [targetDevices, setTargetDevices] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setTitle(""); setKind("text"); setMessage(""); setUrl("");
    setPriority(1500); setEndsInMinutes("60");
    setTargetMode("all"); setTargetGroups(new Set()); setTargetDevices(new Set());
    setError(null);
  };

  const toggleGroup = (id: string) => setTargetGroups((p) => {
    const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n;
  });
  const toggleDevice = (id: string) => setTargetDevices((p) => {
    const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n;
  });

  const handleSubmit = async () => {
    setError(null);
    if (!title.trim()) return setError("ระบุหัวข้อ");
    if (kind === "text" && !message.trim()) return setError("ระบุข้อความ");
    if (kind === "url" && !url.trim()) return setError("ระบุ URL");
    if (targetMode === "groups" && targetGroups.size === 0) return setError("เลือกอย่างน้อย 1 กลุ่ม");
    if (targetMode === "devices" && targetDevices.size === 0) return setError("เลือกอย่างน้อย 1 จอ");

    const payload: Record<string, unknown> =
      kind === "text"
        ? { message: message.trim(), bg_color: "#c00", text_color: "#fff", font_size: 96 }
        : kind === "url"
        ? { url: url.trim(), refresh_sec: 60 }
        : {};

    let target: Record<string, unknown>;
    if (targetMode === "all") target = { all: true };
    else if (targetMode === "groups") target = { group_ids: Array.from(targetGroups) };
    else target = { device_ids: Array.from(targetDevices) };

    const minutes = Number(endsInMinutes);
    const ends_at = minutes > 0 ? new Date(Date.now() + minutes * 60_000).toISOString() : null;

    setLoading(true);
    try {
      const b = await api.post<EmergencyBroadcast>("/emergency/", {
        title: title.trim(), kind, payload, target,
        priority, starts_at: null, ends_at, requires_ack: false,
      });
      onCreated(b);
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
      onClose={() => {
        reset();
        onClose();
      }}
      title="สร้าง emergency broadcast"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            ยกเลิก
          </Button>
          <Button onClick={handleSubmit} loading={loading}>
            สร้าง (DRAFT — ยังไม่ active)
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">หัวข้อ *</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="เช่น ไฟไหม้ - อพยพ" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">ประเภท</label>
          <Select value={kind} onChange={(e) => setKind(e.target.value as EmergencyKind)}>
            <option value="text">ข้อความ (full-screen)</option>
            <option value="url">URL (iframe)</option>
            <option value="image" disabled>
              รูปภาพ (Pass 2)
            </option>
          </Select>
        </div>
        {kind === "text" && (
          <div>
            <label className="mb-1 block text-sm font-medium">ข้อความ *</label>
            <Textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} />
          </div>
        )}
        {kind === "url" && (
          <div>
            <label className="mb-1 block text-sm font-medium">URL *</label>
            <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." />
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Priority</label>
            <Input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
            <p className="mt-0.5 text-xs text-slate-500">ปกติ 1000+ เพื่อให้สูงกว่า schedule</p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">หมดอายุใน (นาที)</label>
            <Input
              type="number"
              value={endsInMinutes}
              onChange={(e) => setEndsInMinutes(e.target.value)}
              placeholder="0 = ไม่หมดอายุ"
            />
          </div>
        </div>
        {/* === Target picker === */}
        <div>
          <label className="mb-1 block text-sm font-medium">เป้าหมาย (ใครเห็น broadcast นี้) *</label>
          <Select value={targetMode} onChange={(e) => setTargetMode(e.target.value as TargetMode)}>
            <option value="all">ทุกจอ (all)</option>
            <option value="groups">เฉพาะกลุ่มจอ</option>
            <option value="devices">เลือกจอเจาะจง</option>
          </Select>
        </div>

        {targetMode === "groups" && (
          <div className="max-h-40 overflow-y-auto rounded border border-slate-200">
            {groups.length === 0 ? (
              <p className="p-3 text-sm text-slate-500">ยังไม่มีกลุ่มจอ</p>
            ) : groups.map((g) => (
              <label key={g.id} className="flex cursor-pointer items-center gap-2 border-b border-slate-100 px-3 py-1.5 last:border-0 hover:bg-slate-50">
                <input type="checkbox" checked={targetGroups.has(g.id)} onChange={() => toggleGroup(g.id)} />
                <span className="flex-1 text-sm">{g.name}</span>
                <span className="text-xs text-slate-500">{g.device_ids.length} จอ</span>
              </label>
            ))}
          </div>
        )}

        {targetMode === "devices" && (
          <div className="max-h-40 overflow-y-auto rounded border border-slate-200">
            {devices.length === 0 ? (
              <p className="p-3 text-sm text-slate-500">ยังไม่มีจอ</p>
            ) : devices.map((d) => (
              <label key={d.id} className="flex cursor-pointer items-center gap-2 border-b border-slate-100 px-3 py-1.5 last:border-0 hover:bg-slate-50">
                <input type="checkbox" checked={targetDevices.has(d.id)} onChange={() => toggleDevice(d.id)} />
                <span className="flex-1 text-sm">{d.name}</span>
                <span className="text-xs text-slate-500">{d.location || "—"}</span>
              </label>
            ))}
          </div>
        )}

        {error && <div className="text-sm text-rose-600">{error}</div>}
      </div>
    </Modal>
  );
}
