#!/usr/bin/env bash
# PDF-pagination self-test — verifies the pdf-reports.md causal claims mechanically.
#   bash self-test/pdf/pdf-test.sh
# Needs: agent-browser + Chrome, python with pymupdf, and network (paged.js CDN).
# Verified: agent-browser 0.27.0 / Chrome 150 (2026-07-14).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
D="$(cygpath -m "$HERE" 2>/dev/null || echo "$HERE")"
S="pdftest"
ab(){ agent-browser --session "$S" "$@" 2>&1; }

render(){ # render <name> <paged:yes|no>
  local name="$1" paged="$2"
  ab open "file:///${D}/${name}.html" >/dev/null
  if [ "$paged" = yes ]; then
    local c=0 tries=0
    while [ "$tries" -lt 40 ]; do
      c=$(ab get count ".pagedjs_page" 2>/dev/null | grep -oE '[0-9]+' | head -1)
      [ -n "${c:-}" ] && [ "$c" -gt 0 ] 2>/dev/null && break
      sleep 0.5; tries=$((tries+1))
    done
    echo "  ${name}: .pagedjs_page=${c:-0}"
  else
    ab wait --load networkidle >/dev/null 2>&1 || true
  fi
  ab pdf "${D}/out-${name}.pdf" >/dev/null
}

echo "=== render ==="
render t1-naive no
render t2-good  yes
render t2-bad   yes
ab close >/dev/null

echo "=== verdict (pymupdf) ==="
python "${HERE}/pdf_inspect.py" "${HERE}"
rc=$?
# tidy generated PDFs (keep the html + scripts under version control, drop artifacts)
rm -f "${HERE}"/out-*.pdf "${HERE}"/out-*.png
exit $rc
