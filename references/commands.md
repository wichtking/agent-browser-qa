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
