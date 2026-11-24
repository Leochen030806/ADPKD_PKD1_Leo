# -*- coding: utf-8 -*-
"""
LC-20261123-PKD1-newbatch-3-4-7-9  ——  板子放反（旋转 180°）后的文件重命名脚本

原理：96 孔板旋转 180° 后，worksheet 中的孔 (行 r, 列 c)
      实际落在仪器的孔 (行 = 'A'+'H'-r, 列 = 13 - c)。
      例：worksheet A2 -> 实际 H11；worksheet H8 -> 实际 A5。

用法（Windows，cmd / PowerShell）：
    python rename_flipped_plate_LC-20261123.py            # 只预览，不改任何文件
    python rename_flipped_plate_LC-20261123.py --apply    # 复制并重命名到子文件夹 renamed\\
    python rename_flipped_plate_LC-20261123.py --apply --inplace   # 直接在原文件夹改名

默认 --apply 会把文件 *复制* 到 DATA_DIR\\renamed\\，原始文件不动；
同时生成 rename_log.csv 记录 原文件名 / 实际孔位 / 原 worksheet 孔位 / 正确样本名 / 新文件名。
"""
import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

DATA_DIR = Path(r"C:\Users\e1638543\Desktop\MGGEN\ADPKD1\data analysis\CE\CEC data"
                r"\LC-20261123-PKD1-newbatch-3-4-7-9")

ROWS = "ABCDEFGH"

# ---------------- 原 worksheet（你本来想放的位置） ----------------
# 第 1 列在截图里看不到，但实际第 12 列有信号 -> worksheet 第 1 列原本也有东西。
# 请把第 1 列 A-H 的样本名填进来（空着的话，实际第 12 列的文件会被跳过、不改名）。
WORKSHEET = {
    1: ["", "", "", "", "", "", "", ""],  # <-- 请填写 worksheet 第 1 列 A..H
    2: ["GM06384-3", "GM06896-3", "GM06907-3", "GM07175-3",
        "GM07537-3", "GM09153-3", "GM10684-3", "GM17942-3"],
    3: ["GM03037-4", "GM03814-4", "GM04282-4", "GM04479-4",
        "GM04820-4", "GM04856-4", "GM05891-4", "GM06075-4"],
    4: ["GM06384-4", "GM06896-4", "GM06907-4", "GM07175-4",
        "GM07537-4", "GM09153-4", "GM10684-4", "GM17942-4"],
    5: ["GM03037-7", "GM03814-7", "GM04282-7", "GM04479-7",
        "GM04820-7", "GM04856-7", "GM05891-7", "GM06075-7"],
    6: ["GM06384-7", "GM06896-7", "GM06907-7", "GM07175-7",
        "GM07537-7", "GM09153-7", "GM10684-7", "GM17942-7"],
    7: ["GM03037-9", "GM03814-9", "GM04282-9", "GM04479-9",
        "GM04820-9", "GM04856-9", "GM05891-9", "GM06075-9"],
    8: ["GM06384-9", "GM06896-9", "GM06907-9", "GM07175-9",
        "GM07537-9", "GM09153-9", "GM10684-9", "GM17942-9"],
}


def build_actual_map():
    """实际孔位 -> (worksheet 孔位, 正确样本名)"""
    m = {}
    for c, names in WORKSHEET.items():
        for ri, name in enumerate(names):
            ws_well = f"{ROWS[ri]}{c}"
            act_well = f"{ROWS[7 - ri]}{13 - c}"
            m[act_well] = (ws_well, name.strip())
    return m


# 文件名中的孔位：被 _ / - / 空格 / 开头 / 扩展名 包围的 A1..H12（允许 A05 这种补零）
WELL_RE = re.compile(r"(?:(?<=^)|(?<=[_\-\s]))([A-H])(0?[1-9]|1[0-2])(?=[_\-\s.]|$)")


def find_well(stem):
    hits = list(WELL_RE.finditer(stem))
    if not hits:
        return None, None
    h = hits[0]
    return f"{h.group(1)}{int(h.group(2))}", h


def new_name_for(path, sample, match):
    """把孔位之前的部分（通常是原样本名）替换成正确样本名，孔位及之后保持不变。"""
    stem, ext = path.stem, path.suffix
    rest = stem[match.start():]          # 从孔位开始的剩余部分，如 "A05_LC-2026..."
    return f"{sample}_{rest}{ext}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DATA_DIR))
    ap.add_argument("--apply", action="store_true", help="真正执行（默认只预览）")
    ap.add_argument("--inplace", action="store_true", help="在原文件夹直接改名，而不是复制到 renamed\\")
    ap.add_argument("--ext", default=".fsa,.hid,.ab1",
                    help="要处理的扩展名，逗号分隔（默认 .fsa,.hid,.ab1）")
    args = ap.parse_args()

    d = Path(args.dir)
    if not d.is_dir():
        sys.exit(f"找不到文件夹: {d}")
    exts = {e.strip().lower() for e in args.ext.split(",") if e.strip()}
    amap = build_actual_map()

    out_dir = d if args.inplace else d / "renamed"
    rows, skipped = [], []
    for p in sorted(d.iterdir()):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        well, m = find_well(p.stem)
        if well is None:
            skipped.append((p.name, "文件名中找不到孔位"))
            continue
        ws_well, sample = amap.get(well, (None, ""))
        if not sample:
            skipped.append((p.name, f"实际孔位 {well} 在 worksheet 中没有对应样本"))
            continue
        rows.append([p.name, well, ws_well, sample, new_name_for(p, sample, m)])

    # 检查重名
    seen = {}
    for r in rows:
        seen.setdefault(r[4], []).append(r[0])
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    if dup:
        print("!! 以下新文件名重复，已中止：")
        for k, v in dup.items():
            print(f"   {k}  <-  {v}")
        sys.exit(1)

    print(f"{'原文件名':<55} {'实际孔':<6} {'WS孔':<6} {'正确样本':<12} 新文件名")
    for r in rows:
        print(f"{r[0]:<55} {r[1]:<6} {r[2]:<6} {r[3]:<12} {r[4]}")
    if skipped:
        print("\n跳过：")
        for n, why in skipped:
            print(f"   {n}  ({why})")
    print(f"\n共 {len(rows)} 个文件可改名，{len(skipped)} 个跳过。")

    if not args.apply:
        print("\n这是预览。确认无误后加 --apply 执行。")
        return

    out_dir.mkdir(exist_ok=True)
    for old, _, _, _, new in rows:
        src, dst = d / old, out_dir / new
        if dst.exists() and dst != src:
            print(f"!! 目标已存在，跳过: {dst.name}")
            continue
        if args.inplace:
            src.rename(dst)
        else:
            shutil.copy2(src, dst)

    log = out_dir / "rename_log.csv"
    with open(log, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["original_file", "actual_well", "worksheet_well", "correct_sample", "new_file"])
        w.writerows(rows)
    print(f"\n完成。输出文件夹: {out_dir}\n日志: {log}")


if __name__ == "__main__":
    main()
