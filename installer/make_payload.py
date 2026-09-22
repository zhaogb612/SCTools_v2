# -*- coding: utf-8 -*-
"""把 dist/SCTools2 打成载荷 zip（内容直接位于 zip 根，不含父目录）"""
import os
import sys
import zipfile

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "dist", "SCTools2")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
OUT = os.path.join(OUT_DIR, "payload.zip")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    n = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _dirs, files in os.walk(SRC):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, SRC))
                n += 1
    print("payload: {} files -> {}".format(n, OUT))


if __name__ == "__main__":
    sys.exit(main())
