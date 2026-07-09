#!/usr/bin/env python3
"""Build agent-browser-qa.skill — a zip bundle for one-file install.

The .skill file is NOT committed (it duplicates the source and goes stale).
Run this to (re)generate it, then attach the output to a GitHub Release.

    python scripts/build-skill.py

Bundle contents: SKILL.md + assets/* + references/* + examples/* + the runtime
scripts/*.py (coverage-check, release-summary — referenced by the docs, so they
must ship) + requirements.txt, under an `agent-browser-qa/` prefix. README, docs,
LICENSE, the build script itself, and .git are excluded.
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
    # runtime scripts referenced by the docs (exclude the bundler itself)
    files += [f for f in sorted(glob.glob("scripts/*.py", root_dir=ROOT))
              if os.path.basename(f) != "build-skill.py"]
    files.append("requirements.txt")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(ROOT, f), "agent-browser-qa/" + f.replace("\\", "/"))
    print(f"Built {OUT} ({len(files)} entries)")
    for f in files:
        print("  agent-browser-qa/" + f.replace("\\", "/"))


if __name__ == "__main__":
    main()
