"use client";
// Presentations — layout composer (5-tier §35.1)
// 1 presentation = layout (zones) + content ที่ใส่ในแต่ละ zone

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, RefreshCw, Layers, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth, hasRole } from "@/lib/auth";
import type { Presentation, PresentationZoneIn, Content } from "@/lib/types";
import {
  Button, Input, Select, Modal, Textarea, Empty, Spinner, Badge,
  TBody, TD, TH, THead, Table,
} from "@/components/ui";
import { useToast } from "@/components/toast";

// preset layout เริ่มต้น — Pass 3 จะให้ user custom เพิ่ม
const LAYOUT_PRESETS = [
  {
    id: "fullscreen",
    name: "เต็มจอ (1 zone)",
    layout: { template: "fullscreen", zones: [{ key: "main", x: 0, y: 0, w: 100, h: 100 }] },
    zoneKeys: ["main"],
  },
  {
    id: "split_70_30",
    name: "70/30 (หลัก + sidebar)",
    layout: {
      template: "split_70_30",
      zones: [
        { key: "main", x: 0, y: 0, w: 70, h: 100 },
        { key: "side", x: 70, y: 0, w: 30, h: 100 },
      ],
    },
    zoneKeys: ["main", "side"],
  },
  {
    id: "main_ticker",
    name: "หลัก + ticker ล่าง",
    layout: {
      template: "main_ticker",
      zones: [
        { key: "main", x: 0, y: 0, w: 100, h: 85 },
        { key: "ticker", x: 0, y: 85, w: 100, h: 15 },
      ],
    },
    zoneKeys: ["main", "ticker"],
  },
];

export default function PresentationsPage() {
  const { user } = useAuth();
  const canEdit = hasRole(user, "super_admin", "admin", "editor");
  const toast = useToast();

  const [items, setItems] = useState<Presentation[] | null>(null);
  const [contents, setContents] = useState<Content[]>([]);
  const [editing, setEditing] = useState<Presentation | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const load = async () => {
    try {
      const [p, c] = await Promise.all([
        api.get<Presentation[]>("/presentations"),
        api.get<Content[]>("/contents"),
      ]);
      setItems(p);
      setContents(c.filter((x) => x.approval_status === "approved"));
    } catch (e) {
      toast.error("โหลดข้อมูลไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const handleDelete = async (p: Presentation) => {
    if (!confirm(`ลบ presentation "${p.name}" ?`)) return;
    try {
      await api.delete(`/presentations/${p.id}`);
      setItems((prev) => prev?.filter((x) => x.id !== p.id) ?? null);
      toast.success("ลบสำเร็จ");
    } catch (e) {
      toast.error("ลบไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-600">
          Presentation = layout + content ใน zones (Tier 3 ใน 5-tier §35.1)
        </p>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" /> รีเฟรช
          </Button>
          {canEdit && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-3.5 w-3.5" /> สร้าง presentation
            </Button>
          )}
        </div>
      </div>

      {items === null ? (
        <div className="flex justify-center py-12"><Spinner className="h-5 w-5 text-brand-600" /></div>
      ) : items.length === 0 ? (
        <Empty title="ยังไม่มี presentation" description="กด 'สร้าง' เพื่อ compose layout" />
      ) : (
        <Table>
          <THead>
            <tr>
              <TH>ชื่อ</TH>
              <TH>Template</TH>
              <TH>Zones</TH>
              <TH>Duration</TH>
              <TH className="text-right">การจัดการ</TH>
            </tr>
          </THead>
          <TBody>
            {items.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50">
                <TD>
                  <div className="font-medium">{p.name}</div>
                  {p.description && <div className="text-xs text-slate-500">{p.description}</div>}
                </TD>
                <TD className="text-xs">
                  <Badge variant="info">
                    <Layers className="mr-1 h-3 w-3" />
                    {(p.layout_json.template as string) || "—"}
                  </Badge>
                </TD>
                <TD>{p.zones.length}</TD>
                <TD>{p.duration_sec}s</TD>
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
            ))}
          </TBody>
        </Table>
      )}

      <PresentationFormModal
        open={createOpen || editing !== null}
        editing={editing}
        contents={contents}
        onClose={() => { setCreateOpen(false); setEditing(null); }}
        onSaved={(p, mode) => {
          if (mode === "create") setItems((prev) => prev ? [p, ...prev] : [p]);
          else setItems((prev) => prev?.map((x) => x.id === p.id ? p : x) ?? null);
        }}
      />
    </div>
  );
}

function PresentationFormModal({
  open, editing, contents, onClose, onSaved,
}: {
  open: boolean;
  editing: Presentation | null;
  contents: Content[];
  onClose: () => void;
  onSaved: (p: Presentation, mode: "create" | "edit") => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [duration, setDuration] = useState(30);
  const [presetId, setPresetId] = useState("fullscreen");
  // zone_key → content_id
  const [zoneContent, setZoneContent] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const preset = LAYOUT_PRESETS.find((p) => p.id === presetId)!;

  useEffect(() => {
    if (!open) return;
    if (editing) {
      setName(editing.name);
      setDescription(editing.description);
      setDuration(editing.duration_sec);
      const tpl = (editing.layout_json.template as string) || "fullscreen";
      setPresetId(LAYOUT_PRESETS.find((p) => p.id === tpl)?.id ?? "fullscreen");
      const map: Record<string, string> = {};
      editing.zones.forEach((z) => { map[z.zone_key] = z.content_id; });
      setZoneContent(map);
    } else {
      setName(""); setDescription(""); setDuration(30);
      setPresetId("fullscreen"); setZoneContent({});
    }
  }, [open, editing]);

  // เมื่อเปลี่ยน preset → reset zoneContent ให้ key ใหม่
  useEffect(() => {
    setZoneContent((prev) => {
      const next: Record<string, string> = {};
      for (const k of preset.zoneKeys) next[k] = prev[k] ?? "";
      return next;
    });
  }, [preset]);

  const handleSubmit = async () => {
    if (!name.trim()) { toast.error("ระบุชื่อ presentation"); return; }
    const missing = preset.zoneKeys.filter((k) => !zoneContent[k]);
    if (missing.length > 0) {
      toast.error(`ยังไม่ได้เลือก content ใน zone: ${missing.join(", ")}`);
      return;
    }

    setLoading(true);
    const zones: PresentationZoneIn[] = preset.zoneKeys.map((k, i) => ({
      zone_key: k,
      content_id: zoneContent[k],
      params_json: {},
      order_index: i,
    }));
    const body = {
      name: name.trim(),
      description: description.trim(),
      layout_json: preset.layout,
      duration_sec: duration,
      zones,
    };
    try {
      const saved = editing
        ? await api.patch<Presentation>(`/presentations/${editing.id}`, body)
        : await api.post<Presentation>("/presentations", body);
      onSaved(saved, editing ? "edit" : "create");
      toast.success(editing ? "บันทึกแล้ว" : "สร้างสำเร็จ");
      onClose();
    } catch (e) {
      toast.error("บันทึกไม่สำเร็จ", e instanceof ApiError ? e.message : undefined);
    } finally {
      setLoading(false);
    }
  };

  if (contents.length === 0 && open) {
    return (
      <Modal open={open} onClose={onClose} title="ไม่มี content ที่อนุมัติแล้ว"
        footer={<Button onClick={onClose}>ปิด</Button>}>
        <p className="text-sm">
          ต้องมี content ที่ <strong>approval_status = approved</strong> อย่างน้อย 1 ตัวก่อน — ไปอนุมัติที่หน้า
          <a href="/contents" className="ml-1 text-brand-600 underline">Contents</a>
        </p>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? `แก้ไข: ${editing.name}` : "สร้าง presentation ใหม่"}
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
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Layout</label>
            <Select value={presetId} onChange={(e) => setPresetId(e.target.value)}>
              {LAYOUT_PRESETS.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Duration (วินาที)</label>
            <Input type="number" min={1} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
          </div>
        </div>

        {/* Layout preview (ASCII zones) */}
        <div>
          <label className="mb-1 block text-sm font-medium">Preview</label>
          <LayoutPreview preset={preset} zoneContent={zoneContent} contents={contents} />
        </div>

        {/* Zone → content picker */}
        <div className="space-y-2">
          {preset.zoneKeys.map((k) => (
            <div key={k}>
              <label className="mb-1 block text-xs font-medium">
                Zone <code className="rounded bg-slate-100 px-1">{k}</code>
              </label>
              <Select value={zoneContent[k] ?? ""} onChange={(e) =>
                setZoneContent((prev) => ({ ...prev, [k]: e.target.value }))}>
                <option value="">— เลือก content —</option>
                {contents.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} [{c.type}]</option>
                ))}
              </Select>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
}

function LayoutPreview({
  preset,
  zoneContent,
  contents,
}: {
  preset: typeof LAYOUT_PRESETS[number];
  zoneContent: Record<string, string>;
  contents: Content[];
}) {
  const zones = preset.layout.zones as { key: string; x: number; y: number; w: number; h: number }[];
  return (
    <div className="relative h-32 w-full overflow-hidden rounded border border-slate-200 bg-slate-50">
      {zones.map((z) => {
        const cid = zoneContent[z.key];
        const c = contents.find((x) => x.id === cid);
        return (
          <div
            key={z.key}
            className="absolute flex items-center justify-center border border-brand-300 bg-brand-50 text-xs text-brand-700"
            style={{
              left: `${z.x}%`, top: `${z.y}%`,
              width: `${z.w}%`, height: `${z.h}%`,
            }}
          >
            <span className="truncate px-1">
              {z.key}{c ? `: ${c.name}` : " (ว่าง)"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
