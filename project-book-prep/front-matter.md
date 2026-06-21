# ส่วนหน้า (Front Matter)

> ปก / หน้าอนุมัติ / บทคัดย่อ / กิตติกรรมประกาศ — ช่อง `[...]` รอข้อมูลจากผู้จัดทำ

---

## ปก (Cover) — ข้อมูลที่ต้องกรอก

| รายการ | ค่า |
|---|---|
| ชื่อเรื่อง (ไทย) | การพัฒนาระบบจัดการจอประชาสัมพันธ์ดิจิทัล *(ปรับได้)* |
| ชื่อเรื่อง (อังกฤษ) | Development of a Digital Signage Management System *(ปรับได้)* |
| ชื่อ-สกุลผู้จัดทำ | [ชื่อนักศึกษา] |
| รหัสนักศึกษา | [รหัส] |
| สาขาวิชา | [สาขา เช่น วิทยาการคอมพิวเตอร์] |
| คณะ/สถาบัน | [คณะ / มหาวิทยาลัย] |
| สถานประกอบการที่ฝึกงาน | [หน่วยงาน — เช่น โรงพยาบาล/คณะฯ] |
| อาจารย์ที่ปรึกษา | [ชื่ออาจารย์ที่ปรึกษา] |
| ภาคเรียน / ปีการศึกษา | [เช่น 2/2568] |

---

## หน้าอนุมัติ (Approval Page)
- อาจารย์ที่ปรึกษา: ............................................... ( [ชื่อ] )
- กรรมการ: ............................................... ( [ชื่อ] )
- หัวหน้าสาขา/ผู้ลงนาม: ............................................... ( [ชื่อ] )

---

## บทคัดย่อ (ภาษาไทย)

ระบบจัดการจอประชาสัมพันธ์ดิจิทัล (Digital Signage Management System) พัฒนาขึ้นเพื่อแก้ปัญหาการบริหารจัดการจอประชาสัมพันธ์หลายจุดในองค์กรที่เดิมต้องอัปเดตเนื้อหาและควบคุมจอด้วยมือทีละเครื่อง โดยรวมการจัดการเนื้อหา การจัดผังการแสดงผล การกำหนดตารางเวลาออกอากาศ การควบคุมจอโทรทัศน์และจอ LED ระยะไกลผ่านโปรโตคอล HDMI-CEC และ RS-232 ตลอดจนการประกาศเหตุฉุกเฉิน ไว้ในระบบกลางเพียงระบบเดียว

ระบบพัฒนาด้วยสถาปัตยกรรมแบบบริการหลายส่วน (FastAPI, PostgreSQL, Redis, MinIO และ Next.js) ทำงานในรูปแบบคอนเทนเนอร์ด้วย Docker มีระบบสิทธิ์ผู้ใช้แบบ RBAC กระบวนการอนุมัติเนื้อหา การบันทึกประวัติการใช้งาน และการเฝ้าระวังสถานะอุปกรณ์ ส่วนแสดงผลรองรับการทำงานแบบ offline-friendly ผ่านไฟล์ manifest ผลการพัฒนาได้ระบบที่ใช้งานได้ครบวงจรตั้งแต่การอัปโหลดเนื้อหาจนถึงการแสดงผลบนจอจริง พร้อมการทดสอบอัตโนมัติประมาณ 133 กรณี

**คำสำคัญ:** ป้ายประชาสัมพันธ์ดิจิทัล, การจัดการเนื้อหา, การควบคุมทีวีระยะไกล, HDMI-CEC, RS-232, FastAPI

---

## ABSTRACT (English)

> [ ] แปลจากบทคัดย่อภาษาไทยด้านบน — โครงร่าง:

The Digital Signage Management System was developed to address the challenge of managing multiple public-display screens within an organization, which previously required manual content updates and screen control on a per-device basis. The system consolidates content management, layout composition, broadcast scheduling, remote control of televisions and LED displays via HDMI-CEC and RS-232 protocols, and emergency announcements into a single centralized platform.

Built on a multi-service architecture (FastAPI, PostgreSQL, Redis, MinIO, and Next.js) running in Docker containers, the system provides role-based access control (RBAC), a content approval workflow, audit logging, and device monitoring. The player component supports offline-friendly operation through manifest files. The result is a fully functional system covering the workflow from content upload to live on-screen display, accompanied by approximately 133 automated test cases.

**Keywords:** Digital Signage, Content Management, Remote TV Control, HDMI-CEC, RS-232, FastAPI

---

## กิตติกรรมประกาศ (Acknowledgements)

*(ข้อความขอบคุณสถานประกอบการ อาจารย์ที่ปรึกษา และผู้เกี่ยวข้อง)* — [ ] เติมเนื้อหาส่วนตัว
