#!/usr/bin/env python3
"""Build agent-browser-qa.skill — a zip bundle for one-file install.

The .skill file is NOT committed (it duplicates the source and goes stale).
Run this to (re)generate it, then attach the output to a GitHub Release.

    python scripts/build-skill.py

Bundle contents: SKILL.md + assets/* + references/* + examples/* under an
`agent-browser-qa/` prefix. README, docs, LICENSE and .git are excluded.
"""
import glob
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "agent-browser-qa.skill")


def main():
    files = ["SKILL.md"]
    files += sorted(glob.glob("assets/*", root_dir=ROOT))
    files += sorted(glob.glob("references/*", root_dir=ROOT))
    files += sorted(glob.glob("examples/*", root_dir=ROOT))
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(ROOT, f), "agent-browser-qa/" + f.replace("\\", "/"))
    print(f"Built {OUT} ({len(files)} entries)")
    for f in files:
        print("  agent-browser-qa/" + f.replace("\\", "/"))


if __name__ == "__main__":
    main()
