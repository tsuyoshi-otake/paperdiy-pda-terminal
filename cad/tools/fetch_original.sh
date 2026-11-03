#!/usr/bin/env bash
# Fetch the original phone-enclosure (Un Kyu Lee, CC BY-NC 4.0) at the commit this design is built from and check
# the three STLs the build reads. The pinned commit and hashes live in src/params.py (ORIG_COMMIT, ORIG_SHA256).
#   tools/fetch_original.sh [destination]        default: ~/phone-enclosure
# Then build with  PHONE_ENCLOSURE_STL=<destination>/STL python3 src/build.py  (the default path needs no variable).
set -euo pipefail
cd "$(dirname "$0")/.."
DEST="${1:-$HOME/phone-enclosure}"
read -r REPO COMMIT < <(python3 -c 'import sys; sys.path.insert(0, "src"); import params as p; print(p.ORIG_REPO, p.ORIG_COMMIT)')
if [ ! -d "$DEST/.git" ]; then
  git clone --quiet --filter=blob:none "$REPO" "$DEST"
fi
git -C "$DEST" fetch --quiet origin "$COMMIT" 2>/dev/null || git -C "$DEST" fetch --quiet origin
git -C "$DEST" -c advice.detachedHead=false checkout --quiet "$COMMIT"
python3 - "$DEST/STL" <<'PY'
import hashlib, os, sys
sys.path.insert(0, "src")
import params as p
bad = 0
for name, want in p.ORIG_SHA256.items():
    got = hashlib.sha256(open(os.path.join(sys.argv[1], name), "rb").read()).hexdigest()
    print(f"{'OK ' if got == want else 'BAD'} {name}")
    bad += got != want
sys.exit(bad)
PY
echo "original STLs ready in $DEST/STL (commit ${COMMIT:0:7})"
