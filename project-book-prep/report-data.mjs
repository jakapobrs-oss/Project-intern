// ข้อมูลกลางของเล่มรายงาน — ใช้ร่วมกันทั้งตัวสร้าง PDF (build-report-pdf.mjs)
// และตัวสร้าง Word (build-report-docx.mjs) ใน E:\Claude-WorkSpace\web-demos
//
// ⭐ เล่มแยกรายคน (ส่งแยกกันคนละเล่ม): เลือกคนด้วย env var PERSON
//      PERSON=1 = จักรภพ (Backend, ค่าเริ่มต้น) · PERSON=2 = พรชนก (Frontend)
//      เช่น  PERSON=2 node build-report-pdf.mjs
//    เนื้อหาบทที่ต่างรายคน ใช้ directive [[P1]]...[[/P1]] / [[P2]]...[[/P2]] ใน ch*.md
//    (ส่วนที่อยู่นอก directive = เนื้อหาร่วม ปรากฏทั้งสองเล่ม)

// ---- ผู้จัดทำ 2 คน — โครงงานเดียวกัน แบ่งความรับผิดชอบ Backend / Frontend ----
export const PERSONS = [
  {
    key: 'jakapob',
    name_th: 'นายจักรภพ รามศักดิ์',
    name_en: 'Mr. Jakapob Ramsak',
    id: '6501209',
    role_th: 'นักพัฒนาระบบส่วนหลัง (Back-End Developer)',
    role_short_th: 'ระบบส่วนหลัง (Backend)',
    role_en: 'Back-End Developer',
    // ท่อน "งานที่ได้รับมอบหมาย" ในบทคัดย่อ (ต่อท้าย "...ได้มอบหมายให้ผู้จัดทำรับผิดชอบ")
    duty_th: 'การพัฒนาระบบส่วนหลัง ซึ่งประกอบด้วยการออกแบบและพัฒนา REST API ด้วย FastAPI การออกแบบฐานข้อมูล PostgreSQL ระบบสิทธิ์ผู้ใช้แบบ RBAC กระบวนการอนุมัติเนื้อหา การบันทึกประวัติการใช้งาน การควบคุมจอโทรทัศน์ระยะไกลผ่านโปรโตคอล HDMI-CEC และ RS-232 ตลอดจนชุดทดสอบอัตโนมัติ โดยระบบทั้งหมดทำงานในรูปแบบคอนเทนเนอร์ด้วย Docker ร่วมกับ Redis และ MinIO',
    duty_en: 'the development of the back-end system, covering the design and implementation of REST APIs with FastAPI, the PostgreSQL database design, role-based access control (RBAC), the content approval workflow, audit logging, remote television control via the HDMI-CEC and RS-232 protocols, and the automated test suite, with all services running in Docker containers alongside Redis and MinIO',
  },
  {
    key: 'phornchanok',
    name_th: 'นางสาวพรชนก ยมรัตน์',
    name_en: 'Miss Phornchanok Yomrat',
    id: '6507533',
    role_th: 'นักพัฒนาส่วนติดต่อผู้ใช้ (Front-End Developer)',
    role_short_th: 'ส่วนติดต่อผู้ใช้ (Frontend)',
    role_en: 'Front-End Developer',
    duty_th: 'การพัฒนาส่วนติดต่อผู้ใช้ ซึ่งประกอบด้วยส่วนจัดการสำหรับผู้ดูแล (Admin UI) พัฒนาด้วย Next.js และ TypeScript ครอบคลุมการจัดการเนื้อหา การจัดผังการแสดงผล การกำหนดตารางเวลาออกอากาศ การจัดการอุปกรณ์ และการประกาศเหตุฉุกเฉิน รวมถึงส่วนแสดงผล (Player) ที่รองรับการทำงานแบบ offline-friendly ผ่านไฟล์ manifest โดยออกแบบหน้าจอให้ทันสมัยและตอบสนองต่อการใช้งาน (responsive)',
    duty_en: 'the development of the user interface, covering the administrator console (Admin UI) built with Next.js and TypeScript for content management, layout composition, broadcast scheduling, device management, and emergency announcements, as well as the player component supporting offline-friendly playback through manifest files, with a modern and responsive screen design',
  },
];

// เลือกคนที่กำลัง build จาก env PERSON (1|2) — ไม่ตั้ง = คนที่ 1
export const PERSON_NO = Math.min(2, Math.max(1, Number(process.env.PERSON || '1') || 1));
const ME = PERSONS[PERSON_NO - 1];
const PARTNER = PERSONS[PERSON_NO % 2];
export const PERSON_KEY = ME.key;

// ---- สถานประกอบการ ----
export const COMPANY_TH = 'บริษัท บลูวินด์ โซลูชั่น จำกัด';
export const COMPANY_EN = 'Bluewind Solution Co., Ltd.'; // ชื่อทางการตามเว็บบริษัท (bluewindsolution.com)

// ---- ข้อมูลหน้าปก ----
export const COVER = {
  title_th: 'การพัฒนาระบบจัดการจอประชาสัมพันธ์ดิจิทัล',
  title_en: '(Development of a Digital Signage Management System)', // บรรทัดใต้ชื่อไทยบนปก
  title_en_meta: 'Development of a Digital Signage Management System', // หัวข้อในหน้า ABSTRACT
  names: [`${ME.name_th} ${ME.id}`],           // ปก + บล็อกข้อมูลบทคัดย่อ
  names_en: [`${ME.name_en} ID ${ME.id}`],     // บล็อกข้อมูลหน้า ABSTRACT
  names_plain: [ME.name_th],                   // ใบรับรอง (ไม่ใส่รหัสนักศึกษา)
  curriculum: 'วิทยาศาสตรบัณฑิต (วท.บ.)',
  curriculum_plain: 'วิทยาศาสตรบัณฑิต', // ใช้ในใบรับรอง (เล่มตัวอย่างไม่ใส่ตัวย่อ)
  curriculum_en: 'Bachelor of Science (B.Sc.)',
  major: 'วิทยาการคอมพิวเตอร์',
  major_en: 'Computer Science',
  faculty: 'วิทยาลัยนวัตกรรมดิจิทัลเทคโนโลยี',              // ตามเล่มตัวอย่าง (สาขา/คณะเดียวกัน)
  faculty_en: 'College of Digital Innovation Technology',   // ตามเล่มตัวอย่าง
  university: 'มหาวิทยาลัยรังสิต',
  year: '2569',
  year_en: '2026',
  // คำนำหน้า "ดร." ตามเล่มตัวอย่างเดชธนา (หน้าบทคัดย่อไทย) และให้ตรงกับ advisor_en
  advisor: 'ดร. อารีย์รัตน์ ส่งสกุลวัฒนา',
  advisor_en: 'Dr. Areerat Songsakulwattana',
  siteSupervisor: 'นางสาว ปิยวรรณ ทรัพย์แสนดี',
  siteSupervisor_en: 'Ms. Piyawan Sapsandee', // สะกดตามที่ผู้จัดทำระบุ
  deptHead: 'อาจารย์ สุพานิช อังศิริกุล', // หัวหน้าสาขาวิชาวิทยาการคอมพิวเตอร์ (ตามเล่มตัวอย่าง)
};

// ---- บทคัดย่อ (โครงตามเล่มตัวอย่าง: ย่อหน้า 1 บริบทสหกิจ+บทบาท · ย่อหน้า 2 งานที่ได้รับมอบหมาย+ผล) ----
export const ABS_TH = [
  `จากการปฏิบัติงานสหกิจศึกษา ณ ${COMPANY_TH} ซึ่งเป็นบริษัทผู้ให้บริการออกแบบและพัฒนาซอฟต์แวร์ ผู้จัดทำในฐานะ${ME.role_th} ได้มีส่วนร่วมในการพัฒนาระบบจัดการจอประชาสัมพันธ์ดิจิทัล (Digital Signage Management System) ซึ่งพัฒนาขึ้นเพื่อแก้ปัญหาการบริหารจัดการจอประชาสัมพันธ์หลายจุดในองค์กรที่เดิมต้องอัปเดตเนื้อหาและควบคุมจอด้วยมือทีละเครื่อง โดยรวมการจัดการเนื้อหา การจัดผังการแสดงผล การกำหนดตารางเวลาออกอากาศ การควบคุมจอโทรทัศน์และจอ LED ระยะไกล ตลอดจนการประกาศเหตุฉุกเฉิน ไว้ในระบบกลางเพียงระบบเดียว`,
  `ในการนี้ บริษัทฯ ได้มอบหมายให้ผู้จัดทำรับผิดชอบ${ME.duty_th} ระบบมีกระบวนการอนุมัติเนื้อหา การบันทึกประวัติการใช้งาน และการเฝ้าระวังสถานะอุปกรณ์ครบถ้วน ผลการพัฒนาได้ระบบที่ใช้งานได้ครบวงจรตั้งแต่การอัปโหลดเนื้อหาจนถึงการแสดงผลบนหน้าจอ โดยผ่านการทดสอบอัตโนมัติครบทั้ง 142 กรณี และการทดสอบแบบ End-to-End ครบทั้ง 10 ขั้นตอนบนฐานข้อมูล PostgreSQL จริง`,
];
export const KW_TH = 'ป้ายประชาสัมพันธ์ดิจิทัล, การจัดการเนื้อหา, การควบคุมทีวีระยะไกล, HDMI-CEC, RS-232, FastAPI';
export const ABS_EN = [
  `During the cooperative education internship at ${COMPANY_EN}, a software design and development company, the author served as a ${ME.role_en} and contributed to the development of the Digital Signage Management System. The system was developed to address the challenge of managing multiple public-display screens within an organization, which previously required manual content updates and per-device screen control, by consolidating content management, layout composition, broadcast scheduling, remote control of televisions and LED displays, and emergency announcements into a single centralized platform.`,
  `In this capacity, the company assigned the author the responsibility of ${ME.duty_en}. The system provides a content approval workflow, audit logging, and device monitoring. The result is a fully functional system covering the workflow from content upload to on-screen display, passing all 142 automated test cases and all 10 steps of the end-to-end test on a live PostgreSQL database.`,
];
export const KW_EN = 'Digital Signage, Content Management, Remote TV Control, HDMI-CEC, RS-232, FastAPI';

// ---- กิตติกรรมประกาศ (รายคน — ขอบคุณเพื่อนร่วมโครงงานอีกฝั่งด้วย) ----
export const ACK_TH = [
  `ปริญญานิพนธ์ฉบับนี้สำเร็จลุล่วงได้ด้วยความกรุณาและการสนับสนุนจากหลายฝ่าย ผู้จัดทำขอขอบพระคุณ ${COMPANY_TH} ที่ให้โอกาสเข้าปฏิบัติงานสหกิจศึกษาและเรียนรู้จากระบบงานจริง ขอขอบพระคุณ คุณปิยวรรณ ทรัพย์แสนดี ที่ปรึกษาสถานประกอบการ ที่ให้คำแนะนำด้านเทคนิคและการทำงานตลอดระยะเวลาการปฏิบัติงาน และขอขอบพระคุณ ${COVER.advisor} อาจารย์ที่ปรึกษา ที่ให้คำปรึกษาด้านวิชาการและการจัดทำปริญญานิพนธ์ฉบับนี้`,
  `ขอขอบคุณ ${PARTNER.name_th} เพื่อนร่วมโครงงานผู้รับผิดชอบ${PARTNER.role_short_th} ที่ร่วมคิด ร่วมพัฒนา และร่วมแก้ปัญหาด้วยกันมาตลอดการดำเนินโครงงาน ขอขอบคุณคณาจารย์ทุกท่านที่ประสิทธิ์ประสาทวิชาความรู้ ตลอดจนครอบครัวและเพื่อน ๆ ที่ให้กำลังใจและการสนับสนุนด้วยดีเสมอมา คุณประโยชน์ใดที่เกิดจากปริญญานิพนธ์ฉบับนี้ ผู้จัดทำขอมอบแด่ผู้มีพระคุณทุกท่าน`,
];
