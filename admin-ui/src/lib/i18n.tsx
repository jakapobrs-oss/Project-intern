"use client";
// i18n provider — th/en switcher + persist ใน localStorage
// ใช้ static dictionary lookup (ไม่พึ่ง react-intl/lingui เพื่อไม่ +deps)

import { createContext, useContext, useEffect, useState } from "react";

type Lang = "th" | "en";

type Dict = Record<string, string>;

// คำแปล — เพิ่มได้เรื่อยๆ
// key = ภาษาอังกฤษเป็นค่า default + ใช้เป็น identifier
const DICTIONARIES: Record<Lang, Dict> = {
  th: {
    "Dashboard": "แดชบอร์ด",
    "Devices": "จอ",
    "Groups": "กลุ่มจอ",
    "Contents": "สื่อ",
    "Presentations": "Presentations",
    "Plans": "Playlists",
    "Schedules": "ตารางเล่น",
    "TV Control": "ควบคุมจอ TV",
    "Emergency": "แจ้งเตือนฉุกเฉิน",
    "Audit log": "Audit log",
    "Users": "ผู้ใช้",
    "Login": "เข้าสู่ระบบ",
    "Logout": "ออกจากระบบ",
    "Username": "ชื่อผู้ใช้",
    "Password": "รหัสผ่าน",
    "Save": "บันทึก",
    "Cancel": "ยกเลิก",
    "Delete": "ลบ",
    "Edit": "แก้ไข",
    "Add": "เพิ่ม",
    "Refresh": "รีเฟรช",
    "Search": "ค้นหา",
    "Status": "สถานะ",
    "Actions": "การจัดการ",
    "Theme": "ธีม",
    "Language": "ภาษา",
    "Light mode": "โหมดสว่าง",
    "Dark mode": "โหมดมืด",
    "System": "ตามระบบ",
  },
  en: {
    // English ใช้ key ตรงๆ — empty dict ก็ได้
  },
};

interface I18nApi {
  lang: Lang;
  setLang: (l: Lang) => void;
  /** translate — fallback เป็น key ถ้าไม่มีคำแปล */
  t: (key: string) => string;
}

const I18nCtx = createContext<I18nApi | null>(null);
const STORAGE_KEY = "signage_lang";

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("th");

  useEffect(() => {
    const saved = (typeof window !== "undefined" && window.localStorage.getItem(STORAGE_KEY)) as Lang | null;
    if (saved === "th" || saved === "en") setLangState(saved);
  }, []);

  const setLang = (l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") window.localStorage.setItem(STORAGE_KEY, l);
    if (typeof document !== "undefined") document.documentElement.lang = l;
  };

  const t = (key: string): string => {
    const dict = DICTIONARIES[lang];
    return dict[key] ?? key;
  };

  return (
    <I18nCtx.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nCtx.Provider>
  );
}

export function useI18n(): I18nApi {
  const ctx = useContext(I18nCtx);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
