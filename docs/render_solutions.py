#!/usr/bin/env python3
# render_solutions.py
# 讀取 experiments/ 中各組 SAT 解答與 placements 對照表，
# 驗證每組解答合法後，輸出一張總覽圖 docs/solutions.svg。
# 只使用 Python 標準函式庫。

import ast
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = DOCS_DIR.parent / "experiments"
OUTPUT_FILE = DOCS_DIR / "solutions.svg"

NUM_PIECES = 11

# (標題, 資料夾, 盤面高, 盤面寬, 解答檔, 對照表)
CASES = [
    ("9x17 · Model A", "9x17/model_A", 9, 17, "solution_9x17_modelA.txt", "placements.txt"),
    ("9x17 · Model B", "9x17/model_B", 9, 17, "solution_9x17_modelB.txt", "placements_9x17_hybrid.txt"),
    ("9x17 · Model C", "9x17/model_C", 9, 17, "solution_9x17_modelC.txt", "placements_9x17_hybrid_amo.txt"),
    ("10x15 · Model A", "10x15/model_A", 10, 15, "solution_10x15_modelA.txt", "placements_10x15_simple.txt"),
    ("10x15 · Model B", "10x15/model_B", 10, 15, "solution_10x15_modelB.txt", "placements_10x15_hybrid.txt"),
    ("10x15 · Model C", "10x15/model_C", 10, 15, "solution_10x15_modelC.txt", "placements_10x15_hybrid_amo.txt"),
    ("12x12 · Model C + symmetry breaking", "12x12/model_C_symmetry", 12, 12,
     "solution_12x12_modelC_symmetry.txt", "placements_12x12_final.txt"),
]
ROWS = [[0, 1, 2], [3, 4, 5], [6]]

# 與 generate 腳本中的 pieces_raw 相同，只用於畫圖例
PIECES_RAW = [
    ["10", "10", "11", "01", "01"], ["011", "010", "110", "010"],
    ["100", "111", "010", "010"], ["111", "010", "010", "010"],
    ["010", "011", "110", "100"], ["001", "011", "110", "100"],
    ["010", "011", "110", "010"], ["110", "010", "011", "001"],
    ["0001", "1111", "0010"], ["0010", "1111", "0010"],
    ["1000", "1111", "0001"],
]
PIECE_LABELS = "0123456789A"

COLORS = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
    "#b07aa1", "#ff9da7", "#9c755f", "#555555", "#b6992d",
]
EMPTY_COLOR = "#ececec"
TEXT_COLOR = "#333333"

CELL = 16
PANEL_GAP = 28
TITLE_H = 22
TITLE_CHAR_W = 7.5  # 13px 粗體 sans-serif 的估計字寬，用來避免標題與右側內容重疊
MARGIN = 20
LEGEND_CELL = 9


def read_true_vars(path):
    """讀取 CaDiCaL（'v' 行）或 MiniSat（'SAT' + 賦值）格式的解答。"""
    true_vars = set()
    with open(path, encoding="latin-1") as f:
        for line in f:
            tokens = line.split()
            if not tokens or tokens[0] in ("c", "s"):
                continue
            for tok in tokens:
                if tok.lstrip("-").isdigit() and int(tok) > 0:
                    true_vars.add(int(tok))
    return true_vars


def read_chosen_placements(path, true_vars):
    chosen = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(",", 5)
            if len(parts) != 6 or not parts[0].isdigit():
                continue
            if int(parts[0]) in true_vars:
                chosen.append((int(parts[1]), ast.literal_eval(parts[5])))
    return chosen


def build_board(title, chosen, h, w):
    """回傳 {(r, c): piece}，並檢查解答是否合法。"""
    pieces = sorted(p for p, _ in chosen)
    if pieces != list(range(NUM_PIECES)):
        raise SystemExit(f"{title}: 拼圖編號不正確 {pieces}")
    owner = {}
    for p, cells in chosen:
        for (r, c) in cells:
            if not (0 <= r < h and 0 <= c < w):
                raise SystemExit(f"{title}: 格子 {(r, c)} 超出盤面")
            if (r, c) in owner:
                raise SystemExit(f"{title}: 格子 {(r, c)} 重疊")
            owner[(r, c)] = p
    for (r, c), p in owner.items():
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                q = owner.get((r + dr, c + dc))
                if q is not None and q != p:
                    raise SystemExit(f"{title}: 拼圖 {p} 與 {q} 在 {(r, c)} 附近接觸")
    return owner


def svg_board(x0, y0, title, owner, h, w):
    out = [f'<text x="{x0}" y="{y0 + 15}" class="title">{title}</text>']
    top = y0 + TITLE_H
    for r in range(h):
        for c in range(w):
            p = owner.get((r, c))
            color = EMPTY_COLOR if p is None else COLORS[p]
            out.append(
                f'<rect x="{x0 + c * CELL}" y="{top + r * CELL}" '
                f'width="{CELL - 1}" height="{CELL - 1}" rx="2" fill="{color}"/>'
            )
    return out


def svg_legend(x0, y0):
    out = [f'<text x="{x0}" y="{y0 + 15}" class="title">Pieces</text>']
    top = y0 + TITLE_H
    slot_w = 5 * LEGEND_CELL + 12
    slot_h = 5 * LEGEND_CELL + 20
    for i, rows in enumerate(PIECES_RAW):
        sx = x0 + (i % 6) * slot_w
        sy = top + (i // 6) * slot_h
        out.append(f'<text x="{sx}" y="{sy + 10}" class="label">{PIECE_LABELS[i]}</text>')
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == "1":
                    out.append(
                        f'<rect x="{sx + c * LEGEND_CELL}" y="{sy + 14 + r * LEGEND_CELL}" '
                        f'width="{LEGEND_CELL - 1}" height="{LEGEND_CELL - 1}" rx="1" fill="{COLORS[i]}"/>'
                    )
    return out, 6 * slot_w, TITLE_H + 2 * slot_h


def main():
    boards = []
    for title, folder, h, w, sol, plc in CASES:
        d = EXPERIMENTS_DIR / folder
        chosen = read_chosen_placements(d / plc, read_true_vars(d / sol))
        boards.append(build_board(title, chosen, h, w))
        print(f"OK  {title}: 11 塊拼圖、66 格、無接觸")

    body = []
    y = MARGIN
    total_w = 0
    for row in ROWS:
        x = MARGIN
        row_h = 0
        for idx in row:
            title, _, h, w, _, _ = CASES[idx]
            body += svg_board(x, y, title, boards[idx], h, w)
            x += max(w * CELL, int(len(title) * TITLE_CHAR_W)) + PANEL_GAP
            row_h = max(row_h, TITLE_H + h * CELL)
        if row == ROWS[-1]:
            legend, legend_w, legend_h = svg_legend(x + 12, y)
            body += legend
            x += 12 + legend_w + PANEL_GAP
            row_h = max(row_h, legend_h)
        total_w = max(total_w, x - PANEL_GAP + MARGIN)
        y += row_h + PANEL_GAP
    total_h = y - PANEL_GAP + MARGIN

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}">',
        "<style>"
        f".title{{font:600 13px sans-serif;fill:{TEXT_COLOR}}}"
        f".label{{font:600 11px sans-serif;fill:{TEXT_COLOR}}}"
        "</style>",
        f'<rect width="{total_w}" height="{total_h}" fill="#ffffff"/>',
        *body,
        "</svg>",
    ]
    OUTPUT_FILE.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"已輸出 {OUTPUT_FILE.relative_to(DOCS_DIR.parent)}")


if __name__ == "__main__":
    sys.exit(main())
