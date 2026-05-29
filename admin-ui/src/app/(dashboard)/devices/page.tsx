"use client";
// Devices — list + สร้างใหม่ + แสดง pairing code + regenerate

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, RefreshCw, Key, ExternalLink } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { Device, DevicePlatform } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";
import {
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
} from "@/components/ui";
import { useToast } from "@/components/toast";

const PLATFORM_OPTIONS: { value: DevicePlatform; label: string }[] = [
  { value: "android_tv", label: "Android TV" },
  { value: "android_tablet", label: "Android Tablet" },
  { value: "rpi_kiosk", label: "Raspberry Pi (Chromium)" },
  { value: "windows_pc", label: "Windows PC" },
  { value: "web_browser", label: "Web Browser" },
  { value: "unknown", label: "อื่น ๆ" },
];

export default function DevicesPage() {
  const { user } = useAuth();
  const toast = useToast();
  const canManage = hasRole(user, "super_admin", "admin");

  const [devices, setDevices] = useState<Device[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [pairingCodeFor, setPairingCodeFor] = useState<Device | null>(null);

  const load = async () => {
    try {
      const list = await api.get<Device[]>("/devices");
      setDevices(list);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "โหลด devices ไม่สำเร็จ");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRegenerate = async (device: Device) => {
    if (!confirm(`รีเซ็ต pairing code ของ "${device.name}"? Token เก่าจะใช้ไม่ได้`)) return;
    try {
      const updated = await api.post<Device>(`/devices/${device.id}/regenerate-pairing`);
      setDevices((prev) => prev?.map((d) => (d.id === device.id ? updated : d)) ?? null);
      setPairingCodeFor(updated);
      toast.success("รีเซ็ต pairing code สำเร็จ");
    } catch (e) {
      toast.error("รีเซ็ตไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          จัดการจอประชาสัมพันธ์ + ผูก player ผ่าน pairing code
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canManage && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> เพิ่มจอ
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {devices === null ? (
        <div className="flex justify-center py-12">
          <Spinner className="h-5 w-5 text-brand-600" />
        </div>
      ) : devices.length === 0 ? (
        <Empty title="ยังไม่มีจอในระบบ" description="กด 'เพิ่มจอ' เพื่อสร้าง pairing code" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>ชื่อ</TH>
              <TH>ตำแหน่ง</TH>
              <TH>แพลตฟอร์ม</TH>
              <TH>สถานะ</TH>
              <TH>Heartbeat ล่าสุด</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {devices.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50">
                <TD>
                  <Link href={`/devices/${d.id}`} className="font-medium text-brand-700 hover:underline">
                    {d.name}
                  </Link>
                  {d.tv_brand && (
                    <div className="text-xs text-slate-500">
                      {d.tv_brand} {d.tv_model}
                    </div>
                  )}
                </TD>
                <TD>{d.location || "—"}</TD>
                <TD className="text-xs">{d.platform}</TD>
                <TD>
                  <StatusBadge status={d.status} />
                  {d.status === "unpaired" && (
                    <span className="ml-1 text-xs text-slate-500">
                      ({STATUS_LABELS[d.status]})
                    </span>
                  )}
                </TD>
                <TD className="text-xs text-slate-500">
                  {d.last_heartbeat_at ? new Date(d.last_heartbeat_at).toLocaleString("th-TH") : "—"}
                </TD>
                <TD className="text-right">
                  {d.pairing_code && (
                    <Button variant="ghost" size="sm" onClick={() => setPairingCodeFor(d)}>
                      <Key className="h-3.5 w-3.5" /> ดู code
                    </Button>
                  )}
                  {canManage && d.status === "unpaired" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRegenerate(d)}
                      title="สร้าง pairing code ใหม่"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <CreateDeviceModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(d) => {
          setDevices((prev) => (prev ? [d, ...prev] : [d]));
          setPairingCodeFor(d);
        }}
      />

      <PairingCodeModal
        device={pairingCodeFor}
        onClose={() => setPairingCodeFor(null)}
      />
    </div>
  );
}

function CreateDeviceModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (d: Device) => void;
}) {
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [platform, setPlatform] = useState<DevicePlatform>("android_tv");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName("");
    setLocation("");
    setPlatform("android_tv");
    setError(null);
  };

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) {
      setError("ระบุชื่อจอ");
      return;
    }
    setLoading(true);
    try {
      const device = await api.post<Device>("/devices", {
        name: name.trim(),
        location: location.trim(),
        platform,
      });
      onCreated(device);
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
      title="เพิ่มจอใหม่"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            ยกเลิก
          </Button>
          <Button onClick={handleSubmit} loading={loading}>
            สร้าง + ออก pairing code
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">ชื่อจอ *</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="เช่น TV ลอบบี้" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">ตำแหน่ง</label>
          <Input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="เช่น ชั้น 1 ทางเข้า"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">แพลตฟอร์ม</label>
          <Select value={platform} onChange={(e) => setPlatform(e.target.value as DevicePlatform)}>
            {PLATFORM_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
        {error && <div className="text-sm text-rose-600">{error}</div>}
      </div>
    </Modal>
  );
}

function PairingCodeModal({
  device,
  onClose,
}: {
  device: Device | null;
  onClose: () => void;
}) {
  if (!device) return null;
  const expiresAt = device.pairing_code_expires_at
    ? new Date(device.pairing_code_expires_at).toLocaleString("th-TH")
    : null;

  return (
    <Modal open={!!device} onClose={onClose} title={`Pairing code: ${device.name}`}
      footer={<Button onClick={onClose}>ปิด</Button>}
    >
      <div className="text-center">
        {device.pairing_code ? (
          <>
            <div className="rounded-lg bg-slate-900 px-6 py-8 text-center font-mono text-4xl font-bold tracking-widest text-emerald-300">
              {device.pairing_code}
            </div>
            <p className="mt-3 text-sm text-slate-600">
              พิมพ์ code นี้ในแอป player เพื่อผูกอุปกรณ์
            </p>
            {expiresAt && (
              <p className="mt-1 text-xs text-slate-500">
                หมดอายุ: {expiresAt}
              </p>
            )}
          </>
        ) : (
          <p className="py-6 text-slate-500">
            จอนี้ paired แล้ว — ถ้าต้องการ re-pair กด &ldquo;รีเซ็ต&rdquo; จากตาราง
          </p>
        )}
      </div>
    </Modal>
  );
}
