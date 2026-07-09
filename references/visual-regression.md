# Visual regression — ให้ layer นี้เชื่อได้ ไม่ noise จนคนเลิกดู

`diff screenshot --baseline` (QA layer 3) มีอยู่แล้ว แต่ visual diff ดิบๆ พังง่าย: anti-aliasing
ต่างนิดเดียวก็แดง, วันที่/running number/timestamp เปลี่ยนทุกรอบก็แดง. พอ false-positive เยอะ คนก็
เลิกเชื่อแล้ว "อนุมัติผ่านๆ" — เท่ากับไม่มี layer นี้. ไฟล์นี้วางวินัย 3 อย่าง: **threshold, mask,
approval** เพื่อให้ diff แดง = regression จริง.

---

## 1. Threshold tolerance — กัน anti-aliasing false diff

pixel diff เป๊ะ 100% ไม่มีทางผ่าน (font rendering, sub-pixel ต่างเล็กน้อยทุกเครื่อง). ตั้ง
`diff_threshold` = สัดส่วน pixel ที่ต่างได้โดยไม่ถือเป็น fail:

```yaml
diff_threshold: 0.02      # default 2% — pixel ต่าง ≤ 2% = ผ่าน
```
- ค่าสูงไป (เช่น 10%) → กลืน regression จริง. ต่ำไป (0%) → แดงทุกรอบ.
- 2% เป็นจุดเริ่มที่ดีสำหรับ form ทั่วไป. ปรับตามหน้า: หน้าที่มี chart/graph animation อาจต้องสูงขึ้น
  แต่ให้ **mask ก่อน ไม่ใช่ดัน threshold ขึ้น** (§2) — threshold สูงเพื่อกลบ dynamic content คือกับดัก.

---

## 2. Masking dynamic content — ตัดส่วนที่เปลี่ยนทุกรอบออกจาก diff

running number, วันที่, timestamp, user name, session id เปลี่ยนทุกรอบโดยธรรมชาติ — ไม่ใช่ regression.
list CSS selector ของ region พวกนี้ใน `mask_regions` → diff จะ**ไม่นับพื้นที่นั้น** (เท่ากับถมทึบก่อนเทียบ):

```yaml
mask_regions:                      # default: [] — CSS selectors ของ dynamic content
  - ".running-number"              # เลขที่เอกสาร gen ใหม่ทุกครั้ง
  - "#trandate"                    # วันที่
  - "[data-test='timestamp']"
```

### ตัวอย่าง: mask running-number ให้ diff ไม่ false-positive
```yaml
# flow ที่หน้ามี running number เปลี่ยนทุก save
scenarios:
  - id: SC-INV-view
    steps:
      - intent: "เปิด record ที่เพิ่ง save"
        action: open
        target: "{{record_url}}"
        wait: networkidle
    mask_regions:
      - "#doc_number"              # running number: '.../INV0012' vs '.../INV0013' ทุกรอบ
    diff_threshold: 0.02
    # ผล: baseline vs รอบใหม่ ต่างแค่ตัวเลขใน #doc_number ซึ่งถูก mask → diff = 0% → PASS
    # ถ้าไม่ mask: ตัวเลขเปลี่ยน → diff แดงทุกรอบ (false-positive) → คนเลิกเชื่อ layer
```

**กติกา:** dynamic content → **mask**. อย่าใช้ threshold สูงกลบ (threshold ไว้กัน AA เท่านั้น).

---

## 3. Baseline approval workflow — ใคร/เมื่อไหร่/ยังไง update

baseline (`qa/<feature>/baseline/*.png`) คือ "ความจริงที่อนุมัติแล้ว". การเปลี่ยนมันต้องตั้งใจ:

- **update เมื่อไหร่:** เฉพาะเมื่อ UI เปลี่ยน**ตั้งใจ** (redesign, field ใหม่, ปุ่มย้าย) และ review แล้ว.
  ห้าม update เพื่อ "ทำให้ diff เขียว" ตอนเจอ regression — นั่นคือกลบ bug.
- **ใคร:** ตาม RACI ใน TEAM-PROCESS — QA (+agent) เสนอ, review โดย Tech Lead/QA Lead.
- **ยังไง:** commit baseline ใหม่ต้องมี **justification** ใน commit message (อ้าง ticket ที่ทำให้ UI เปลี่ยน)
  เช่น `chore(qa): update baseline SC-INV-view — new tax field (PROJ-91)`. baseline อยู่ใน repo
  ตาม feature (versioned) ไม่ใช่ในเครื่องใครคนเดียว.

---

## 4. Intentional change vs regression — แยกให้ขาด

เมื่อ diff แดง ต้องตอบก่อนว่า "ตั้งใจ หรือ regression":

```
diff แดง
  ├─ ส่วนที่แดงเป็น dynamic content (date/running number)? → ยังไม่ mask → เพิ่ม mask_regions, รันใหม่
  ├─ UI เปลี่ยนตรงกับ ticket ที่กำลังทำ (ตั้งใจ)?          → update baseline + justification (§3)
  └─ UI เปลี่ยนโดยไม่มี ticket / ไม่คาด (regression)?      → FAIL, เปิด bug (1 bug = 1 repro)
```
ห้ามข้ามขั้น "ถามว่าตั้งใจไหม" แล้ว update baseline อัตโนมัติ — นั่นทำให้ regression กลายเป็น baseline เงียบๆ.

---

## 5. Schema ใน flow.yaml + ต่อยอด diff เดิม

optional มี default (backward-compatible):
```yaml
scenarios:
  - id: SC-001
    mask_regions: []          # default: [] — CSS selectors ของ dynamic content
    diff_threshold: 0.02      # default: 0.02 (2%)
```
`diff screenshot --baseline` อ่าน 2 field นี้: mask selector ที่ระบุ (ถมก่อนเทียบ) แล้วตัดสิน
pass/fail ด้วย `diff_threshold`. flow เดิมที่ไม่ระบุ → ใช้ default (2%, ไม่ mask) เหมือนเดิม.

**Acceptance:** doc มี policy ครบ 3 (threshold §1 / mask §2 / approval §3); มีตัวอย่าง mask
running-number ที่ diff ไม่ false-positive (§2).
