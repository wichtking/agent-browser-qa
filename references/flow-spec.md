# Flow Spec — เขียน test case เป็นไฟล์ reproducible

test-design.md ตัดสิน *จะทดสอบอะไร*. ไฟล์นี้บอก *เก็บ test case ยังไงให้รันซ้ำได้* —
เขียน flow เป็น YAML declarative แทน ad-hoc command ต่อรอบ. รูปแบบเดียวกับ
`qa-runner-ui/flows/*.yaml` (มี runner ขับผ่าน UI ได้: `node server.js` → localhost:5170).

**ทำไมต้องเป็นไฟล์:** 1 flow file = 1 repro ถาวร (กติกา "1 bug = 1 repro"), diff ได้, รันซ้ำ
regression ได้, เติม vars ต่างค่าเพื่อยิง edge case ได้โดยไม่แก้ logic.

---

## Schema

```yaml
story: <slug>                    # id สั้นๆ ของ flow (ใช้ตั้งชื่อโฟลเดอร์ artifact)
title: <ชื่ออ่านเข้าใจ>          # ขึ้นหัว guide/report
ticket: <PROJ-123>               # (team) link กลับ requirement/ticket — ไหลเข้า qa-report + guide

vars:                            # ค่าที่ inject ผ่าน {{name}} — UI render เป็นช่องกรอก
  - { name: base_url, label: URL, default: "https://..." }
  - { name: password, label: Password, default: "x", secret: true }   # secret → input password

scenarios:
  - id: <scenario-id>
    doc: true                    # true = ใช้ scenario นี้ generate user-guide ด้วย
    requirement: <PROJ-123>      # (team) requirement ที่ scenario นี้ยืนยัน (override story.ticket)
    acceptance: >               # (team) Acceptance Criteria — Given/When/Then ที่ steps ต้องพิสูจน์
      Given ผู้ใช้ login แล้ว When กด Checkout Then ไปหน้า step-one
    steps:
      - intent: "<คำอธิบายคน — ขึ้นเป็น step ใน guide>"
        action: open|fill|click|select|press|scrollintoview|eval|wait
        target: "<selector | @eN | {{var}} | url>"
        value: "<ค่า/ข้อความ (สำหรับ fill/select) — รองรับ {{var}}>"
        wait: networkidle | <ms> | "<selector>"    # รอหลัง action
        assert:                  # พิสูจน์ผล (ตาม gotchas: อย่าเชื่อ ✓Done)
          url_contains: "/inventory.html"
          # หรือ: { target: ".shopping_cart_badge", contains: "1" }
```

**assert forms ที่ใช้บ่อย:** `url_contains: "..."` · `{ target: "<sel>", contains: "<text>" }`.
ทุก step ที่เปลี่ยน state **ควรมี assert** — ไม่งั้นเป็น false-pass (ดู gotchas ข้อ 2).

**Traceability (สำหรับทีม):** `ticket`/`requirement` + `acceptance` ทำให้ตอบได้ว่า *test นี้ยืนยัน
req ไหน* และ *req นี้ครอบด้วย scenario ไหน*. 1 acceptance criterion → 1 scenario (map 1:1) →
qa-report + user-guide อ้าง req เดียวกัน = ปิด loop req→test→doc. ดู `docs/TEAM-PROCESS.md`.

---

## Design → Spec → Run → Report (pipeline เต็ม)

0. **Requirement** — แต่ละ requirement/ticket → เขียน **Acceptance Criteria** (Given/When/Then).
1. **Design** (`test-design.md`) — จาก AC + อ่าน code → coverage matrix → list case (happy + adversarial).
   AC จับ "ฟีเจอร์ที่ควรมีแต่ไม่มี" (code-based test จับไม่ได้); code จับ branch/edge ที่ AC ไม่ครอบ.
2. **Spec** — แปลงแต่ละ case เป็น scenario ใน `qa/<feature>/flow.yaml` (ใส่ `requirement`+`acceptance`).
   - happy path: `doc: true` (ใช้ทำ guide).
   - adversarial: scenario แยก `doc: false` — ยิง edge value ผ่าน `vars` (ไทย/emoji/boundary/
     injection payload) แล้ว assert ว่า error **surface** (ไม่ใช่ Pass เงียบ).
3. **Run** — ขับตาม step. flow ยาว → รวบเป็น `batch` (ดู commands.md) คืน `run-log.json`.
   screenshot ทุก step เฉพาะ scenario `doc:true`; adversarial ถ่ายเฉพาะตอนเจอ bug.
4. **Report** — `qa-report.md` (ตาราง Phase 3) + ป้อน bug เข้า `assets/bug-report-template.html`,
   guide จาก scenario `doc:true` เข้า `assets/guide-template.html`.

โครง artifact:
```
qa/<feature>/
  flow.yaml            # test case ทั้งหมด (happy + adversarial scenarios)
  run-log.json         # ผลจาก batch --json (ลำดับคำสั่ง + ผลทุก step)
  shots/               # screenshot (artifact ไม่เข้า context)
  qa-report.md         # verdict + ตาราง case + severity
  guide/               # user-guide / bug-report ที่ generate
```

ตัวอย่างจริงพร้อมรัน: `qa-runner-ui/flows/saucedemo.yaml` (login→cart→checkout, css+assert ครบ).
