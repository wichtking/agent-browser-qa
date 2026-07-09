#!/usr/bin/env python3
"""coverage-check.py — turn the release gate from prose into an exit code.

@author Wichit Wongta

Reads a coverage manifest (qa/<feature>/coverage.yaml) that maps every
Acceptance Criterion (AC) to the flow scenario that proves it, and computes
whether the release gate is open.

    usage: python scripts/coverage-check.py <path/to/coverage.yaml>

Exit codes (contract):
    0  every AC has a flow_scenario + result=pass, no critical/high open,
       nothing quarantined  -> GATE: PASS
    1  at least one AC is not_tested / blocked / fail(critical|high) /
       quarantined           -> GATE: FAIL
    2  coverage.yaml is missing, unparseable, or structurally invalid
       (error surfaced, never a silent default)

No silent fallback: a malformed manifest or a missing dependency exits 2 with a
clear message instead of degrading quietly. medium/low fails do NOT block the
gate (ship with a tracked ticket, per docs/TEAM-PROCESS.md) but are flagged WARN.
"""
import sys

RESULT_VALUES = {"pass", "fail", "not_tested", "blocked"}
SEVERITY_VALUES = {"critical", "high", "medium", "low"}
VERIFIABLE_VALUES = {"browser", "code-only"}
BLOCKING_SEVERITY = {"critical", "high"}


class ManifestError(Exception):
    """Raised for anything that should surface as exit 2."""


def die_config(msg):
    """Surface a structural / dependency error and exit 2 (no silent fallback)."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)


def load_manifest(path):
    try:
        import yaml
    except ImportError:
        die_config(
            "PyYAML is not installed. Run: pip install -r requirements.txt "
            "(or: pip install pyyaml)"
        )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        die_config(f"coverage file not found: {path}")
    except yaml.YAMLError as exc:
        die_config(f"cannot parse YAML: {exc}")
    except OSError as exc:
        die_config(f"cannot read {path}: {exc}")
    if not isinstance(data, dict):
        die_config("top level of coverage.yaml must be a mapping")
    return data


def validate(data):
    """Return the list of AC dicts, or raise ManifestError (-> exit 2)."""
    acs = data.get("acceptance_criteria")
    if acs is None:
        raise ManifestError("missing required key: acceptance_criteria")
    if not isinstance(acs, list):
        raise ManifestError("acceptance_criteria must be a list")
    for i, ac in enumerate(acs):
        where = f"acceptance_criteria[{i}]"
        if not isinstance(ac, dict):
            raise ManifestError(f"{where} must be a mapping")
        if not ac.get("id"):
            raise ManifestError(f"{where} missing required key: id")
        acid = ac["id"]
        result = ac.get("result")
        if result not in RESULT_VALUES:
            raise ManifestError(
                f"{acid}: result must be one of {sorted(RESULT_VALUES)}, got {result!r}"
            )
        sev = ac.get("severity")
        if result == "fail" and sev not in SEVERITY_VALUES:
            raise ManifestError(
                f"{acid}: result=fail requires severity in {sorted(SEVERITY_VALUES)}, got {sev!r}"
            )
        if sev is not None and sev not in SEVERITY_VALUES:
            raise ManifestError(
                f"{acid}: severity must be null or one of {sorted(SEVERITY_VALUES)}, got {sev!r}"
            )
        verifiable = ac.get("verifiable")
        if verifiable is not None and verifiable not in VERIFIABLE_VALUES:
            raise ManifestError(
                f"{acid}: verifiable must be one of {sorted(VERIFIABLE_VALUES)}, got {verifiable!r}"
            )
        quarantine = ac.get("quarantine", False)
        if not isinstance(quarantine, bool):
            raise ManifestError(f"{acid}: quarantine must be true/false, got {quarantine!r}")
    return acs


def classify(ac):
    """Return (status, blocking: bool) for one AC.

    A missing flow_scenario downgrades to not_tested regardless of result, so an
    AC can never claim pass without a scenario that ran.
    """
    scenario = ac.get("flow_scenario")
    result = ac["result"]
    sev = ac.get("severity")
    if ac.get("quarantine", False):
        return "QUARANTINE", True
    if not scenario:
        return "NOT_TESTED", True          # no scenario -> not proven
    if result in ("not_tested", "blocked"):
        return result.upper(), True
    if result == "fail":
        if sev in BLOCKING_SEVERITY:
            return f"FAIL({sev})", True
        return f"FAIL({sev})", False       # medium/low -> WARN, ship with ticket
    return "PASS", False


def print_table(rows):
    headers = ["AC", "Scenario", "Verifiable", "Result", "Severity", "Status"]
    widths = [len(h) for h in headers]
    for r in rows:
        for j, cell in enumerate(r):
            widths[j] = max(widths[j], len(cell))
    line = "  ".join(h.ljust(widths[j]) for j, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[j] for j in range(len(headers))))
    for r in rows:
        print("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(r)))


def main(argv):
    if len(argv) != 2:
        die_config("usage: python scripts/coverage-check.py <path/to/coverage.yaml>")
    path = argv[1]
    data = load_manifest(path)
    try:
        acs = validate(data)
    except ManifestError as exc:
        die_config(str(exc))

    feature = data.get("feature", "(unnamed)")
    print(f"Feature: {feature}   Manifest: {path}")
    if not acs:
        print("GATE: FAIL  (no acceptance criteria defined)")
        return 1

    rows = []
    blocking = 0
    warn = 0
    for ac in acs:
        status, is_blocking = classify(ac)
        if is_blocking:
            blocking += 1
        elif status.startswith("FAIL"):
            warn += 1
        rows.append([
            str(ac["id"]),
            str(ac.get("flow_scenario") or "-"),
            str(ac.get("verifiable") or "-"),
            str(ac["result"]),
            str(ac.get("severity") or "-"),
            status,
        ])
    print_table(rows)

    total = len(acs)
    passed = sum(1 for r in rows if r[5] == "PASS")
    print()
    print(f"Summary: {passed}/{total} pass | {blocking} blocking | {warn} warn (medium/low fail)")
    if blocking == 0:
        note = "  (warnings need a tracked ticket)" if warn else ""
        print(f"GATE: PASS{note}")
        return 0
    print("GATE: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
