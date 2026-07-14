# self-test — regression harness for agent-browser-qa

Machine-checks the skill's **syntax / recipe / reproducible-causal** claims against a real
agent-browser so a wrong or drifted claim is caught mechanically, not by accident.

## Run

```bash
bash self-test/smoke-test.sh
```

Needs `agent-browser` on PATH (v0.27.0+) and Chrome for Testing installed. Uses an isolated
`--session smoketest` and a local `file://` page (`smoke-page.html`), so it never touches your
other sessions. Exit code is non-zero if any check fails.

## What it verifies (each = one documented claim)

| Claim | Source |
|---|---|
| `get attr <sel> <name>` — selector before name (reversed → "not found") | gotchas #4 |
| `find <locator> <val> <action> --name` — action before name | commands.md |
| `eval` shares page global scope — bare `let x` collides; IIFE avoids it | gotchas #4 |
| `batch --json` → array of `{command, result, error, success}` | commands.md |
| `click` does NOT auto-scroll — below-fold click returns `✓ Done` but is a no-op; `scrollintoview` fixes it | gotchas #1 |
| `open about:blank` → `get url` reflects it (black window ≠ bug) | gotchas #9 |

Plus efficiency measurements: **batch vs sequential** round-trips/time, and **`snapshot -i` vs full**
output size (token-discipline proxy).

## When to run

- After any **agent-browser or Chrome version bump** — this is the drift detector. A claim that
  silently changed behavior (e.g. the `batch` JSON shape, a flag rename) fails here first.
- Before shipping edits to `references/commands.md` or `references/gotchas.md`.

## Discipline this encodes

A causal/behavioral claim ships with a **reproducible check**, not an anecdote. See
[`docs/CLAIMS-AUDIT.md`](../docs/CLAIMS-AUDIT.md) for the full claim ledger (which claims are
verified vs inferred vs version-pinned). The one class this harness can't cover — intermittent /
long-background conditions (os 10060, GPU/occlusion black) — must rely on dated provenance instead.
