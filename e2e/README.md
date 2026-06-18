# e2e/ — Browser E2E tests (puppeteer-core + Chrome)

ทดสอบ UI ของ project-intern แบบ **headless browser จริง** (ขับ Chrome ผ่าน puppeteer-core)
ย้ายมาจาก `web-demos` เพื่อให้ project-intern **self-contained** (มี `puppeteer-core` ของตัวเองใน `node_modules/`)

| ไฟล์ | ทดสอบอะไร |
|---|---|
| `login_e2e.mjs` | Admin UI: login `admin/ChangeMe123!` → เด้งเข้าแดชบอร์ด + ดึงข้อมูลจริง |
| `webplayer_e2e.mjs` | Web player: pair ผ่าน LAN → render เนื้อหาจาก manifest เต็มจอ |

## ต้องมีก่อนรัน
- stack รันอยู่: `docker compose up -d` (จากโฟลเดอร์แม่)
- Chrome ที่ `C:\Program Files\Google\Chrome\Application\chrome.exe` (ถ้าใช้ Edge/path อื่น แก้ตัวแปร `CHROME` ในสคริปต์)
- `npm install` (ลง puppeteer-core แล้ว — ทำครั้งเดียว)

## รัน
```powershell
# 1) Admin UI login (ต้องมี admin-ui ที่ :3000)
node login_e2e.mjs

# 2) Web player (ต้อง serve player + setup content ก่อน)
..\backend\.venv\Scripts\python.exe -m http.server 8080 --directory ..\player\web   # หน้าต่างค้างไว้
..\backend\.venv\Scripts\python.exe ..\emulator\_webplayer_setup.py                 # → จด PAIR_CODE
node webplayer_e2e.mjs <PAIR_CODE>
```

Screenshot ออกที่ `../user-test-demo/login-e2e.png` และ `../user-test-demo/webplayer-e2e.png`
