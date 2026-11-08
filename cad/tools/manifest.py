#!/usr/bin/env python3
"""Fingerprints of every generated CAD file, to show that a rebuild reproduces the committed outputs.

    python3 tools/manifest.py --write     # record out/ and 3mf/ in out/MANIFEST.json (after a deliberate change)
    python3 tools/manifest.py --check     # compare the current files with out/MANIFEST.json (exit 1 on a mismatch)

Each STL is recorded with its SHA-256 and its geometry (volume, bounding box, triangle count); each 3MF with its
SHA-256 and the volume of every object in it. --check accepts a file whose bytes differ only if its geometry
matches to 0.01 mm / 0.01 % (another CPU or library build may round the last digit differently); anything else
is a real change and fails.
"""
import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np
import trimesh

CAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(CAD, "out", "MANIFEST.json")
PATTERNS = ["out/*.stl", "out/split/*.stl", "out/split/usb_variants/*.stl", "out/split/splice/*.stl", "out/whole/*.stl", "out/whole/usb_variants/*.stl",
            "out/coupons/*.stl", "out/assembly.json", "out/coupons/orientation.json", "3mf/*.3mf", "3mf/usb_variants/*.3mf",
            "3mf/large/*.3mf", "3mf/large/usb_variants/*.3mf"]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def geometry(path):
    if path.endswith(".stl"):
        m = trimesh.load(path)
        return {"volume": round(float(m.volume), 2), "bbox": np.round(m.bounds, 3).tolist(), "faces": len(m.faces)}
    if path.endswith(".3mf"):
        sc = trimesh.load(path)
        geoms = sc.dump() if isinstance(sc, trimesh.Scene) else [sc]
        return {"objects": len(geoms), "volumes": sorted(round(float(g.volume), 2) for g in geoms)}
    return {}


def collect():
    files = sorted({os.path.relpath(p, CAD) for pat in PATTERNS for p in glob.glob(os.path.join(CAD, pat))})
    return {f: {"sha256": sha(os.path.join(CAD, f)), **geometry(os.path.join(CAD, f))} for f in files}


def same_geometry(a, b):
    if "volume" in a:
        return (abs(a["volume"] - b["volume"]) <= max(0.01, 1e-4 * abs(a["volume"]))
                and np.allclose(a["bbox"], b["bbox"], atol=0.01))
    if "volumes" in a:
        return a["objects"] == b["objects"] and np.allclose(a["volumes"], b["volumes"], rtol=1e-4, atol=0.01)
    return False


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    now = collect()
    if args.write:
        with open(MANIFEST, "w") as f:
            json.dump(now, f, indent=1, sort_keys=True)
            f.write("\n")
        print(f"wrote {os.path.relpath(MANIFEST, CAD)}: {len(now)} files")
        return 0
    with open(MANIFEST) as f:
        ref = json.load(f)
    identical = geom_only = 0
    problems = []
    for name in sorted(set(ref) | set(now)):
        if name not in now:
            problems.append(f"missing   {name}")
        elif name not in ref:
            problems.append(f"new       {name} (not in the manifest)")
        elif now[name]["sha256"] == ref[name]["sha256"]:
            identical += 1
        elif same_geometry(now[name], ref[name]):
            geom_only += 1
        else:
            problems.append(f"changed   {name}: {ref[name]} -> {now[name]}")
    print(f"{identical} files byte-identical, {geom_only} with the same geometry but different bytes, "
          f"{len(problems)} problems")
    for p in problems:
        print("  " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
