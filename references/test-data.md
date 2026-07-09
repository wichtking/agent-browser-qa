# Test data — ให้ regression รอบที่ 2 เชื่อได้

target ของ skill นี้ (NetSuite / APEX) เป็น **stateful** — record ที่ seed หรือสร้างระหว่าง run
ค้างอยู่จริง. ถ้าไม่จัดการ test data รอบสองจะเจอ "ชื่อซ้ำ", "running number ชน", หรือ pass เพราะ
record เก่าค้าง (false pass). ไฟล์นี้วางกติกา **setup → run → teardown ที่ idempotent** + cleanup
ที่ปลอดภัย.

Adversarial pass (double-submit, duplicate running number) จงใจทำให้เกิด state ค้าง — ต้อง reset
ก่อนรอบถัดไป ไม่งั้น bug รอบก่อนจะปนผลรอบใหม่.

---

## 1. Fixtures & idempotency

**Fixture** = ข้อมูลตั้งต้นที่ scenario ต้องใช้ (ลูกค้า, item, งบ, sublist ตั้งต้น). กติกา:

- **Idempotent เสมอ** — รัน seed ซ้ำต้องไม่พัง และไม่สร้างซ้ำ. รูปแบบ: *identify แล้วค่อยตัดสิน*
  (มีอยู่แล้ว → update/skip, ไม่มี → create). ห้าม "create แล้วหวังว่าไม่ซ้ำ".
- **Marker ที่ระบุตัวได้** — ทุก record ที่ test สร้าง ต้องติด marker ที่ query กลับมาเจอได้แน่ๆ
  (external id / custom field). ใช้ prefix `QA_` + **3-letter topic prefix** (เช่น `QA_SO_`, `QA_INV_`)
  เพื่อ cleanup แบบ scope แคบ ไม่โดน production data.
- **แยก data ของแต่ละ scenario** — อย่าให้ scenario A แก้ record ที่ scenario B พึ่งพา.

รูปแบบ setup ที่ idempotent (pseudo):
```
seed(marker):
  rows = identify(marker)          # query ก่อน (ดู §3 SuiteQL-first)
  if rows: return rows             # มีแล้ว → ใช้ซ้ำ (idempotent)
  return create(with marker)       # ไม่มี → สร้าง แล้วติด marker
```

---

## 2. Isolation — reset state ระหว่างรอบ

หลัง run ที่เปลี่ยน state (โดยเฉพาะ adversarial) ต้องคืนสภาพก่อนรอบถัดไป:

- **หลัง happy path** — ถ้า scenario สร้าง transaction จริง (SO/PO/adjustment) ให้ teardown ลบ/void
  เฉพาะ record ที่ marker ตรง (ดู §3, §5).
- **หลัง adversarial** — double-submit อาจสร้าง 2 record, duplicate running number อาจทิ้ง sequence
  ค้าง. บันทึกว่าเกิดอะไร แล้ว cleanup ให้กลับ baseline.
- **ลำดับ** — setup (idempotent) → run → assert → teardown (scoped). ถ้า teardown fail ต้อง
  **surface error + ไม่ mark รอบถัดไปว่า clean** (no silent fallback).

---

## 3. NetSuite

### 3.1 Marker + identify
Test record ติด custom field / external id ด้วย prefix `QA_<TOPIC>_` (topic = 3 ตัวอักษร). ทำให้
cleanup query เจาะจงได้ ไม่ต้องเดา.

### 3.2 Cleanup แบบ SuiteQL-first (identify ก่อน delete)
**ห้ามใช้ `N/search` เพื่อหา record ที่จะลบ** — ใช้ **SuiteQL** identify ให้เห็น id ที่จะโดนก่อน
แล้วค่อย delete ทีละ id ที่ยืนยันแล้ว. เหตุผล: SuiteQL ให้ query ที่ตรวจ/diff/log ได้ชัดว่าจะลบอะไร.

ตัวอย่าง identify-before-delete (SuiteQL):
```sql
-- STEP 1 identify: ดูก่อนว่าจะลบอะไร (log ผลนี้ไว้เป็นหลักฐาน)
SELECT id, tranid, trandate
FROM transaction
WHERE externalid LIKE 'QA_SO_%'          -- scope แคบด้วย marker
  AND trandate >= '2026-07-01'           -- ขอบเขตเวลา ห้าม broad
ORDER BY id;
-- STEP 2 delete: วนลบเฉพาะ id ที่ STEP 1 คืน (record.delete ต่อ id) — ไม่ลบด้วย criteria กว้างๆ
```
กติกา: STEP 1 ต้องรัน + log ก่อน STEP 2 เสมอ. ลบด้วย **list ของ id ที่ยืนยันแล้ว** ไม่ใช่ criteria
(กัน where เพี้ยนแล้วกวาดของจริง). ดู `netsuite-suiteql` / `ns-suiteql` skill สำหรับ syntax.

### 3.3 Lot / Serial / Subsidiary state
- Lot/serial number, subsidiary scope, inventory balance บางส่วน **reset ผ่าน browser ไม่ได้** →
  mark เป็น **code-only** ใน coverage.yaml (`verifiable: code-only`) แล้วให้ Dev reset ผ่าน script/DB.
  อย่า mark Pass ถ้า reset ไม่ได้จริง.
- ถ้า reset ได้ผ่าน UI (เช่น void transaction, adjust คืน) → ทำใน teardown แบบ scoped.

### 3.4 TWMS Ship / Outbound — realtime เท่านั้น
ถ้า flow แตะ Ship/Outbound critical path: **ห้ามเสนอ async / Map-Reduce / Scheduled Script**
ในการ setup หรือ teardown. path นี้ต้อง realtime — setup/cleanup ต้องเป็น realtime call เท่านั้น
(สอดคล้อง test-design.md add-on: ตรวจว่าไม่มี async แทรกใน critical path).

---

## 4. APEX (Oracle)

- **Seed ผ่าน SQL script** — ไม่ใช่คลิกมือใน UI. เก็บ seed เป็นไฟล์ .sql ที่รันซ้ำได้.
- **Isolation:** ใช้ **transaction rollback** (seed → run → rollback) หรือ **dedicated test schema**
  แยกจาก production. อย่าปนกับ data จริง.
- **Cleanup order ตาม FK** — ลบ child ก่อน parent (เรียงตาม foreign key) ไม่งั้น constraint error.
- ทดสอบ Thai input ทุกครั้ง (ดู test-design.md); dynamic IG cell → semantic locator.

---

## 5. Destructive guard (บังคับทุก teardown)

teardown ที่ **ลบข้อมูล** ต้อง:
1. **ระบุขอบเขตชัด** — marker `QA_<TOPIC>_` + ขอบเขตเวลา/subsidiary. **ห้าม broad criteria**
   (ห้าม `DELETE ... WHERE type = 'SalesOrd'` เฉยๆ).
2. **identify ก่อน (SuiteQL-first) + log** รายการที่จะลบ ให้คนเห็นก่อน delete.
3. **ยืนยันก่อนลบ** — ถ้าจำนวนที่จะลบเกินคาด (เช่น > N) ให้หยุดถามก่อน ไม่ลบอัตโนมัติ.
4. ลบด้วย **list ของ id ที่ยืนยันแล้ว** ไม่ใช่ criteria กว้าง.
5. teardown fail → **surface error + exit non-zero** ห้ามกลืนเงียบ.

---

## 6. Schema ใน flow.yaml (fixtures / teardown)

field ใหม่ **optional** — flow เดิมที่ไม่มียังรันได้ปกติ (backward-compatible). ดู `flow-spec.md` §schema.
```yaml
# ระดับไฟล์ (หรือผูก scenario)
fixtures:
  - id: FX-001
    setup: seed/qa_so_seed.sql          # ref ไป seed script / SuiteQL / SQL
    idempotent: true                    # ต้องรันซ้ำได้
teardown:
  - cleanup/qa_so_cleanup.md            # ref cleanup ที่มี destructive guard (§5)
```
`setup`/teardown เก็บเป็น **ref ไปไฟล์** (script/SQL/doc) ไม่ฝัง logic ลง flow.yaml —
รักษาหลัก brain/hands (flow.yaml บอก *อะไร*, script ทำ *ยังไง*).

**Acceptance ของ Phase นี้:** มี pattern setup→run→teardown idempotent (§1–2), มีตัวอย่าง
SuiteQL identify-before-delete (§3.2), flow เดิมที่ไม่มี fixtures/teardown ยังรันได้ (optional §6).
