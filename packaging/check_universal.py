#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path

app = Path(sys.argv[1]).resolve()
bad = []
checked = 0

for path in app.rglob("*"):
    if not path.is_file() or path.is_symlink():
        continue
    try:
        out = subprocess.check_output(["file", str(path)], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        continue
    if "Mach-O" not in out:
        continue
    checked += 1
    arches = set()
    if "arm64" in out:
        arches.add("arm64")
    if "x86_64" in out:
        arches.add("x86_64")
    if not {"arm64", "x86_64"}.issubset(arches):
        bad.append((path.relative_to(app), arches))

print(f"Mach-O files checked: {checked}")
if bad:
    print("The following files are not Universal 2:")
    for path, arches in bad[:100]:
        print(f"  {path} -> {', '.join(sorted(arches)) or 'unknown'}")
    raise SystemExit(1)

print("PASS: all detected Mach-O files contain arm64 and x86_64.")
