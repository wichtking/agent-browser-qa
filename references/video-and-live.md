# Record video / watch live + pointer marking the active spot

Record a flow as video or watch the browser live (good for demo/handover). Commands also in
`commands.md`.

- **Video file:** `record start <out.webm> [url]` → walk the flow → `record stop`. **Requires
  `ffmpeg`**, otherwise `record stop` fails at the end (`ffmpeg not found`) — losing the whole flow.
  After installing, **restart the daemon** so it picks up the new PATH (see `gotchas.md` §8).
- **Watch live (no ffmpeg):** `dashboard start` → open `http://localhost:4848` · or `stream enable`
  (WebSocket).

## Pointer marking the focus/click spot (important for video)

agent-browser drives via CDP/JS — **there is no real cursor for the screencast to capture**, so the
video doesn't show where the action happens. Fix by injecting a DOM overlay (a glowing ring) that,
being **rendered, gets recorded**.

Use `assets/pointer.js` (`point(sel)`): call `eval point(sel)` **before every action** with the same
selector you'll act on → `wait ~600ms` (let the ring move + pulse) → then fill/click. It's idempotent
(recreates the ring if lost on navigate) and positions via `getBoundingClientRect`. **Verify one
frame before the real recording** (`eval point` → `screenshot`) to guard against quoting bugs.

## Guard against a lost flow

Before recording a long flow, do one throwaway `record start` + a short action + `record stop` and
confirm the file exists. `stream`/`dashboard` need no ffmpeg — if you only want to watch live, use
those and avoid the ffmpeg trap entirely.
