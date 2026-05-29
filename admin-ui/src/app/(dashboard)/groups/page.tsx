"use client";
// Player Groups — list + create/edit + เลือก device เป็นสมาชิก
// schedule ผูกกับ group (ไม่ใช่ device ตรงๆ) §35.1

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, RefreshCw, Monitor } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { PlayerGroup, Device } from "@/lib/types";
import {
  Button, Input, Modal, Textarea, Empty, Spinner, Card, CardBody, Badge,
  TBody, TD, TH, THead, Table,
} from "@/components/ui";
import { useToast } from "@/components/toast";

export default function GroupsPage() {
  const { user } = useAuth();
  const canManage = hasRole(user, "super_admin", "admin");
  const toast = useToast();

  const [groups, setGroups] = useState<PlayerGroup[] | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [editing, setEditing] = useState<PlayerGroup | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const load = async () => {
    try {
      const [g, d] = await Promise.all([
        api.get<PlayerGroup[]>("/groups"),
        api.get<Device[]>("/devices"),
      ]);
      setGroups(g);
      setDevices(d);
    } catch (e) {
      toast.error("โหลดข้อมูลไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const handleDelete = async (g: PlayerGroup) => {
    if (!confirm(`ลบ group "${g.name}" ?`)) return;
    try {
      await api.delete(`/groups/${g.id}`);
      setGroups((prev) => prev?.filter((x) => x.id !== g.id) ?? null);
      toast.success("ลบ group สำเร็จ");
    } catch (e) {
      toast.error("ลบไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const deviceNameById = (id: string) => devices.find((d) => d.id === id)?.name ?? id.slice(0, 8);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          กลุ่มจอ — schedule ผูกกับ group แทนที่จะผูกแต่ละจอ (§35.1)
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canManage && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> สร้างกลุ่ม
            </Button>
          )}
        </div>
      </div>

      {groups === null ? (
        <div className="flex justify-center py-12"><Spinner className="h-5 w-5 text-brand-600" /></div>
      ) : groups.length === 0 ? (
        <Empty title="ยังไม่มีกลุ่มจอ" description="กด 'สร้างกลุ่ม' เพื่อรวมจอเข้าด้วยกัน" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>ชื่อกลุ่ม</TH>
              <TH>คำอธิบาย</TH>
              <TH>จำนวนจอ</TH>
              <TH>จอในกลุ่ม</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {groups.map((g) => (
              <tr key={g.id} className="hover:bg-slate-50">
                <TD className="font-medium">{g.name}</TD>
                <TD className="text-sm text-slate-500">{g.description || "—"}</TD>
                <TD><Badge variant="info">{g.device_ids.length}</Badge></TD>
                <TD>
                  <div className="flex flex-wrap gap-1">
                    {g.device_ids.slice(0, 4).map((id) => (
                      <span key={id} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                        {deviceNameById(id)}
                      </span>
                    ))}
                    {g.device_ids.length > 4 && (
                      <span className="text-xs text-slate-400">+{g.device_ids.length - 4}</span>
                    )}
                  </div>
                </TD>
                <TD className="text-right">
                  {canManage && (
                    <>
                      <Button size="sm" variant="ghost" onClick={() => setEditing(g)}>
                        <Pencil className="h-3.5 w-3.5" /> แก้ไข
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(g)}>
                        <Trash2 className="h-3.5 w-3.5 text-rose-600" />
                      </Button>
                    </>
                  )}
                </TD>
              </tr>
            ))}
          </TBody>
        </Table>
      )}

      <GroupFormModal
        open={createOpen || editing !== null}
        editing={editing}
        devices={devices}
        onClose={() => { setCreateOpen(false); setEditing(null); }}
        onSaved={(g, mode) => {
          if (mode === "create") {
            setGroups((prev) => (prev ? [g, ...prev] : [g]));
          } else {
            setGroups((prev) => prev?.map((x) => (x.id === g.id ? g : x)) ?? null);
          }
        }}
      />
    </div>
  );
}

function GroupFormModal({
  open, editing, devices, onClose, onSaved,
}: {
  open: boolean;
  editing: PlayerGroup | null;
  devices: Device[];
  onClose: () => void;
  onSaved: (g: PlayerGroup, mode: "create" | "edit") => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setName(editing?.name ?? "");
      setDescription(editing?.description ?? "");
      setSelected(new Set(editing?.device_ids ?? []));
    }
  }, [open, editing]);

  const toggleDevice = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!name.trim()) { toast.error("ระบุชื่อกลุ่ม"); return; }
    setLoading(true);
    const body = {
      name: name.trim(),
      description: description.trim(),
      device_ids: Array.from(selected),
    };
    try {
      const saved = editing
        ? await api.patch<PlayerGroup>(`/groups/${editing.id}`, body)
        : await api.post<PlayerGroup>("/groups", body);
      onSaved(saved, editing ? "edit" : "create");
      toast.success(editing ? "บันทึกการแก้ไข" : "สร้างกลุ่มสำเร็จ");
      onClose();
    } catch (e) {
      toast.error("บันทึกไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? `แก้ไข: ${editing.name}` : "สร้างกลุ่มจอใหม่"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>ยกเลิก</Button>
          <Button onClick={handleSubmit} loading={loading}>บันทึก</Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">ชื่อกลุ่ม *</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="เช่น จอชั้น 1" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">คำอธิบาย</label>
          <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">
            จอในกลุ่ม ({selected.size} ตัว)
          </label>
          {devices.length === 0 ? (
            <p className="text-sm text-slate-500">ยังไม่มีจอในระบบ — ไปสร้างที่หน้า Devices ก่อน</p>
          ) : (
            <div className="max-h-60 overflow-y-auto rounded border border-slate-200">
              {devices.map((d) => (
                <label
                  key={d.id}
                  className="flex cursor-pointer items-center gap-2 border-b border-slate-100 px-3 py-2 last:border-0 hover:bg-slate-50"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(d.id)}
                    onChange={() => toggleDevice(d.id)}
                  />
                  <Monitor className="h-3.5 w-3.5 text-slate-400" />
                  <span className="flex-1 text-sm">{d.name}</span>
                  <span className="text-xs text-slate-500">{d.location || "—"}</span>
                  <span className="text-xs text-slate-400">{d.status}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
