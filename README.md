# agent-browser-qa

> Claude Code / Agent **skill** for browser QA + documentation with [`agent-browser`](https://github.com/vercel-labs/agent-browser) — drive a real browser through a web flow once, get **two outputs**: a QA verdict **and** polished docs (user guide / bug report PDF).

ขับ browser อัตโนมัติด้วย `agent-browser` (Rust CLI ผ่าน CDP) เพื่อทำ QA และสร้างเอกสารจาก **การรันจริง** — *one pass, two outputs*.

## What it does

- **Browser QA** — smoke / functional / visual-regression / error-surfacing on any web app (login, checkout, wizard, form, grid), including NetSuite Suitelet & Oracle APEX.
- **Docs from the same run** — turn a tested flow into a **user-guide** or **bug-report PDF** (cover, table of contents, page numbers, annotated screenshots) using bundled templates.
- **Hard-won gotchas baked in** — the traps that make browser automation *fail silently* are documented with reproductions and fixes (see below).

## Why it exists

`agent-browser` is fast and AI-friendly, but a few behaviours waste hours and cause **false "pass" results** if you don't know them. This skill captures install → usage → the silent-failure traps → a one-pass-two-outputs workflow → ready-to-use PDF templates, so the next run starts sharp.

## Key gotchas it protects against

| Trap | Symptom | Fix |
|---|---|---|
| `click` doesn't auto-scroll | below-fold button → CLI says `✓ Done` but **nothing happens** | `scrollintoview <sel>` before `click` |
| Don't trust `✓ Done` | command "succeeds" without producing the result | assert state after every action (`wait` / `get url` / `get text`) |
| `os error 10060` | `wait --text` / `wait <selector>` flakes on Windows | use `wait --load networkidle` + short state checks |
| headless has no Thai font | injected Thai labels render as tofu | keep text in HTML, bake only the highlight ring |
| `pdf` double-pagination | paged.js PDF gets blank alternating pages | fitted `@page size` + screen-only `.pagedjs_page` margin |

Full detail with evidence: [`references/gotchas.md`](references/gotchas.md).

## Install

**Option A — one file (easiest):** download [`agent-browser-qa.skill`](agent-browser-qa.skill) and install it via your Claude Code skill installer.

**Option B — clone into your skills dir:**
```bash
git clone https://github.com/wichtking/agent-browser-qa.git ~/.claude/skills/agent-browser-qa
```

Then make sure the `agent-browser` CLI itself is installed:
```bash
npm install -g agent-browser   # or brew / cargo install agent-browser
agent-browser install          # download Chrome for Testing (first run)
```

## What's inside

```
agent-browser-qa/
├── SKILL.md                      # overview · golden rules · workflow
├── references/
│   ├── gotchas.md                # the silent-failure traps + workarounds  ← the heart
│   ├── commands.md               # command reference + token discipline
│   └── pdf-reports.md            # paged.js recipe (TOC, page numbers, fixes)
├── assets/
│   ├── guide-template.html       # user-guide PDF (edit the data array)
│   ├── bug-report-template.html  # bug-report PDF (edit the bugs array)
│   └── highlight.js              # inject a highlight ring before screenshots
└── agent-browser-qa.skill        # packaged, one-click install
```

## License

[MIT](LICENSE) © 2026 Wichit Wongta

*Templates and gotchas were derived from real runs against [saucedemo.com](https://www.saucedemo.com) and the `agent-browser` 0.27.0 CLI on Windows.*
