# agent-browser — Command Reference (v0.27.0)

คู่มือในตัวที่ version-matched: `agent-browser skills get core --full`. ด้านล่างคือคำสั่งที่ใช้บ่อย
สำหรับ QA + docs. global flags: `--json` (machine output), `--session <name>` (isolated),
`--profile <name|path>` (reuse Chrome login), `--headed`, `--cdp <port>`, `--max-output <n>`.

## Navigate / Interact
| คำสั่ง | ใช้ทำ |
|---|---|
| `open <url>` | เปิดหน้า (เริ่ม daemon ถ้ายังไม่มี) |
| `click <sel>` | คลิก (CSS / XPath / `@eN`). **scrollintoview ก่อนถ้าใต้ fold** |
| `fill <sel> <text>` | clear + กรอก |
| `type <sel> <text>` | พิมพ์ต่อท้าย · `press <key>` กดปุ่ม (Enter, Tab, Control+a) |
| `scrollintoview <sel>` | เลื่อน element เข้า viewport (ใช้ก่อน click ปุ่มใต้ fold) |
| `scroll <dir> [px]` · `hover` · `select <sel> <val>` · `check/uncheck` · `upload` | อื่นๆ |
| `back` · `forward` · `reload` · `close [--all]` | นำทาง/ปิด |

## อ่านข้อมูล (ผลลัพธ์สั้น — ปลอดภัยต่อ token)
| คำสั่ง | หมายเหตุ |
|---|---|
| `snapshot -i` | accessibility tree เฉพาะ interactive (มี ref `@eN`). scope: `-s "#sel"` |
| `get text <sel>` · `get value <sel>` | ดึงค่า |
| `get attr <sel> <name>` | **selector ก่อน name** เช่น `get attr @e2 href` |
| `get url` · `get title` · `get count <sel>` · `get box <sel>` | สั้น ปลอดภัย |
| `is visible/enabled/checked <sel>` | เช็ค state (คนละคำสั่งกับ `find`) |
| `errors --json` · `console --json` | error surfacing — หลังทุก step สำคัญ |
| `eval <js>` | รัน JS — ใช้ assert ลึก หรือ JS click (ดู gotchas) |

## หา element แบบ semantic (ทน dynamic UI)
`find <locator> <value> <action> [--flags]` — **action มาก่อน, ชื่อใส่ flag**:
```
find role button click --name "Submit"
find label "ชื่อลูกค้า" fill "บริษัท ก"
find text "Checkout" click
```
locator: `role | text | label | placeholder | alt | title | testid | first | last | nth`

## จับภาพ native `<select>` dropdown (ที่เปิดเห็นตัวเลือก) — สำหรับ user guide
native dropdown ของ `<select>` ถูกเปิดด้วย **input synthesis** เท่านั้น (`showPicker()`/`.click()`
จาก `eval` จะ fail `requires a user gesture`). **ยืนยันแล้วว่า `press` เปิดได้และ screenshot จับติด
ทั้ง headed + headless** (Chrome for Testing 150):
```
eval "document.querySelector('SEL').focus()"
press "Alt+ArrowDown"          # เปิด dropdown (เห็นตัวเลือกลอยทับ content)
press "ArrowDown"              # ทำซ้ำ N ครั้งเลื่อนไฮไลต์ไปตัวเลือกที่ต้องการ
screenshot guide/step.png      # จับ dropdown ที่เปิดอยู่ + ไฮไลต์ตัวที่เลือก
press "Enter"                  # commit (หรือ Escape ปิด — ค่าจะตามตัวที่ไฮไลต์อยู่แล้ว)
```
- **ArrowDown commit ค่าทันที** (selection ตามไฮไลต์) — เหมาะกับ guide ที่ต้องเลือกตัวนั้นพอดี.
- รุ่น Chrome เก่ากว่านี้อาจจับ native popup ไม่ติด → fallback: ตั้ง `select.size=N` ชั่วคราว
  (กางเป็น list inline) หรือ inject DOM overlay เลียนแบบ dropdown (ทั้งคู่อยู่ใน DOM = จับติดเสมอ).
- ป๊อปอัป native อื่นที่ **อยู่นอก DOM** (`alert`/`confirm`, file dialog) ยัง screenshot ไม่ติด.
- **crop เฉพาะส่วนสำคัญ:** `screenshot "<selector>" <path>` clip เฉพาะกล่อง element (เช่น `.card`) ตัดขอบว่างทิ้ง.
  **แต่ element-scoped screenshot จะ "ตก" native dropdown/top-layer popup** (เป็น layer แยก) → ถ้าภาพมี popup
  ให้ถ่าย **full viewport** แล้ว crop ด้วย image tool ตาม `getBoundingClientRect` (PowerShell `System.Drawing`
  ถ้าไม่มี PIL: `$g.DrawImage($src,destRect,srcRect,Pixel)`). ภาพ card แนวตั้ง/จัตุรัส ใน guide ควรคุม
  `.shot{max-width:340px;margin:auto}` กันรูปบานเต็มหน้า (กิน page เกินจำเป็น).

## หลักฐาน / เอกสาร
| คำสั่ง | หมายเหตุ |
|---|---|
| `screenshot <path>` | เซฟไฟล์. `--json` คืน path. `--full` ทั้งหน้า |
| `screenshot --annotate <path>` | ติดเลข+กล่อง element (คืน box+ref ใน --json) |
| `diff screenshot --baseline <a> -o <b>` | visual regression |
| `pdf <path>` | เซฟ PDF (Chrome printToPDF — ไม่มี option margin/paper ดู pdf-reports.md) |

## รอแบบฉลาด (อย่ารอ fixed ms กับหน้า async)
```
wait --load networkidle        # ← ชอบใช้สุด (เสถียร, เลี่ยง os 10060)
wait --fn "window.jQuery && jQuery.active === 0"   # NetSuite async
wait "<selector>"  / wait --text "<text>"          # long-poll — เจอ os 10060 เป็นระยะ บน Windows
wait <ms>                       # เฉพาะ clientside toggle สั้นๆ + verify
```

## Session / Auth / Tabs
`state save|load|clear` · `auth save|login` · `--profile` (เลี่ยง 2FA) · `--session <name>` ·
`tab new|close|<id>` · `frame "#sel"` / `frame main` (เข้า/ออก iframe) · `mcp` (เป็น MCP server)
