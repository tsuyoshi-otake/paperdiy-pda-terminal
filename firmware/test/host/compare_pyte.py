#!/usr/bin/env python3
"""Replay captured terminal sessions through the firmware's VT emulator (./snap) and through pyte, a
Python reference emulator, and compare the 80x24 screens and cursor at six points of each capture.

    python3 compare_pyte.py fixtures/*.raw        # run by `make test`; needs `pip install pyte==0.8.2`

pyte has no alternate screen (DECSET 1049), so programs that use it (vim, less, nano) differ from pyte once
they exit back to the shell; EXPECTED lists how many of the six snapshots must match for each capture.
"""
import os
import subprocess
import sys

import pyte

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snap")
EXPECTED = {"top.raw": 6, "bash.raw": 6, "tmux.raw": 6, "vim.raw": 5, "less.raw": 5, "nano.raw": 5}


class Screen(pyte.Screen):
    def select_graphic_rendition(self, *a, private=False, **k):   # ignore private SGR (CSI > ... m)
        if private:
            return
        return super().select_graphic_rendition(*a)


def pyte_snaps(data, offsets):
    scr = Screen(80, 24)
    st = pyte.ByteStream(scr)
    out, pos = [], 0
    for end in offsets:
        st.feed(data[pos:end])
        pos = end
        lines = ["".join(scr.buffer[y][x].data for x in range(80)).rstrip() for y in range(24)]
        out.append((end, scr.cursor.x, scr.cursor.y, lines))
    return out


def main(files):
    failed = 0
    for name in files:
        data = open(name, "rb").read()
        offs = sorted(set([len(data) * k // 6 for k in range(1, 6)] + [len(data)]))
        ref = pyte_snaps(data, offs)
        res = subprocess.run([SNAP, name] + [str(o) for o in offs[:-1]], capture_output=True, text=True, errors="replace")
        if res.returncode != 0:
            print(f"{name}: CRASH\n{res.stderr[-2000:]}")
            failed += 1
            continue
        blocks = res.stdout.split("\x01SNAP")[1:]
        same = 0
        for (end, cx, cy, lines), blk in zip(ref, blocks):
            hdr, *mine = blk.split("\n")
            mine = mine[:24]
            mcx, mcy = map(int, hdr.split()[2:4])
            diffs = [y for y in range(24) if lines[y] != mine[y]]
            if not diffs and (cx, cy) == (mcx, mcy):
                same += 1
            elif os.environ.get("VERBOSE"):
                print(f"  {name} @{end}: cursor ref=({cx},{cy}) firmware=({mcx},{mcy}), rows differ: {diffs}")
        need = EXPECTED.get(os.path.basename(name), len(ref))
        ok = same >= need
        failed += not ok
        print(f"{os.path.basename(name)}: {same}/{len(ref)} snapshots identical to pyte (need {need}) "
              f"{'OK' if ok else 'FAIL'}")
    return failed


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
