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
8. `record` ต้องมี ffmpeg + PATH ไม่ refresh ใน daemon เก่า
9. headed window ดำ/about:blank ≠ GPU bug — คือหน้ายังไม่ navigate
10. หลาย terminal ชนกัน — ตั้ง session ต่อ terminal (สำคัญเมื่อรันขนาน)

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

**10060 ทุกคำสั่งแม้ kill daemon แล้ว = session file ค้าง:** `~/.agent-browser/<session>.pid/.port`
ชี้ไป daemon ที่ตายแล้ว → CLI พยายามต่อ port เก่าจน timeout ไม่ spawn ใหม่. แก้:
`Remove-Item "$env:USERPROFILE\.agent-browser\default.*"` (หรือชื่อ session ที่ใช้)
แล้วสั่งคำสั่งใดก็ได้ — CLI spawn daemon ใหม่เอง (เจอจริง 2026-07-05: kill process แล้ว
ทุกคำสั่งยัง 10060 ต่อเนื่องจนลบไฟล์).

> **Retry policy:** 10060 / daemon stall เป็น *infra error* → retry ได้ (max 2 + backoff)
> **หลัง reset สาเหตุ** เท่านั้น. assertion fail ไม่ใช่ infra → ห้าม retry. ดู
> [`reliability-policy.md`](reliability-policy.md).

---

## 4. Syntax ที่พลาดบ่อย [LOW — แต่เสียเวลา debug]

- **`get attr <selector> <name>`** — selector มาก่อน! `get attr @e2 href` ✓.
  สลับเป็น `get attr href @e2` → คืน `Element not found` (ชี้สาเหตุผิด).
- **`find <locator> <value> <action> [--flags]`** — action มาก่อน, ชื่อใส่ flag:
  `find role button click --name "Submit"` ✓. ไม่ใช่ `find role button "Submit" click`.
- **`is` ไม่ใช่ subaction ของ `find`** — เช็ค visibility ด้วยคำสั่งแยก `is visible @ref`.
- **ref จาก `snapshot -i` (เช่น `@e2`) ใช้ข้าม CLI invocation ได้** (daemon เก็บ browser ไว้);
  chain ด้วย `&&`. แต่ ref จะ stale ถ้าหน้า re-render/navigate → snapshot ใหม่.
- **PowerShell กลืน `@e18`** (`@` = splatting token) → `click @e18` กลาย `click` เปล่า
  ("Missing arguments"). ref ต้อง quote เสมอใน PowerShell: `agent-browser click '@e18'`.
- **`eval` ทุกครั้งรันใน global scope เดียวกันของหน้า** — top-level `let x` ใน eval แรกทำให้
  eval ถัดไปที่ประกาศ `let x` ซ้ำพัง `SyntaxError: Identifier 'x' has already been declared`
  (เจอจริง 2 ครั้งใน session เดียว). ครอบ IIFE เสมอ: `(function(){ ...; return JSON.stringify(out); })()`;
  ค่าที่ต้องใช้ข้าม eval เก็บใน `window.__x`.

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

---

## 8. `record` ต้องมี ffmpeg + PATH ไม่ refresh ใน daemon เก่า [MEDIUM — เสีย flow ทั้งรอบ]

**อาการ:** `record start` คืน `✓ Recording started` ปกติ → เดิน flow จนจบ → `record stop` พัง
`✗ ffmpeg not found or failed to execute`. ไฟล์วิดีโอ **ไม่ถูกสร้าง** → เสีย flow ที่อัดไปทั้งรอบ.

**เหตุ:** `record` ใช้ ffmpeg encode WebM แต่เครื่องไม่มี. และถึงติดตั้งแล้ว (เช่น
`winget install Gyan.FFmpeg`) — **PATH ที่ installer แก้ไม่ refresh ใน daemon ที่รันอยู่ก่อนติดตั้ง**
(daemon เป็น process ค้าง). `record stop` ทำ encode ที่ฝั่ง daemon → ยังหา ffmpeg ไม่เจอ.

**แก้:**
1. ติดตั้ง ffmpeg (`winget install Gyan.FFmpeg`).
2. **kill daemon เก่า**: `Stop-Process` process ชื่อ `agent-browser-win32-x64` — **อย่าแตะ `chrome`
   ของผู้ใช้** (มีหลายตัว). หรือเปิด terminal ใหม่ทั้งหมด.
3. เริ่ม `record` ในเชลล์ที่ ffmpeg อยู่บน PATH แล้ว (prepend bin ลง `$env:PATH` ถ้ายังไม่ refresh)
   → daemon ใหม่ inherit PATH → `record stop` encode ได้.

**กันพลาด:** ก่อนอัด flow ยาว ลอง `record start` + action สั้นๆ + `record stop` 1 รอบให้ได้ไฟล์ก่อน.
`stream`/`dashboard` **ไม่ต้องใช้ ffmpeg** — ถ้าแค่อยากดู live ใช้ทางนั้นเลี่ยงปัญหานี้ได้.

---

## 9. headed window จอดำ — แยก 3 กลไก อย่าเหมารวมว่า "GPU" [MEDIUM]

จอดำใน headed Chrome มี **3 สาเหตุคนละเรื่อง** วิธีแยก: ถาม 2 คำถามก่อนเสมอ —
(1) `get url` เป็น `about:blank` ไหม? (2) หน้าต่างถูก **บัง/background** อยู่ไหม (terminal ทับ,
QA window อยู่หลัง)?

**กลไก A — `about:blank` cosmetic (benign, เจอบ่อยสุด).**
`about:blank` พื้น dark theme ว่างเปล่า = ดำ เป็นเรื่องปกติ ไม่ใช่ paint พัง. ทดสอบจับภาพหน้าต่างจริง
ตรงพิกัด: ดำ ⟺ `url == about:blank` เท่านั้น; พอ navigate หน้าจริง render ปกติทันที **ทั้งมีและไม่มี
`--disable-gpu`**. แปลว่า browser **ยังไม่ได้ navigate ไปเป้าหมาย** — มักเพราะ `open` ครั้งแรก
หลัง daemon restart ล้มเหลว:
```
⚠ Daemon version mismatch detected, restarting...
✗ Could not configure browser: Failed to read... (os error 10060)
get url → about:blank        ← ค้าง = จอดำ
```
แก้: หลัง `open` เช็ก `get url` เสมอ (golden rule #4); ถ้าค้าง about:blank → `open` ซ้ำ 1 ครั้ง;
จะ present/screenshot ให้ทำหลังหน้าจริงโหลด.

**กลไก B — GPU-compositing black rectangle.** automation Chrome บน Windows headed บาง
เงื่อนไข paint content เป็นสี่เหลี่ยมดำทั้งที่ url เป็นหน้าจริง. แก้: `--disable-gpu`
`--disable-software-rasterizer`.

**กลไก C — occluded/background window หยุด paint ("the real repeat offender").** Chrome บน
Windows มี feature `CalculateNativeWinOcclusion`: หน้าต่างที่ถูกบัง/background จะถูกมองว่า hidden แล้ว
**หยุด render** → จอดำ. QA window ถูก background ตลอดเวลาที่ agent ขับ → โดนเต็ม ๆ. แก้:
`--disable-features=CalculateNativeWinOcclusion --disable-backgrounding-occluded-windows
--disable-renderer-backgrounding`.

**Source of truth = launcher `qa-browser.ps1`** (repo PWOC/WCS/DA-Light-Mfg, ดู `netsuite-qa-browser`).
มันรวม flag set ครบทั้ง B+C ไว้ที่ launch แล้ว (comment ในไฟล์ชี้ว่า **C คือตัวการหลัก ไม่ใช่ B**).
flag ใช้ตอน launch เท่านั้น → session ที่รันอยู่ต้อง `close` + relaunch.

**สิ่งที่วัดได้เอง (bound):** ทดสอบ A/B บนเครื่องนี้ (Chrome 150, จับภาพหน้าต่างจริง + cover window 9s):
บน example.com **และหน้า NetSuite Login จริง**, มี/ไม่มี flag → **reproduce B และ C ไม่ได้เลย**
(หน้า render ปกติทุกครั้ง); reproduce ได้แค่ A (about:blank). สรุป: B/C เป็น **conditional จริง**
(background นานเป็นนาที / GPU driver เฉพาะ / Chrome รุ่นเก่า) ที่ cover สังเคราะห์สั้น ๆ trigger ไม่ติด —
launcher เจอจาก session จริงยาว ๆ จึงยังเชื่อถือได้, แค่ trigger ไม่ง่ายบน Chrome 150.
ที่ยืนยันแน่: **CDP `screenshot` ภูมิคุ้มกัน occlusion** (capture จาก renderer compositor ไม่ใช่ native
window) → ถูกบังอยู่ก็ยังได้ภาพหน้าจริง → **artifact ของ guide/report ไม่พังแม้ on-screen จะดำ** (กลไก C
กระทบแค่คนดู live/dashboard, ไม่กระทบไฟล์ screenshot).

**Decision rule เวลาเจอจอดำ:** เช็ก `get url` ก่อน → `about:blank` = กลไก A (retry open, benign);
url เป็นหน้าจริง + หน้าต่างถูกบัง/background = กลไก B/C → relaunch ด้วย flag set ของ launcher.
CDP screenshot ใช้ได้เสมอไม่ว่ากรณีไหน.

**ยังไม่ฟันธง:** `%TEMP%\agent-browser-chrome-*` สะสมเป็นสิบชุด (orphan temp profile) — เห็นจริงแต่ยัง
ไม่พิสูจน์ว่า leak ต่อ `open` หรือเป็นซากจาก crash/kill สะสม. กินดิสก์ ลบทิ้งเป็นครั้งคราวได้เมื่อไม่มี session รันอยู่.

---

## 10. หลาย terminal ขับ agent-browser พร้อมกัน → ชน daemon/browser ตัวเดียวกัน [HIGH — เมื่อรันขนาน]

**อาการ (เจอจริง 2026-07-17):** เปิด Claude หลาย terminal ทำ QA พร้อมกัน ทุกตัว default session ชื่อ
`default` เหมือนกัน → 1 daemon + 1 browser ตัวเดียวกัน สอง terminal คลิกทับกัน/แย่งแท็บ, หน้าเปิดทับกัน,
หลุดกลางคัน. ซ้ำร้าย session ที่ crash ทิ้ง daemon (`agent-browser-win32-x64`) + Chrome-for-Testing ค้าง
สะสมข้ามคืน (เจอ 11 daemon + 39 orphan chrome ค้าง ~20 ชม. จนเครื่องแน่น). **พอร์ต 4848 = dashboard
server ไม่ใช่ต้นเหตุ**; TIME_WAIT storm บน 4848 เป็น connection churn ปกติ ปล่อยได้.

**กลไก:** agent-browser = 1 daemon ต่อ 1 **session name**; แต่ละ session แยก browser context.
ไม่ตั้งชื่อ = ทุก terminal ใช้ `default` = แชร์ browser เดียวกัน. บน Windows ยังมีชั้น **profile lock**:
1 `--profile` dir = Chrome ได้แค่ 1 process → หลาย terminal ใช้ profile login เดียวกันชนที่ lock แม้ตั้ง
session ต่างกันแล้ว.

**แก้ (ทำก่อนขับ browser ทุกครั้ง — โดยเฉพาะเมื่อจะรันขนาน):**
- **ตั้ง session ต่อ terminal** จาก `CLAUDE_CODE_SESSION_ID` (Claude Code ฉีดเข้า env ทุก child process,
  นิ่งต่อ terminal, ต่างข้าม terminal):
  - bash (ต้นสาย `&&` chain): `export AGENT_BROWSER_SESSION="cc-${CLAUDE_CODE_SESSION_ID:0:8}"`
  - pwsh: `$env:AGENT_BROWSER_SESSION = "cc-$($env:CLAUDE_CODE_SESSION_ID.Substring(0,8))"`
  - fallback ราย command: ใส่ `--session "cc-<sid8>"` ทุกคำสั่ง
  - ⚠ env ไม่ persist ข้าม tool call (harness shell = -NoProfile/non-interactive, `~/.bashrc`/profile.ps1
    ไม่ถูกโหลด) → ต้อง `export`/`$env:` **inline ในทุก bash chain / pwsh call** หรือใช้ `--session`.
- **รันขนานที่ต้องใช้ login เดิม (NetSuite):** ต้องแยก **profile dir ต่อ terminal** ด้วย ไม่งั้นชน profile
  lock — seed สำเนา profile ที่ login แล้วเป็น `...\profiles\cc-<sid8>` ต่อ terminal
  (ดู `netsuite-qa-browser` persistent-profile). generic web QA (ephemeral profile) ตั้งแค่ session ก็พอ.

**Idle-timeout กันซากพอกซ้ำ:** ตั้ง env `AGENT_BROWSER_IDLE_TIMEOUT_MS` (ms) → daemon ปิด browser +
exit เองเมื่อไม่มีคำสั่งตามเวลาที่ตั้ง. บนเครื่องนี้ตั้งถาวรที่ User scope = `1800000` (30 นาที).

**Recipe ล้างซากแบบปลอดภัย (ห้าม `taskkill chrome` มั่ว — Chrome ส่วนตัว user ปนกับ QA):**
1. `agent-browser close --all` → `agent-browser doctor` (เก็บ stale daemon/session files)
2. kill เฉพาะ Chrome-for-Testing (path `*\.agent-browser\browsers\*`); **เว้น**
   `C:\Program Files\Google\Chrome` (ส่วนตัว) + msedge/webview2. คลัสเตอร์ chrome ที่ไม่มี daemon เวลา
   start คู่กัน = เบราว์เซอร์ส่วนตัว.
3. kill daemon ค้างที่เหลือ: process ชื่อ `agent-browser-win32-x64`.
```powershell
agent-browser close --all; agent-browser doctor
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  ? { $_.ExecutablePath -like '*\.agent-browser\browsers\*' } |
  % { Stop-Process -Id $_.ProcessId -Force }
Get-Process 'agent-browser-win32-x64' -ErrorAction SilentlyContinue | Stop-Process -Force
```
