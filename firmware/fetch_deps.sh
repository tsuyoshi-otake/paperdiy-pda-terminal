#!/usr/bin/env bash
# Fetch third-party components at the revisions this firmware was built against.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p deps
fetch() { # name url commit
  local name=$1 url=$2 commit=$3
  if [ ! -d "deps/$name/.git" ]; then
    git clone --filter=blob:none "$url" "deps/$name"
  fi
  git -C "deps/$name" fetch --depth 1 origin "$commit" 2>/dev/null || true
  git -C "deps/$name" checkout -q "$commit"
}
fetch M5GFX       https://github.com/m5stack/M5GFX.git       7cb26b44ab31bb41a0a597196dd2c6d868869a21  # 0.2.36
fetch M5Unified   https://github.com/m5stack/M5Unified.git   44952cb8e4ac88bf04ad23b9dfd6f4b05c788348  # 0.2.29
fetch libssh2-src https://github.com/libssh2/libssh2.git     a312b43325e3383c865a87bb1d26cb52e3292641  # libssh2-1.11.1

# M5Unified declares m5gfx as a managed dependency; we use the local checkout instead
# (same adaptation as M5Stack's own PaperDIY factory firmware).
python3 - <<'PY'
import re, pathlib
p = pathlib.Path("deps/M5Unified/idf_component.yml")
s = p.read_text()
s2 = re.sub(r"\ndependencies:\n(?:  .*\n?)*", "\n", s)
if s2 != s:
    p.write_text(s2)
    print("patched", p)
PY
echo "deps ready"
