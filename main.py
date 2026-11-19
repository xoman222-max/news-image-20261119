#!/usr/bin/env python3
"""v2 entry: one image summing up the world news of Thursday 19 November 2026.

The image is drawn by renderer.py from stories.json (50 real,
date-checked stories in the 11/17 champion's layout) and bundled in
this repository as entry.png. This program only copies it to the
grader's output directory: the grader container runs Python 3.13
standard library only, with nothing installed, so the entrypoint
itself uses nothing but the standard library.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   -> out/entry.png
"""

import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "entry.png")
    except OSError:
        os.makedirs("out", exist_ok=True)
        path = os.path.join("out", "entry.png")
    shutil.copyfile(HERE / "entry.png", path)
    # The bundled image is byte-identical to what renderer.py draws
    # from stories.json, so every run writes the same bytes.
    print(f"wrote {path} ({os.path.getsize(path)} bytes, 1024x1024)")


if __name__ == "__main__":
    main()
