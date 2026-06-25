# agent-browser — กับดักที่เจอจริง + วิธีแก้

รวมบั๊ก/ข้อจำกัด/ความเข้าใจผิดที่เสียเวลาไปจริง (agent-browser 0.27.0 · Windows 11 ·
Chrome for Testing headless). เรียงตามความสำคัญ. **อ่านก่อนเริ่มขับ browser** เพราะหลายอันทำให้
automation "ผ่านแบบหลอก" (false pass) ตรวจจับยาก.

## TOC
1. click ไม่ auto-scroll → silent no-op (สำคัญสุด)
2. อย่าเชื่อ `✓ Done` — assert state เสมอ
3. `os error 10060` บน long-poll wait
4. syntax ที่พลาดบ่อย (get attr / find / is)
5. headless ไม่มีฟอนต์ไทย
6. PDF viewer สคริปต์ไม่ได้ (shadow DOM)
7. JS click = ทางหนีที่ชัวร์

---

## 1. `click` ไม่เลื่อน element เข้า viewport → คลิก "เงียบ" ไม่ทำงาน [HIGH]

**อาการ:** สั่ง `click` element ที่อยู่ใต้ fold (นอก viewport แนวตั้ง) → CLI คืน `✓ Done`
แต่ event ไม่ถึง element จริง ไม่มีอะไรเกิดขึ้น และไม่มี error.

**พิสูจน์ (minimal repro):**
```
button rect:  top=952  innerH=568  inView=false
click "#b"          → ✓ Done
get text "#out"     → "count=0"        ← ไม่เปลี่ยน (no-op!)
# หลักฐานเชิงลึก: listener บนปุ่มจับ click ได้ []; document listener จับที่ target=HTML
# (พื้นที่ว่าง); elementFromPoint(จุดคลิก)=ปุ่มถูกต้อง, ไม่มี overlay, DPR=1
```

**แก้:** `scrollintoview <sel>` ก่อน `click` เสมอ →
```
scrollintoview "#b"   # ปุ่มเลื่อนมา inView=true
click "#b"            # ทำงานทันที → count=1 trusted=true
```

**ผลกระทบ:** ร้ายแรง — สคริปต์ผ่านแบบหลอกเพราะ click คืน Done โดยไม่ error. ปุ่มท้ายฟอร์ม
(Continue/Finish/Cancel) มักอยู่ใต้ fold → โดนบ่อย. ในจอ (in-viewport) click ทำงานปกติ.

---

## 2. อย่าเชื่อ `✓ Done` — assert state ผลลัพธ์เสมอ [HIGH]

`✓ Done` แปลว่า "คำสั่งทำงานเสร็จ" ไม่ใช่ "เกิดผลลัพธ์ตามตั้งใจ". หลัง action ที่เปลี่ยน state
ต้องพิสูจน์ด้วยคำสั่งสั้น:
- หลัง click ที่นำทาง → `get url` (เช็ค url เปลี่ยน) หรือ `wait --load networkidle`
- หลัง add-to-cart → `wait "[data-test=remove-...]"` หรือ `get text ".badge"`
- หลังกรอกฟอร์ม → `get value` ยืนยันค่าเข้า

อ่าน state ทันทีหลัง click บางครั้ง race (ยังไม่ render) → ใช้ `wait <selector ผลลัพธ์>` แทนการ
อ่านดิบ. การ "อ่านเร็วเกิน + chain หลุด" ทำให้เข้าใจผิดว่า click ไม่ติดทั้งที่ติด.

---

## 3. `os error 10060` (connection timeout) บน long-poll wait [MEDIUM]

**อาการ:** `wait --text "..."` หรือ `wait "[selector]"` บางครั้งโยน
`✗ Failed to read: A connection attempt failed ... (os error 10060)` ระหว่าง flow ต่อเนื่อง
(TCP connect timeout ไม่ใช่ timeout ปกติ) แล้ว command ถัดมา fail ต่อ (chain หลุด).

**แก้:** เลี่ยง element/text-wait แบบ long-poll → ใช้ `wait --load networkidle` + เช็ค state
ด้วยคำสั่งสั้น (`get url` / `get count`). สำหรับ clientside toggle (เช่น add-to-cart) ใช้
`wait <ms สั้นๆ>` + verify. ทำเป็นช่วงสั้นๆ ต่อ bash call ลดโอกาส daemon สะดุด.

---

## 4. Syntax ที่พลาดบ่อย [LOW — แต่เสียเวลา debug]

- **`get attr <selector> <name>`** — selector มาก่อน! `get attr @e2 href` ✓.
  สลับเป็น `get attr href @e2` → คืน `Element not found` (ชี้สาเหตุผิด).
- **`find <locator> <value> <action> [--flags]`** — action มาก่อน, ชื่อใส่ flag:
  `find role button click --name "Submit"` ✓. ไม่ใช่ `find role button "Submit" click`.
- **`is` ไม่ใช่ subaction ของ `find`** — เช็ค visibility ด้วยคำสั่งแยก `is visible @ref`.
- **ref จาก `snapshot -i` (เช่น `@e2`) ใช้ข้าม CLI invocation ได้** (daemon เก็บ browser ไว้);
  chain ด้วย `&&`. แต่ ref จะ stale ถ้าหน้า re-render/navigate → snapshot ใหม่.

---

## 5. headless Chrome for Testing ไม่มีฟอนต์ไทย [LOW]

ข้อความไทยที่ **render/วาดใน headless** (เช่น label ที่ inject เองด้วย `font: ... sans-serif`)
กลายเป็นกล่อง □□□. แต่ HTML ที่เปิดในเบราว์เซอร์ผู้ใช้ render ไทยปกติ.

**แก้:** อย่า bake ข้อความไทยลง screenshot ใน headless — ใส่แค่กรอบ/ไฮไลต์เปล่าๆ (ดู
`assets/highlight.js`) แล้วเขียนข้อความไทยใน HTML/เอกสาร. หรือกำหนด font stack ที่มี glyph ไทย.

---

## 6. Chrome PDF viewer สคริปต์ไม่ได้ [LOW]

หน้า PDF ใน Chrome อยู่ใน `<embed>`/shadow DOM — `elementFromPoint` คืน BODY, `PageDown` /
`#page=N` / คลิก thumbnail **ไม่ทำงานผ่าน CDP**. ถ้าต้องอ่าน PDF อ้างอิงให้ screenshot ทีละหน้า
(แต่ก็เลื่อนหน้าไม่ได้ง่ายๆ) — ทางที่ดีกว่าคือแปลง PDF→ข้อความ/ภาพด้วยเครื่องมืออื่นถ้ามี.

---

## 7. JS click = ทางหนีที่ชัวร์ตอนเก็บ screenshot/เดิน flow

ถ้า native `click` / `find ... click` flaky (ข้อ 1) และเป้าหมายคือ "เดิน flow ให้ถึงสถานะที่
อยากถ่ายรูป" (ไม่ใช่ทดสอบความคลิกได้ของแอป) → ขับด้วย JS click:
```
eval "document.querySelector('SEL').click()"
```
พิสูจน์แล้วว่า fire React/handler ชัวร์เสมอ. แยกการ QA "ความคลิกได้จริง" ออกไป assert ใน
qa-report ต่างหาก. ใช้คู่กับ `get url`/`get count` ยืนยันผลทุกครั้ง.
