# agent-browser — Command Reference (v0.32.1)

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
wait --load networkidle        # ← ชอบใช้สุด (เสถียร, เลี่ยง os 10060) — ห้ามบน NetSuite: โพลไม่จบ
wait --fn "window.jQuery && jQuery.active === 0"   # NetSuite async (ใช้ตัวนี้แทน networkidle เสมอ — ดู skill netsuite-qa-browser)
wait "<selector>"  / wait --text "<text>"          # long-poll — เจอ os 10060 เป็นระยะ บน Windows
wait <ms>                       # เฉพาะ clientside toggle สั้นๆ + verify
```

## Batch — ลด round-trip / daemon stall (efficiency)
ยิงหลายคำสั่งใน invocation เดียวแทนที่จะเรียก CLI ทีละครั้ง → ลด process spawn + โอกาส daemon สะดุด
ระหว่าง flow ยาว (เจอ os 10060 น้อยลง) + log เป็นก้อนเดียว. `batch [--bail] "<cmd>" ...`
รับคำสั่งเป็น **quoted args** หรือ **JSON ผ่าน stdin** (ไม่ใช่ path ไฟล์):
```
# quoted args (default = รันต่อแม้ error; --bail = หยุดที่ error แรก):
agent-browser batch "open <url>" "wait --load networkidle" "get url" "errors" --json
# หรือ pipe JSON: echo '["get url","get title"]' | agent-browser batch --json
```
- **`--json` ของ batch คืน array** `[{command, result, error, success}, ...]`. **shape เปลี่ยนจาก
  v0.27 → v0.32.1** (verify 2026-07-17): `command` เป็น **array** (`["get","url"]` ไม่ใช่ string `"get url"`)
  และ `result` เป็น **object ห่อ** `{lifecycle, <ค่าที่ชื่อตาม command เช่น url>}` (v0.27 คืนค่าตรง ๆ).
  key ยังครบ 4 (command/result/error/success). ดึงค่าจริงที่ `result.<field>` (เช่น `.result.url`). ใช้เป็น `run-log.json` ได้เลย.
- ref `@eN` persist ข้ามคำสั่งใน batch (daemon เก็บ browser). ถ้าไม่ batch: chain ด้วย `&&` ในเชลล์ก็ได้.
- **อย่าใส่ assertion ที่ output ยาว** (snapshot เต็ม/get html) ลง batch — ผลรวมกลับ context ทั้งก้อน.
  batch เก็บเฉพาะคำสั่งสั้น (navigate/fill/click/get/errors) ตาม token discipline.

## Pre-flight health-check — กัน cold-start 10060 loop (efficiency)
ก่อนเริ่ม flow ยาว เช็ค daemon+session ให้ warm ก่อน เลี่ยงลูป cold-start ที่ช้าเป็นนาที (ดู gotchas):
```
agent-browser get url --session <name> || {           # ถ้า block/10060 = session ค้าง
  # ลบ session file ที่ชี้ daemon ตาย แล้วให้ CLI spawn ใหม่:
  # PowerShell: Remove-Item "$env:USERPROFILE\.agent-browser\<name>.*"
  agent-browser open about:blank --session <name>      # pre-warm (poll จน get url คืน URL)
}
```
- ใช้ **fixed session** ตลอด flow (`--session uiqarun`) + **อย่า `close --all`** ระหว่างทาง (ใช้ `reload`
  รีเซ็ต state แทน) — เลี่ยง cold relaunch ที่ค้าง CLI >2 นาที.
- ถ้าจะ `record`/`ffmpeg`: warm-up `record start`+action สั้น+`record stop` 1 รอบให้ได้ไฟล์ก่อนอัด flow จริง.

## Session / Auth / Tabs
`state save|load|clear` · `auth save|login` · `--profile` (เลี่ยง 2FA) · `--session <name>` ·
`tab new|close|<id>` · `frame "#sel"` / `frame main` (เข้า/ออก iframe) · `mcp` (เป็น MCP server)

## Record วิดีโอ / Live (demo / ส่งมอบ)
| คำสั่ง | หมายเหตุ |
|---|---|
| `record start <out.webm> [url]` … `record stop` | อัด flow เป็นวิดีโอ WebM/VP8. **ต้องมี `ffmpeg`** (ดู gotchas — ติดตั้งแล้วต้อง restart daemon) |
| `stream enable [--port <n>]` · `stream status` · `stream disable` | live WebSocket streaming (ไม่ต้อง ffmpeg) |
| `dashboard start [--port <n>]` (default 4848) · `dashboard stop` | หน้า observability ดู browser + console/network สด (ไม่ต้อง ffmpeg) → เปิด `http://localhost:4848` |

**pointer ชี้จุด focus/คลิกในวิดีโอ** (CDP screencast ไม่จับ OS cursor → inject DOM overlay แทน):
ใช้ `assets/pointer.js` — เรียก `eval point(sel)` ก่อนทุก action → `wait ~600ms` → fill/click. ตัวอย่าง:
```
PT="(function(s){var p=document.getElementById('__ptr');if(!p){p=document.createElement('div');p.id='__ptr';p.style.cssText='position:fixed;z-index:2147483647;width:26px;height:26px;margin:-13px 0 0 -13px;border:3px solid #ff2d55;border-radius:50%;background:rgba(255,45,85,.2);box-shadow:0 0 0 5px rgba(255,45,85,.22),0 0 16px #ff2d55;pointer-events:none;transition:left .45s ease,top .45s ease;left:50%;top:50%';document.body.appendChild(p);}var e=document.querySelector(s);if(!e)return 'noel:'+s;e.scrollIntoView({block:'center'});var r=e.getBoundingClientRect();p.style.left=(r.left+r.width/2)+'px';p.style.top=(r.top+r.height/2)+'px';p.animate([{transform:'scale(1.8)'},{transform:'scale(1)'}],{duration:450});return 'ok';})"
agent-browser record start flow.webm <url>
agent-browser eval "$PT('#user-name')" && agent-browser wait 650 && agent-browser fill '#user-name' 'x'
# ... point ก่อนทุก action ...
agent-browser record stop
```
- ใส่ paced `wait 500-900` ระหว่าง action ให้วิดีโอเห็นการเคลื่อนไหว (ไม่งั้น action กระโดดเร็วเกินดูไม่ทัน).
- verify ด้วย `ffprobe` (duration/ขนาด) + ดึงเฟรม `ffmpeg -ss <t> -i flow.webm -vframes 1 frame.png` มาเช็ค pointer.
