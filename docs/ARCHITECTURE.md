# ARCHITECTURE — agent-browser-qa

สถาปัตยกรรม + workflow diagrams (mermaid) ทุก flow. GitHub render mermaid ได้ในตัว.
สรุปสั้นอยู่ใน [`../README.md`](../README.md) · กับดัก/วิธีแก้ดู [`../references/gotchas.md`](../references/gotchas.md)

## TOC
1. [ภาพรวม: one pass, two outputs](#1-ภาพรวม-one-pass-two-outputs)
2. [Golden-rule action loop (click อย่างปลอดภัย)](#2-golden-rule-action-loop)
3. [QA 4 ชั้น](#3-qa-4-ชั้น)
4. [User-guide / Bug-report PDF pipeline (paged.js)](#4-pdf-pipeline-pagedjs)
5. [Highlight capture sub-flow](#5-highlight-capture-sub-flow)
6. [เป้าหมาย & setup (Web / NetSuite / APEX)](#6-เป้าหมาย--setup)

---

## 1. ภาพรวม: one pass, two outputs

เดิน happy path **รอบเดียว** → แตกเป็น (1) QA verdict และ (2) วัตถุดิบเอกสาร. Claude เป็นสมอง,
agent-browser เป็นมือ-ตา, CDP คุย Chrome. ใช้คำสั่ง **ผลสั้น** เพื่อกัน context ล้น.

```mermaid
sequenceDiagram
    participant U as ผู้ใช้
    participant C as Claude (สมอง)
    participant A as agent-browser (มือ-ตา)
    participant B as Chrome / CDP
    U->>C: "QA หน้า X แล้วทำคู่มือ/รายงาน"
    C->>A: open <url> ; wait --load networkidle
    A->>B: นำทาง + รอจน idle
    loop ทุก step
        C->>A: scrollintoview → screenshot (ไฟล์)
        C->>A: click / fill  (หรือ JS click ถ้า flaky)
        A->>B: ทำ action
        C->>A: assert (wait / get url / get text / get count)
        C->>A: errors --json
        A-->>C: ผลสั้น (token-safe)
    end
    C->>C: ① qa-report.md (verdict + ตาราง step)
    C->>C: ② HTML (template) + paged.js → pdf
    C-->>U: QA verdict + PDF (guide / bug-report)
```

---

## 2. Golden-rule action loop

หัวใจที่กัน **false pass**: เลื่อนเข้า viewport ก่อนคลิก, ถ้า native click ไม่ติดให้ใช้ JS click,
แล้ว **assert ผลลัพธ์เสมอ** — อย่าเชื่อ `✓ Done`.

```mermaid
flowchart TD
    a["ต้องการ interact element"] --> b{"อยู่ใน viewport?"}
    b -->|"ใต้ fold / ไม่แน่ใจ"| c["scrollintoview &lt;sel&gt;"]
    b -->|ใช่| d["click / fill &lt;sel&gt;"]
    c --> d
    d --> e{"เกิดผลจริงไหม?<br/>(re-render / nav)"}
    e -->|"ไม่ (native click flaky)"| f["eval: querySelector(sel).click()"]
    f --> g
    e -->|"ดูเหมือนเกิด"| g["assert state<br/>wait / get url / get count"]
    g --> h{"ผลลัพธ์ตรงคาด?"}
    h -->|ไม่| x["❌ FAIL → errors --json → บันทึก"]
    h -->|ใช่| ok["✅ ผ่าน step → ถัดไป"]
```

---

## 3. QA 4 ชั้น

```mermaid
flowchart LR
    s["1 · Smoke<br/>happy path จบ<br/>+ errors ว่าง"] --> f["2 · Functional<br/>assert state<br/>ด้วยคำสั่งสั้น"]
    f --> v["3 · Visual<br/>diff screenshot<br/>--baseline"]
    v --> e["4 · Error surfacing<br/>errors/console<br/>หลังทุก step สำคัญ"]
```

| ชั้น | ทำเมื่อ | คำสั่งหลัก | เกณฑ์ผ่าน |
|---|---|---|---|
| Smoke | ทุก commit | `open` · `wait` · `errors` | flow จบ + errors ว่าง |
| Functional | feature สำคัญ | `is` · `get` · `wait` | state ตรงคาดทุก step |
| Visual | UI เปลี่ยน | `diff screenshot --baseline` | diff อยู่ในเกณฑ์ |
| Error surfacing | ทุก step สำคัญ | `errors --json` · `console --json` | error ต้องโผล่ ไม่กลืน |

---

## 4. PDF pipeline (paged.js)

`agent-browser pdf` ไม่มี option margin/paper → ใช้ **paged.js** ทำสารบัญ+เลขหน้าจริง.
กับดักหลักคือ **double-pagination** (หน้าว่างสลับ) — แก้ที่ `@page size` + margin เฉพาะ screen.

```mermaid
flowchart TD
    t["เลือก template<br/>guide / bug-report"] --> ed["แก้ data array<br/>(เนื้อหาจาก run จริง)"]
    ed --> sh["วาง screenshot ใน shots/"]
    sh --> op["agent-browser open &lt;html&gt;"]
    op --> wt["wait 6000<br/>(รอ paged.js จัดหน้า)"]
    wt --> ck{".pagedjs_page count<br/>= ที่คาด?"}
    ck -->|"เป็น ~2 เท่า (มีหน้าว่าง)"| fx["fix double-pagination:<br/>@page size 182×250mm (เล็กกว่าพื้นที่พิมพ์)<br/>+ .pagedjs_page margin เฉพาะ @media screen"]
    fx --> wt
    ck -->|ตรง| pd["agent-browser pdf out.pdf"]
    pd --> vf["เปิด PDF กลับมา screenshot<br/>verify: เลขหน้า · สารบัญ · ไม่มีหน้าว่าง"]
    vf --> done["✅ PDF พร้อมส่ง"]
```

รายละเอียด recipe เต็ม: [`../references/pdf-reports.md`](../references/pdf-reports.md)

---

## 5. Highlight capture sub-flow

เก็บ screenshot ที่มีกรอบไฮไลต์ชี้จุดคลิก — ฝัง **เฉพาะกรอบ** (ไม่มีข้อความไทย เพราะ headless
ไม่มีฟอนต์ไทย) แล้วขับ flow ด้วย JS click ให้ชัวร์.

```mermaid
flowchart LR
    nav["นำทางถึงสถานะที่ต้องถ่าย"] --> hl["eval: inject ring บน target<br/>scrollIntoView + outline + glow<br/>🔴 จุดคลิก · 🟢 จุดสังเกตผล"]
    hl --> shot["screenshot shots/NN.png"]
    shot --> act["eval: querySelector(sel).click()"]
    act --> asrt["assert (get url / get count)"]
    asrt --> nav
```

snippet: [`../assets/highlight.js`](../assets/highlight.js)

---

## 6. เป้าหมาย & setup

| Target | setup / auth | locator strategy | ข้อควรระวัง |
|---|---|---|---|
| **Web app ทั่วไป** | `open <url>` | `@ref` จาก `snapshot -i` หรือ `[data-test=...]` | scrollintoview ก่อน click ปุ่มใต้ fold |
| **NetSuite Suitelet** | `--profile "Work"` (reuse session, เลี่ยง 2FA) | `@ref` / css; element ใน iframe → `frame "#sel"` แล้ว `frame main` | โหลด async → `wait --fn "window.jQuery && jQuery.active===0"` |
| **Oracle APEX** | `--session porjai` (isolated) | semantic: `find label "..." fill "..."` / `find role button click --name "..."` (IG dynamic) | ทดสอบ Thai input ทุกครั้ง; `vitals --json` ถ้ามีใน version นั้น |

---

*แผนภาพทั้งหมดมาจาก workflow จริงที่ใช้ทำ QA + เอกสารด้วย agent-browser 0.27.0 บน Windows.*
