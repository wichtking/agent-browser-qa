#!/usr/bin/env python3
"""release-summary.py — roll every qa/<feature>/coverage.yaml into one sign-off page.

@author Wichit Wongta

Aggregates each feature's coverage manifest (reusing the exact gate logic from
coverage-check.py) plus a note on whether its qa-report.md exists, and prints a
single table for a QA Lead to sign off a release.

    usage: python scripts/release-summary.py [qa_dir]      # default: qa

Exit codes:
    0  every feature's gate is PASS      -> RELEASE: READY
    1  at least one feature gate is FAIL -> RELEASE: BLOCKED
    2  a manifest is malformed, or qa_dir has no coverage.yaml (surfaced,
       never a silent empty pass)

No silent fallback: a malformed manifest is reported with its feature and
reason, and forces exit 2.
"""
import glob
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_checker():
    """Import coverage-check.py (hyphenated filename) to reuse its gate logic."""
    path = os.path.join(HERE, "coverage-check.py")
    spec = importlib.util.spec_from_file_location("coverage_check", path)
    if spec is None or spec.loader is None:
        print(f"ERROR: cannot load {path}", file=sys.stderr)
        sys.exit(2)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def feature_name(manifest_path, data):
    return data.get("feature") or os.path.basename(os.path.dirname(manifest_path))


def main(argv):
    qa_dir = argv[1] if len(argv) > 1 else "qa"
    if not os.path.isdir(qa_dir):
        print(f"ERROR: qa dir not found: {qa_dir}", file=sys.stderr)
        sys.exit(2)

    manifests = sorted(
        p for p in glob.glob(os.path.join(qa_dir, "*", "coverage.yaml"))
        if os.path.basename(os.path.dirname(p)) != "_template"
    )
    if not manifests:
        print(f"ERROR: no qa/*/coverage.yaml under {qa_dir}", file=sys.stderr)
        sys.exit(2)

    cc = load_checker()
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is not installed. Run: pip install -r requirements.txt",
              file=sys.stderr)
        sys.exit(2)

    rows = []
    errors = []
    any_fail = False
    for path in manifests:
        feat = os.path.basename(os.path.dirname(path))
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if not isinstance(data, dict):
                raise cc.ManifestError("top level must be a mapping")
            acs = cc.validate(data)
        except (yaml.YAMLError, OSError, cc.ManifestError) as exc:
            errors.append(f"{feat}: {exc}")
            rows.append([feat, "-", "-", "-", "-", "MALFORMED", "-"])
            continue

        feat = feature_name(path, data)
        blocking = warn = passed = 0
        for ac in acs:
            status, is_blocking = cc.classify(ac)
            if is_blocking:
                blocking += 1
            elif status.startswith("FAIL"):
                warn += 1
            elif status == "PASS":
                passed += 1
        gate = "PASS" if blocking == 0 else "FAIL"
        if gate == "FAIL":
            any_fail = True
        report = "yes" if os.path.exists(
            os.path.join(os.path.dirname(path), "qa-report.md")) else "MISSING"
        rows.append([feat, str(len(acs)), str(passed), str(blocking), str(warn), gate, report])

    headers = ["Feature", "ACs", "Pass", "Block", "Warn", "GATE", "Report"]
    widths = [len(h) for h in headers]
    for r in rows:
        for j, cell in enumerate(r):
            widths[j] = max(widths[j], len(cell))
    print("Release summary - " + qa_dir)
    print("  ".join(h.ljust(widths[j]) for j, h in enumerate(headers)))
    print("  ".join("-" * widths[j] for j in range(len(headers))))
    for r in rows:
        print("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(r)))
    print()

    if errors:
        print("Malformed manifests (fix before sign-off):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print("RELEASE: BLOCKED (malformed manifest)")
        return 2
    if any_fail:
        print("RELEASE: BLOCKED")
        return 1
    print("RELEASE: READY")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
