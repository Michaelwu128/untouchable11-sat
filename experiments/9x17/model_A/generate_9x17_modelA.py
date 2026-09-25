#!/usr/bin/env python3
# generate_cnf_compact.py
# 產生 9x17 版本的 placement-level CNF + placements.txt 映射檔

import itertools
import json

# ---------- 參數：棋盤大小 ----------
BOARD_H = 9
BOARD_W = 17

# ---------- 你的 11 塊拼圖（用字串列表示，每行用 '1'/'0'） ----------
pieces_raw = [
    ["10","10","11","01","01"],       # piece 1
    ["011","010","110","010"],        # piece 2
    ["100","111","010","010"],        # piece 3
    ["111","010","010","010"],        # piece 4
    ["010","011","110","100"],        # piece 5
    ["001","011","110","100"],        # piece 6
    ["010","011","110","010"],        # piece 7
    ["110","010","011","001"],        # piece 8
    ["0001","1111","0010"],           # piece 9
    ["0010","1111","0010"],           # piece 10
    ["1000","1111","0001"],           # piece 11
]

# ---------- 轉換成二維整數矩陣 ----------
def str_rows_to_matrix(rows):
    return [[1 if c=='1' else 0 for c in row] for row in rows]

pieces = [str_rows_to_matrix(r) for r in pieces_raw]

# ---------- 生成變形（旋轉 + 翻面），去重 ----------
def rotate90(mat):
    h = len(mat); w = len(mat[0])
    return [[mat[h-1-r][c] for r in range(h)] for c in range(w)]

def flip_h(mat):
    return [row[::-1] for row in mat]

def flip_v(mat):
    return mat[::-1]

def mat_to_tuple(mat):
    return tuple(tuple(row) for row in mat)

def generate_transforms(piece):
    seen = set()
    out = []
    m = piece
    for k in range(4):
        if k>0:
            m = rotate90(m)
        # original rotation
        for cand in (m, flip_h(m), flip_v(m)):
            t = mat_to_tuple(cand)
            if t not in seen:
                seen.add(t)
                out.append([list(row) for row in t])
    return out

# ---------- helper: occupied cells for a placed transform at (x,y) ----------
def occupied_cells(mat, x, y):
    cells = []
    h = len(mat); w = len(mat[0])
    for i in range(h):
        for j in range(w):
            if mat[i][j]:
                cells.append((x+i, y+j))
    return cells

# ---------- 產生所有合法 placement（在棋盤內）並分配 var id ----------
placements = []  # list of dicts: {var, piece, transform_index, x,y, cells}
var_counter = 1

all_piece_transforms = [generate_transforms(p) for p in pieces]

for p_idx, transforms in enumerate(all_piece_transforms):
    for f_idx, t in enumerate(transforms):
        th = len(t); tw = len(t[0])
        for x in range(BOARD_H - th + 1):
            for y in range(BOARD_W - tw + 1):
                cells = occupied_cells(t, x, y)
                # sanity: cells must be within [0..BOARD_H-1] x [0..BOARD_W-1]
                valid = all(0 <= cx < BOARD_H and 0 <= cy < BOARD_W for (cx,cy) in cells)
                if not valid:
                    continue
                placements.append({
                    "var": var_counter,
                    "piece": p_idx,
                    "transform": f_idx,
                    "x": x,
                    "y": y,
                    "cells": cells
                })
                var_counter += 1

num_vars = var_counter - 1
print(f"總合法 placement 數量: {len(placements)}  => 變數數量 {num_vars}")

# ---------- 建立索引：每塊拼圖的 placement list ----------
placements_by_piece = {}
for plc in placements:
    placements_by_piece.setdefault(plc["piece"], []).append(plc)

# ---------- 產生子句 ----------
clauses = []

# 每塊至少放一次（OR）
for p_idx in range(len(pieces)):
    plcs = placements_by_piece.get(p_idx, [])
    if not plcs:
        raise SystemExit(f"錯誤：拼圖 {p_idx} 沒有任何合法放置位置！")
    clause = [plc["var"] for plc in plcs]
    clauses.append(clause)

# 每塊最多放一次（pairwise -a -b）
for p_idx, plcs in placements_by_piece.items():
    for a, b in itertools.combinations(plcs, 2):
        clauses.append([-a["var"], -b["var"]])

# 不同拼圖之間：若重疊或相鄰 (3x3)，禁止同時成立
# 我們建立一 hash map 以免每次都重複檢查慢
# 但 placements 數量通常比原本少很多，所以直接 pairwise 檢查也可行
for p1_idx, p2_idx in itertools.combinations(range(len(pieces)), 2):
    pl1 = placements_by_piece.get(p1_idx, [])
    pl2 = placements_by_piece.get(p2_idx, [])
    for a in pl1:
        cells1 = a["cells"]
        for b in pl2:
            cells2 = b["cells"]
            # overlap?
            if any(c in cells2 for c in cells1):
                clauses.append([-a["var"], -b["var"]])
                continue
            # adjacency (3x3) : any pair with |dx|<=1 and |dy|<=1
            adj = False
            for (x1,y1) in cells1:
                for (x2,y2) in cells2:
                    if abs(x1-x2) <= 1 and abs(y1-y2) <= 1:
                        adj = True
                        break
                if adj:
                    break
            if adj:
                clauses.append([-a["var"], -b["var"]])

num_clauses = len(clauses)
print(f"產生子句總數: {num_clauses}")

# ---------- 寫 DIMACS CNF 與 placements 對照表 ----------
cnf_name = "untouchable_9x17.cnf"
placements_name = "placements.txt"

with open(cnf_name, "w") as f:
    f.write(f"p cnf {num_vars} {num_clauses}\n")
    for cl in clauses:
        f.write(" ".join(map(str, cl)) + " 0\n")

with open(placements_name, "w") as f:
    # write csv-like: var,piece,transform,x,y,cells
    for plc in placements:
        f.write(f"{plc['var']},{plc['piece']},{plc['transform']},{plc['x']},{plc['y']},{plc['cells']}\n")

print(f"寫檔完成: {cnf_name} ({num_vars} vars, {num_clauses} clauses)")
print(f"placements map 存成: {placements_name}")
print("接下來可以用 minisat untouchable_9x17.cnf solution.txt 求解")
