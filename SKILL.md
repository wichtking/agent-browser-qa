---
name: agent-browser-qa
description: >-
  Use this skill to actually drive a real browser through a web flow and produce QA
  results plus documentation from that live run. Trigger when the user wants to:
  smoke-test or QA a web app flow (login, checkout, wizard, form, grid); click through a
  UI step-by-step capturing screenshots at each step; do a visual check or
  visual-regression diff against a baseline; verify a form/row actually saved; test
  NetSuite/Suitelet/APEX or any page through the browser; or turn a real run into a
  user-guide or bug-report PDF (cover, table of contents, page numbers, annotated
  screenshots). Works for English or Thai requests, headless or headed, even when
  "agent-browser" isn't named. Do NOT trigger for writing Playwright/Cypress test code,
  setting up CI test pipelines, or pure file/CSV-to-PDF conversion with no browser run.
  Always read references/gotchas.md before driving the browser — several silent-failure
  traps (below-fold click, fake ✓Done, os 10060) live there.
---

# agent-browser QA & Docs

`agent-browser` = Rust CLI ([vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser)) ขับ Chrome ผ่าน CDP, output เป็น
accessibility tree + element ref (`@e1`) ที่ LLM อ่านง่าย. **ตัว CLI ไม่กิน token — token เกิด
เฉพาะตอน feed output กลับเข้า context.**

**บทบาท:** Claude = สมอง (อ่าน code → derive test → ตีความ pass/fail → เขียนเอกสาร).
agent-browser = มือ-ตา (ขับ browser + เก็บหลักฐาน ไม่ตัดสินอะไร).

**หลักการ one pass, two outputs:** เดิน happy path รอบเดียว → ได้ทั้ง (1) QA verdict และ
(2) วัตถุดิบ user guide/bug report.

---

## 1. ติดตั้ง (ครั้งแรก)

```bash
npm install -g agent-browser     # หรือ brew / cargo install agent-browser
agent-browser install            # โหลด Chrome for Testing (~186MB, ครั้งเดียว)
agent-browser --version          # ยืนยัน
```

คู่มือในตัวที่ version-matched (ดีกว่าเดาจาก --help): `agent-browser skills get core --full`

---

## 2. กฎทอง — อ่านก่อนขับ browser (สำคัญสุด)

กับดักเหล่านี้ทำให้ automation **พังเงียบ ไม่มี error** — รายละเอียด+หลักฐานเต็มใน
`references/gotchas.md` แต่จำ 3 ข้อนี้ให้ขึ้นใจ:

1. **`click` ไม่ auto-scroll** → ถ้าปุ่มอยู่ใต้ fold, click คืน `✓ Done` แต่ตกที่พื้นที่ว่าง
   ไม่ทำงานจริง. **เรียก `scrollintoview <sel>` ก่อน `click` เสมอ** สำหรับปุ่มท้ายฟอร์ม/ใต้จอ.
2. **อย่าเชื่อ `✓ Done`** — ต้อง assert state ผลลัพธ์ทุกครั้ง (`wait` element / `get url` /
   `get text .badge`). คลิกแล้วต้องพิสูจน์ว่าเกิดผล ไม่ใช่แค่คำสั่งคืนค่าสำเร็จ.
3. **เลี่ยง `wait --text` / `wait <selector>` แบบ long-poll** บน Windows (เจอ `os error 10060`
   เป็นระยะ) → ใช้ `wait --load networkidle` + เช็ค state ด้วยคำสั่งสั้นแทน.

เสริม: ถ้า native `click`/`find ... click` ยัง flaky ให้ขับด้วย **JS click**
`eval "document.querySelector('SEL').click()"` (ชัวร์เสมอ — ความคลิกได้จริงของแอปค่อย QA แยก).

---

## 3. Token discipline (กัน context ล้น)

- assertion ใช้คำสั่ง **ผลลัพธ์สั้น** เท่านั้น: `wait`, `is visible/enabled`, `get value/text`,
  `get count`, `errors --json`, `console --json`.
- **ห้าม** feed `snapshot` ทั้งหน้า หรือ `get html` ดิบกลับเข้า context. ถ้าต้อง snapshot ให้กรอง:
  `snapshot -i` (interactive-only) หรือ scope `-s "#sel"`.
- **screenshot = ไฟล์เสมอ** (`--json` คืนแค่ path) — path เข้า context ได้ ภาพไม่ (เว้นจำเป็นจริง).
- cap output: `--max-output 50000`.

Command reference เต็ม + syntax ที่พลาดบ่อย → `references/commands.md`

---

## 4. Workflow มาตรฐาน (one pass, two outputs)

```
1. open <url> → wait --load networkidle
2. ก่อนแต่ละ action: screenshot (ไฟล์) เก็บเป็นหลักฐาน/วัตถุดิบ guide
3. action: scrollintoview → click/fill (หรือ JS click) ด้วย ref @eN หรือ semantic locator
4. assert ผลลัพธ์ด้วยคำสั่งสั้น (กฎทองข้อ 2)
5. errors --json → ถ้าไม่ว่าง = FAIL บันทึก error (no silent fallback)
6. จบ flow: เขียน 2 ไฟล์ — qa-report.md (verdict) + user guide / bug report
```

QA 4 ชั้น: (1) Smoke = happy path จบ + errors ว่าง · (2) Functional = assert state ·
(3) Visual = `diff screenshot --baseline` · (4) Error surfacing = `errors`/`console` หลังทุก step สำคัญ.

โครง artifact แนะนำ:
```
qa/<feature>/
  qa-report.md          # verdict + ตาราง step + errors
  shots/                # screenshot ทุก step (artifact ไม่เข้า context)
  guide/                # เอกสารที่ generate (HTML/PDF) + shots
```

---

## 5. สร้างเอกสาร PDF (user guide / bug report)

ทำเอกสารคุณภาพระดับส่งจริง (ปก+โลโก้, สารบัญ+เลขหน้า, FAQ, glossary) จาก run จริง —
มี template พร้อมใช้ + recipe การทำ PDF ที่เลขหน้าตรง. **อ่าน `references/pdf-reports.md` ก่อนทำ PDF**
(มีกับดัก paged.js + Chrome printToPDF ที่ทำให้เกิดหน้าว่างสลับ).

- `assets/guide-template.html` — user guide สไตล์เอกสาร (cover, breadcrumb, screenshot ไฮไลต์,
  ตารางฟิลด์, คืออะไร/ทำไม/ผลต่อระบบ, FAQ, glossary). แก้แค่ data array.
- `assets/bug-report-template.html` — bug report (cover, สารบัญ+severity, Steps/Expected/Actual/
  Evidence/Workaround/Impact). แก้แค่ bug array.
- `assets/highlight.js` — snippet inject กรอบไฮไลต์ชี้จุดคลิกลง screenshot (ring-only, ไม่มีข้อความ).

หัวใจการทำ PDF: ออกแบบ HTML + paged.js → `agent-browser open <html>` → รอ ~6s ให้จัดหน้า →
`agent-browser pdf <out.pdf>`. **อย่า bake ข้อความไทยลง screenshot** (headless ไม่มีฟอนต์ไทย).

---

## เป้าหมายเฉพาะ (NetSuite / APEX)

- **NetSuite:** login ผ่าน Chrome profile ที่ login ไว้ (`--profile "Work"` เลี่ยง 2FA ซ้ำ);
  element ใน iframe → `frame "#sel"` ก่อน snapshot เสร็จแล้ว `frame main`; โหลด async →
  `wait --fn "window.jQuery && jQuery.active === 0"`.
- **Porjai APEX:** `--session porjai` แยก isolated; IG cell/button dynamic → semantic locator
  `find label "..." fill "..."` / `find role button click --name "..."`; ทดสอบ Thai input;
  `vitals --json` (ถ้ามีใน version นั้น — ตรวจก่อนใช้).
