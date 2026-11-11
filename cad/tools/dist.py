#!/usr/bin/env python3
"""Release bundles: the print files, the STLs and the prebuilt firmware as zips in dist/ at the repository root, with
their SHA-256 sums. The same inputs give the same bytes (fixed timestamps, sorted entries). Each zip carries the licence
that applies to its contents and a short README.txt.

    python3 cad/tools/dist.py [TAG]      (or: make dist TAG=v2026.11.11)
"""
import hashlib
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = "https://github.com/tsuyoshi-otake/paperdiy-pda-terminal"
STAMP = (2026, 1, 1, 0, 0, 0)            # every entry: fixed, so the zips do not change from run to run


def files(folder, exts, recursive=True):
    """(path in the repository, path below `folder`) of every file under `folder` with one of `exts`, sorted."""
    out = []
    for base, dirs, names in os.walk(os.path.join(ROOT, folder)):
        dirs.sort()
        if not recursive:
            dirs[:] = []
        for n in sorted(names):
            if n.lower().endswith(exts):
                p = os.path.join(base, n)
                out.append((p, os.path.relpath(p, os.path.join(ROOT, folder))))
    return out


def readme(tag, title, lines, licence):
    return "\n".join([f"PaperDIY PDA Terminal {tag}: {title}", REPO, ""] + lines + ["", licence, ""]).encode("utf-8")


def write_zip(name, entries):
    """entries: [(name in the zip, bytes)]."""
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    path = os.path.join(ROOT, "dist", name)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, data in sorted(entries):
            info = zipfile.ZipInfo(arc, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return path


def read(path):
    with open(path, "rb") as f:
        return f.read()


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "dev"
    docs = f"{REPO}/blob/{tag}" if tag != "dev" else f"{REPO}/blob/main"
    fw = read(os.path.join(ROOT, "firmware", "version.txt")).decode().strip()
    cc = ("Licence: CC BY-NC 4.0 (non-commercial), adapted from \"The PDA Terminal\" / phone-enclosure by Un Kyu Lee. "
          "See LICENSE.md.")
    case_licence = [("LICENSE.md", read(os.path.join(ROOT, "cad", "LICENSE.md")))]
    guide = [f"Assembly guide (Japanese): {docs}/cad/ASSEMBLY_ja.md", f"Details (English): {docs}/cad/README.md",
             "Nothing needs supports. Print plate 0 (the test coupons) first."]
    made = []

    made.append(write_zip("paperdiy-pda-case-bambu-a1mini.zip", case_licence + [
        ("README.txt", readme(tag, "Bambu Studio projects for the Bambu Lab A1 mini, 0.4 mm nozzle", [
            "Open bambu_plate0_test_coupons.3mf ... bambu_plate3_panel.3mf with File > Open Project (Bambu Studio 2.0 or",
            "later): printer, plate type, filament and process are selected. Check the four boxes after opening; if they",
            "are not as described in the guide, open the plain plates of paperdiy-pda-case-3mf.zip instead and import",
            "paperdiy_process_a1mini_04.json (File > Import > Import Configs)."] + guide, cc))
    ] + [(rel, read(p)) for p, rel in files("cad/3mf/bambu_a1mini", (".3mf", ".json"))]))

    made.append(write_zip("paperdiy-pda-case-3mf.zip", case_licence + [
        ("README.txt", readme(tag, "print plates (3MF, geometry only, any slicer)", [
            "plate0_test_coupons.3mf ... plate3_panel.3mf: split parts on a 180 x 180 mm plate (Bambu Lab A1 mini).",
            "large/: lid, tray and panel in one piece each on a 220 x 220 mm plate, nothing to glue.",
            "usb_variants/, large/usb_variants/: lids for a panel-mount female USB-C (ears 16 to 30 mm apart, or none).",
            "The files carry no print settings: see chapter 2 of the guide."] + guide, cc))
    ] + [(rel, read(p)) for p, rel in files("cad/3mf", (".3mf",)) if not rel.startswith("bambu_a1mini")]))

    made.append(write_zip("paperdiy-pda-case-stl.zip", case_licence + [
        ("README.txt", readme(tag, "the single parts as STL", [
            "split/: the pieces for a 180 mm bed and their splice plates; whole/: lid, tray and panel in one piece;",
            "coupons/: the test coupons; the files next to this one: hinge covers, the unsplit checked parts and the",
            "kit's envelope. The 3MF plates hold the same parts already oriented for printing."] + guide, cc))
    ] + [(rel, read(p)) for p, rel in files("cad/out", (".stl",))]))

    pre = os.path.join(ROOT, "firmware", "prebuilt")
    made.append(write_zip(f"paperdiy-term-firmware-{fw}.zip", [
        ("README.txt", readme(tag, f"firmware {fw} for the M5Stack PaperDIY (ESP32-S3)", [
            "paperdiy-term-merged.bin: write at 0x0 for the first install (erases the settings).",
            "paperdiy-term-app.bin: write at 0x20000 to update and keep the settings.",
            f"How to flash and use (Japanese): {docs}/firmware/README.md",
            "Build conditions: BUILDINFO.md. Check the downloads with SHA256SUMS."],
            "Licence: MIT (LICENSE); the libraries built in are listed in THIRD_PARTY_NOTICES.md.")),
        ("LICENSE", read(os.path.join(ROOT, "LICENSE")))
    ] + [(n, read(os.path.join(pre, n))) for n in sorted(os.listdir(pre)) if os.path.isfile(os.path.join(pre, n))]))

    with open(os.path.join(ROOT, "dist", "SHA256SUMS"), "w") as f:
        for p in made:
            f.write(f"{hashlib.sha256(read(p)).hexdigest()}  {os.path.basename(p)}\n")
    for p in made:
        with zipfile.ZipFile(p) as z:
            print(f"{os.path.relpath(p, ROOT)}: {len(z.namelist())} files, {os.path.getsize(p) / 1e6:.2f} MB")
    print("dist/SHA256SUMS")


if __name__ == "__main__":
    main()
