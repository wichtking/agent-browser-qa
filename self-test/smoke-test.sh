#!/usr/bin/env bash
# Smoke self-test for agent-browser-qa documented claims.
# Verifies syntax/recipe/reproducible-causal claims mechanically + measures efficiency.
# Re-run after any agent-browser / Chrome version bump = automatic drift detector.
#
#   bash self-test/smoke-test.sh
#
# Verified: agent-browser 0.27.0 / Chrome for Testing 150 / Windows 11 (2026-07-14).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERE_WIN="$(cygpath -m "$HERE" 2>/dev/null || pwd -W 2>/dev/null || echo "$HERE")"
PAGE="file:///${HERE_WIN}/smoke-page.html"
S="smoketest"
ab(){ agent-browser --session "$S" "$@" 2>&1; }
shopt -s nocasematch
pass=0; fail=0
chk(){ # chk "name" "expected-substr" "actual"  — pure bash match (grep -F SIGABRTs on UTF-8 checkmarks in Git Bash)
  if [[ "$3" == *"$2"* ]]; then echo "  PASS  $1"; pass=$((pass+1));
  else echo "  FAIL  $1 | want '$2' | got: ${3//$'\n'/ }" | head -c 200; echo; fail=$((fail+1)); fi; }

echo "=== setup ==="
ab open "$PAGE" >/dev/null; echo "url: $(ab get url)"

echo "=== #6 get attr: selector BEFORE name ==="
chk     "get attr @sel href (correct order)" "example.org/target" "$(ab get attr '#lnk' href)"
chk     "get attr reversed order -> not found" "not found"        "$(ab get attr href '#lnk')"

echo "=== #7 find: action before, name as flag ==="
ab open "$PAGE" >/dev/null
chk     "find role button click --name Act -> handler fired" "act-clicked" "$(ab find role button click --name 'Act' >/dev/null; ab get text '#out')"

echo "=== #9 eval shares global scope (bare let x collides) ==="
ab eval "let smk=1; smk" >/dev/null
chk     "2nd bare 'let smk' -> SyntaxError" "already been declared" "$(ab eval 'let smk=2; smk')"
chk     "IIFE form avoids collision"        "ok3"                   "$(ab eval "(function(){var smk=3; return 'ok'+smk;})()")"

echo "=== #10 batch --json shape ==="
BJ="$(ab batch 'get url' 'get title' --json)"
chk     "batch starts as array"       '[{'        "$(tr -d ' \n' <<<"$BJ" | head -c 3)"
chk     "batch item has command key"  '"command"' "$BJ"
chk     "batch item has result key"   '"result"'  "$BJ"
chk     "batch item has error key"    '"error"'   "$BJ"
chk     "batch item has success key"  '"success"' "$BJ"

echo "=== #13 click does NOT auto-scroll (below-fold = silent no-op) then scrollintoview fixes ==="
ab open "$PAGE" >/dev/null
raw_click="$(ab click '#btm')"; after_noscroll="$(ab get text '#bout')"
echo "  (raw below-fold click returned: $(head -c 40 <<<"$raw_click"))"
chk     "below-fold click left state unchanged" "bidle" "$after_noscroll"
ab scrollintoview '#btm' >/dev/null; ab click '#btm' >/dev/null
chk     "scrollintoview + click fired handler"  "btm-clicked" "$(ab get text '#bout')"

echo "=== #17 about:blank benign + get url reflects it ==="
chk     "open about:blank -> get url == about:blank" "about:blank" "$(ab open about:blank >/dev/null; ab get url)"

echo "=== EFFICIENCY: batch vs sequential (5 short reads) ==="
ab open "$PAGE" >/dev/null
t0=$(date +%s.%N); for c in "get url" "get title" "get count body" "is visible #act" "errors"; do ab $c >/dev/null; done; t1=$(date +%s.%N)
t2=$(date +%s.%N); ab batch "get url" "get title" "get count body" "is visible #act" "errors" --json >/dev/null; t3=$(date +%s.%N)
echo "  sequential: 5 CLI calls, $(awk "BEGIN{printf \"%.2f\", $t1-$t0}")s | batch: 1 CLI call, $(awk "BEGIN{printf \"%.2f\", $t3-$t2}")s"

echo "=== EFFICIENCY: output size snapshot(full) vs snapshot -i (token proxy) ==="
echo "  snapshot full: $(ab snapshot | wc -c) bytes | snapshot -i: $(ab snapshot -i | wc -c) bytes"

echo "=== cleanup ==="
ab close >/dev/null
echo ""
echo "======== RESULT: $pass passed, $fail failed ========"
[ "$fail" -eq 0 ]
