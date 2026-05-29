"use client";
// Plans (playlists) — list + create/edit ที่มี drag-drop ordering
// ใช้ HTML5 drag-drop ปกติ (ไม่พึ่ง dnd-kit เพื่อไม่ต้องเพิ่ม dep)

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, RefreshCw, GripVertical, X, ListOrdered } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { Plan, PlanItemIn, Presentation } from "@/lib/types";
import {
  Button, Input, Select, Modal, Textarea, Empty, Spinner, Badge,
  TBody, TD, TH, THead, Table, Card, CardBody,
} from "@/components/ui";
import { useToast } from "@/components/toast";

export default function PlansPage() {
  const { user } = useAuth();
  const canEdit = hasRole(user, "super_admin", "admin", "editor");
  const toast = useToast();

  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [presentations, setPresentations] = useState<Presentation[]>([]);
  const [editing, setEditing] = useState<Plan | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const load = async () => {
    try {
      const [p, pr] = await Promise.all([
        api.get<Plan[]>("/plans"),
        api.get<Presentation[]>("/presentations"),
      ]);
      setPlans(p);
      setPresentations(pr);
    } catch (e) {
      toast.error("โหลดข้อมูลไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const handleDelete = async (p: Plan) => {
    if (!confirm(`ลบ plan "${p.name}" ?`)) return;
    try {
      await api.delete(`/plans/${p.id}`);
      setPlans((prev) => prev?.filter((x) => x.id !== p.id) ?? null);
      toast.success("ลบสำเร็จ");
    } catch (e) {
      toast.error("ลบไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  const presNameById = (id: string) => presentations.find((p) => p.id === id)?.name ?? id.slice(0, 8);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          Playlist — ลำดับของ presentation ที่จะเล่นต่อกัน (Tier 4 ใน 5-tier §35.1)
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canEdit && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> สร้าง plan
            </Button>
          )}
        </div>
      </div>

      {plans === null ? (
        <div className="flex justify-center py-12"><Spinner className="h-5 w-5 text-brand-600" /></div>
      ) : plans.length === 0 ? (
        <Empty title="ยังไม่มี plan" description="กด 'สร้าง plan' เพื่อจัดลำดับ presentation" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>ชื่อ</TH>
              <TH>คำอธิบาย</TH>
              <TH>จำนวน items</TH>
              <TH>Total duration</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {plans.map((p) => {
              const total = p.items.reduce((sum, it) => {
                const pres = presentations.find((x) => x.id === it.presentation_id);
                return sum + (it.duration_sec_override ?? pres?.duration_sec ?? 0);
              }, 0);
              return (
                <tr key={p.id} className="hover:bg-slate-50">
                  <TD className="font-medium">{p.name}</TD>
                  <TD className="text-sm text-slate-500">{p.description || "—"}</TD>
                  <TD><Badge variant="info">{p.items.length}</Badge></TD>
                  <TD className="text-xs">{total}s ({(total / 60).toFixed(1)} นาที)</TD>
                  <TD className="text-right">
                    {canEdit && (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => setEditing(p)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => handleDelete(p)}>
                          <Trash2 className="h-3.5 w-3.5 text-rose-600" />
                        </Button>
                      </>
                    )}
                  </TD>
                </tr>
              );
            })}
          </TBody>
        </Table>
      )}

      <PlanFormModal
        open={createOpen || editing !== null}
        editing={editing}
        presentations={presentations}
        onClose={() => { setCreateOpen(false); setEditing(null); }}
        onSaved={(p, mode) => {
          if (mode === "create") setPlans((prev) => prev ? [p, ...prev] : [p]);
          else setPlans((prev) => prev?.map((x) => x.id === p.id ? p : x) ?? null);
        }}
      />
    </div>
  );
}

function PlanFormModal({
  open, editing, presentations, onClose, onSaved,
}: {
  open: boolean;
  editing: Plan | null;
  presentations: Presentation[];
  onClose: () => void;
  onSaved: (p: Plan, mode: "create" | "edit") => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [items, setItems] = useState<PlanItemIn[]>([]);
  const [addId, setAddId] = useState("");
  const [loading, setLoading] = useState(false);

  // drag state
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editing) {
      setName(editing.name);
      setDescription(editing.description);
      setItems(
        editing.items
          .sort((a, b) => a.order_index - b.order_index)
          .map((it) => ({
            presentation_id: it.presentation_id,
            order_index: it.order_index,
            duration_sec_override: it.duration_sec_override,
          })),
      );
    } else {
      setName(""); setDescription(""); setItems([]); setAddId("");
    }
  }, [open, editing]);

  const presNameById = (id: string) => presentations.find((p) => p.id === id)?.name ?? id.slice(0, 8);
  const presDurationById = (id: string) =>
    presentations.find((p) => p.id === id)?.duration_sec ?? 30;

  const addItem = () => {
    if (!addId) return;
    setItems((prev) => [
      ...prev,
      { presentation_id: addId, order_index: prev.length, duration_sec_override: null },
    ]);
    setAddId("");
  };

  const removeItem = (idx: number) => {
    setItems((prev) =>
      prev.filter((_, i) => i !== idx).map((it, i) => ({ ...it, order_index: i })),
    );
  };

  // === drag handlers ===
  const onDragStart = (idx: number) => setDragIdx(idx);
  const onDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
  };
  const onDrop = (idx: number) => {
    if (dragIdx === null) return;
    setItems((prev) => {
      const next = [...prev];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(idx, 0, moved);
      return next.map((it, i) => ({ ...it, order_index: i }));
    });
    setDragIdx(null);
  };

  const updateDuration = (idx: number, value: string) => {
    const n = value === "" ? null : Number(value);
    setItems((prev) => prev.map((it, i) => i === idx ? { ...it, duration_sec_override: n } : it));
  };

  const handleSubmit = async () => {
    if (!name.trim()) { toast.error("ระบุชื่อ plan"); return; }
    if (items.length === 0) { toast.error("ต้องมี item อย่างน้อย 1 ตัว"); return; }
    setLoading(true);
    const body = { name: name.trim(), description: description.trim(), items };
    try {
      const saved = editing
        ? await api.patch<Plan>(`/plans/${editing.id}`, body)
        : await api.post<Plan>("/plans", body);
      onSaved(saved, editing ? "edit" : "create");
      toast.success(editing ? "บันทึกแล้ว" : "สร้าง plan สำเร็จ");
      onClose();
    } catch (e) {
      toast.error("บันทึกไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    } finally {
      setLoading(false);
    }
  };

  if (presentations.length === 0 && open) {
    return (
      <Modal open={open} onClose={onClose} title="ยังไม่มี presentation"
        footer={<Button onClick={onClose}>ปิด</Button>}>
        <p className="text-sm">ต้องสร้าง presentation อย่างน้อย 1 ตัวก่อน — ไปที่หน้า{" "}
          <a href="/presentations" className="text-brand-600 underline">Presentations</a></p>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? `แก้ไข: ${editing.name}` : "สร้าง plan ใหม่"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>ยกเลิก</Button>
          <Button onClick={handleSubmit} loading={loading}>บันทึก</Button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-sm font-medium">ชื่อ *</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">คำอธิบาย</label>
          <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">
            ลำดับ presentation ({items.length}) — ลากเพื่อจัดลำดับ
          </label>

          <div className="space-y-1 rounded border border-slate-200 bg-slate-50 p-2">
            {items.length === 0 && (
              <p className="py-2 text-center text-xs text-slate-500">ยังไม่มี item — เพิ่มด้านล่าง</p>
            )}
            {items.map((it, i) => (
              <div
                key={i}
                draggable
                onDragStart={() => onDragStart(i)}
                onDragOver={(e) => onDragOver(e, i)}
                onDrop={() => onDrop(i)}
                className={`flex items-center gap-2 rounded border bg-white px-2 py-1.5 text-sm ${
                  dragIdx === i ? "border-brand-400 opacity-50" : "border-slate-200"
                }`}
              >
                <GripVertical className="h-4 w-4 cursor-grab text-slate-400" />
                <span className="w-6 text-center text-xs text-slate-500">#{i + 1}</span>
                <span className="flex-1 truncate">{presNameById(it.presentation_id)}</span>
                <div className="flex items-center gap-1">
                  <Input
                    type="number"
                    value={it.duration_sec_override ?? ""}
                    onChange={(e) => updateDuration(i, e.target.value)}
                    placeholder={`${presDurationById(it.presentation_id)}`}
                    className="w-16 px-1 py-0.5 text-xs"
                  />
                  <span className="text-xs text-slate-400">s</span>
                </div>
                <button
                  onClick={() => removeItem(i)}
                  className="rounded p-1 text-rose-600 hover:bg-rose-50"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>

          {/* Add item */}
          <div className="mt-2 flex gap-2">
            <Select value={addId} onChange={(e) => setAddId(e.target.value)} className="flex-1">
              <option value="">— เลือก presentation —</option>
              {presentations.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.duration_sec}s)</option>
              ))}
            </Select>
            <Button onClick={addItem} disabled={!addId} size="md">
              <Plus className="h-3.5 w-3.5" /> เพิ่ม
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
