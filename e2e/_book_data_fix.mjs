// เตรียมข้อมูลเดโมสำหรับรูปเล่มบท 4 (ครั้งเดียวทิ้ง)
// - ลบ content ชื่อเพี้ยน (???) ที่เกิดจากส่งไทยผ่าน curl/git-bash
// - สร้างใหม่: โปสเตอร์ (pending รออนุมัติ) + แผนที่ OSM (approved)
// - ชี้ presentation "หน้าจอต้อนรับ" → แผนที่ + เปลี่ยนชื่อ
const API = 'http://localhost:8000';

async function api(method, path, body, token, form = false) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (body !== undefined) {
    headers['Content-Type'] = form ? 'application/x-www-form-urlencoded' : 'application/json';
    payload = form ? new URLSearchParams(body).toString() : JSON.stringify(body);
  }
  const r = await fetch(API + path, { method, headers, body: payload });
  const text = await r.text();
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status} ${text.slice(0, 200)}`);
  return text ? JSON.parse(text) : null;
}

const { access_token: T } = await api('POST', '/api/v1/auth/login',
  { username: 'admin', password: 'ChangeMe123!' }, null, true);

// ลบ content ที่ชื่อกลายเป็น ??? (สร้างพลาดเมื่อครู่)
const contents = await api('GET', '/api/v1/contents?page_size=100', undefined, T);
for (const c of (contents.items ?? contents)) {
  if (/^\?+$/.test(c.name)) {
    await api('DELETE', `/api/v1/contents/${c.id}`, undefined, T);
    console.log('deleted mojibake content:', c.id);
  }
}

// โปสเตอร์รณรงค์ — จงใจปล่อยค้างสถานะ "รออนุมัติ" ให้เห็น approval workflow ในรูป
const poster = await api('POST', '/api/v1/contents/url', {
  name: 'โปสเตอร์สัปดาห์ล้างมือโลก', description: 'สื่อรณรงค์จากงานสื่อสารองค์กร',
  type: 'web', url: 'https://www.who.int/campaigns/world-hand-hygiene-day',
}, T);
await api('POST', `/api/v1/contents/${poster.id}/submit`, undefined, T);
console.log('poster pending:', poster.id);

// แผนที่ OSM (iframe ได้) — approved แล้วใช้เป็นเนื้อหาบนจอ player
const map = await api('POST', '/api/v1/contents/url', {
  name: 'แผนที่เส้นทางภายในโรงพยาบาล', description: 'จอบอกทางสำหรับผู้มารับบริการ',
  type: 'web',
  url: 'https://www.openstreetmap.org/export/embed.html?bbox=100.5195%2C13.7605%2C100.5335%2C13.7715&layer=mapnik&marker=13.7659%2C100.5265',
}, T);
await api('POST', `/api/v1/contents/${map.id}/submit`, undefined, T);
await api('POST', `/api/v1/contents/${map.id}/approve`, { approve: true }, T);
console.log('map approved:', map.id);

// ชี้ presentation หน้าจอต้อนรับ → แผนที่
const pres = await api('GET', '/api/v1/presentations', undefined, T);
const p = pres.find((x) => x.name === 'หน้าจอต้อนรับ' || x.name === 'หน้าจอต้อนรับและบอกทาง');
if (!p) throw new Error('ไม่พบ presentation หน้าจอต้อนรับ');
const upd = await api('PATCH', `/api/v1/presentations/${p.id}`, {
  name: 'หน้าจอต้อนรับและบอกทาง',
  zones: [{ zone_key: 'main', content_id: map.id, order_index: 0, params_json: {} }],
}, T);
console.log('presentation:', upd.name, '→ map zone OK');
console.log('DATA_FIX_DONE');
