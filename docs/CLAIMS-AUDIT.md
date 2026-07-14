# Claims Audit — agent-browser-qa (+ netsuite-qa-browser cross-ref)

Audited: 2026-07-14 · by: Claude Code · env: Win11, agent-browser 0.27.0, Chrome 150

**Goal:** find claims that might be "written wrong" before they bite — especially **causal claims
with no A/B** (the class the black-window="GPU" bug belonged to).

**Scoring:**
- Type: `causal` (symptom→cause→fix) · `syntax` · `recipe` · `principle` · `efficiency`
- Provenance: does the line carry "verified/observed <date/version>"?
- Risk: **HIGH** = causal + no A/B/provenance · **MED** = inferred/intermittent or version-pinned · **LOW** = has A/B, or syntax the smoke harness checks
- Smoke: covered by `self-test/smoke-test.sh`?

---

## Executive summary

1. **The skill authors already have good provenance discipline** — most high-risk claims carry an
   inline "verified <date>" / "verified v0.27.0". **The black-window="GPU" claim was the outlier**
   (a causal claim stated as fact with no A/B). Fixed → gotchas #9 is now a 3-mechanism model.
2. **Remaining risk classes:**
   - **Intermittent-infra** (os 10060 causes) — causal but hard to reproduce → *inference*, not A/B → label "inferred".
   - **Version-pinned** (Chrome 150 / CfT / 0.27.0 / specific NetSuite accounts) — drift risk on upgrade.
   - **Syntax/recipe** — machine-checkable → let `self-test/smoke-test.sh` verify them.
3. **No remaining "GPU-2" causal claim** in the audited surface (gotchas #1–9, netsuite §0–1 tables, commands.md).

---

## Claim risk table (by risk)

| # | Claim | Location | Type | Provenance | Risk | Smoke |
|---|-------|----------|------|-----------|------|-------|
| 1 | occlusion (`CalculateNativeWinOcclusion`) = primary black-window cause | ns §0 / abq #9 | causal | launcher (primary) but **not synthetically reproduced on Chrome 150** | MED | hard |
| 2 | GPU-compositing → black, fix `--disable-gpu` | ns §1 / abq #9 | causal | no A/B; scoped as conditional | MED | hard |
| 3 | long-poll `wait` → os 10060 (Windows) | abq #3 | causal | "observed 2026-07-05", intermittent, inferred | MED | hard |
| 4 | stale session file → 10060 on every command until killed | abq #3 / ns §1 | causal | "observed 2026-07-05" | MED | partial |
| 5 | `record` needs ffmpeg + PATH not refreshed in old daemon | abq #8 | causal | detailed, verified | MED | partial |
| 6 | `get attr <sel> <name>` — selector before name | commands / #4 | syntax | confirmed | LOW | ✅ |
| 7 | `find <locator> <val> <action>` — action first, name as flag | commands / #4 | syntax | confirmed | LOW | ✅ |
| 8 | PowerShell eats `@eN` (splatting) → must quote | abq #4 | syntax | observed | LOW | (pwsh) |
| 9 | `eval` shares global scope → bare `let x` collides | abq #4 / ns §4 | syntax | "observed 2×" | LOW | ✅ |
| 10 | `batch --json` → array of `{command,result,error,success}` | commands | recipe | "verified v0.27.0" | LOW | ✅ |
| 11 | `press Alt+ArrowDown` opens native dropdown + screenshot captures it | commands | recipe | "verified headed+headless CfT150" | LOW | manual |
| 12 | element-scoped `screenshot <sel>` drops top-layer popup | commands | recipe | stated | LOW | manual |
| 13 | click does NOT auto-scroll → below-fold = silent no-op; scrollintoview fixes | abq #1 | causal | in-file minimal repro | LOW | ✅ |
| 14 | `✓ Done` ≠ success → assert state | abq #2 | principle | — | LOW | n/a |
| 15 | JS click (`eval …click()`) fires handler reliably | abq #7 | recipe | confirmed | LOW | ✅ |
| 16 | headless CfT has no Thai font → boxes | abq #5 | causal | stated | LOW | (render) |
| 17 | about:blank = black but benign; verify get url → retry open | abq #9 | causal | **A/B verified 2026-07-14** | LOW | ✅ |
| 18 | CDP screenshot immune to occlusion | abq #9 / ns §0 | causal | **verified 2026-07-14** (cover 8s) | LOW | (cover) |

**abq** = agent-browser-qa · **ns** = netsuite-qa-browser

Rows #6, #7, #9, #10, #13, #17 are exercised by `self-test/smoke-test.sh` (13 checks, all green on
2026-07-14; batch was measured ~5× fewer round-trips than sequential).

---

## Actions

**A. Complete provenance labels** — #3, #4 (10060 causes) are *inferred*; add "inferred, intermittent"
so a reader doesn't mistake them for an A/B result.

**B. Smoke harness covers the reproducible rows** — re-run `self-test/smoke-test.sh` on every
agent-browser / Chrome bump; it is the automatic drift detector.

**C. Claims the harness can't cover (#1–#5, intermittent/conditional)** — rely on the provenance date
and re-verify on a tool bump; do not promote to "fact" without an A/B.

**D. Not yet audited (honest gap):** `reliability-policy.md`, `perf-layer.md`, `a11y-layer.md`,
`visual-regression.md`, `flow-spec.md`, `pdf-reports.md`, `test-design.md` — lower causal-claim
density (procedural), but should be covered in a next pass.
