#!/usr/bin/env python3
# generate_cnf_hybrid_10x15.py
# 產生 10x15 版本的 "混合式" CNF，效能更高。
# 它使用兩種變數：
# 1. 放置變數 v(p,o,x,y) [ID: 1 ... N]
# 2. 格子變數 c(r,c,p)   [ID: N+1 ... M]
# 並在兩者之間建立 "通道" (Channeling) 子句。

import itertools
import json
import collections

# ---------- 參數：棋盤大小 ----------
BOARD_H = 10  # <<< 修改處
BOARD_W = 15  # <<< 修改處
NUM_PIECES = 11

# ---------- 你的 11 塊拼圖（用字串列表示，每行用 '1'/'0'） ----------
pieces_raw = [
    ["10","10","11","01","01"],       # piece 0
    ["011","010","110","010"],        # piece 1
    ["100","111","010","010"],        # piece 2
    ["111","010","010","010"],        # piece 3
    ["010","011","110","100"],        # piece 4
    ["001","011","110","100"],        # piece 5
    ["010","011","110","010"],        # piece 6
    ["110","010","011","001"],        # piece 7
    ["0001","1111","0010"],           # piece 8
    ["0010","1111","0010"],           # piece 9
    ["1000","1111","0001"],           # piece 10
]

# ---------- 轉換成二維整數矩陣 ----------
def str_rows_to_matrix(rows):
    return [[1 if c=='1' else 0 for c in row] for row in rows]

pieces = [str_rows_to_matrix(r) for r in pieces_raw]
assert len(pieces) == NUM_PIECES

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

# ---------- 
# --- 階段 1: 建立 "放置變數" v(p,o,x,y)
# ----------
print("階段 1: 建立 '放置變數' v(p,o,x,y)")
placements = []  # {var, piece, transform, x, y, cells}
placements_by_piece = collections.defaultdict(list)
# 輔助索引: placements_covering[(r,c)][p] = [v1, v2, ...]
placements_covering = collections.defaultdict(lambda: collections.defaultdict(list))

var_counter = 1
all_piece_transforms = [generate_transforms(p) for p in pieces]

for p_idx, transforms in enumerate(all_piece_transforms):
    for f_idx, t in enumerate(transforms):
        th = len(t); tw = len(t[0])
        # 迴圈範圍會自動使用新的 10x15 參數
        for x in range(BOARD_H - th + 1):
            for y in range(BOARD_W - tw + 1):
                cells = occupied_cells(t, x, y)
                valid = all(0 <= cx < BOARD_H and 0 <= cy < BOARD_W for (cx,cy) in cells)
                if not valid:
                    continue
                
                plc = {
                    "var": var_counter,
                    "piece": p_idx,
                    "transform": f_idx,
                    "x": x,
                    "y": y,
                    "cells": cells
                }
                placements.append(plc)
                placements_by_piece[p_idx].append(plc)
                
                for (r, c) in cells:
                    placements_covering[(r, c)][p_idx].append(var_counter)
                    
                var_counter += 1

num_placement_vars = var_counter - 1
print(f"  > 找到 {len(placements)} 個合法放置, 分配變數 ID 1..{num_placement_vars}")

# ---------- 
# --- 階段 2: 建立 "格子變數" c(r,c,p)
# ----------
print("階段 2: 建立 '格子變數' c(r,c,p)")

cell_var_start_id = num_placement_vars + 1
# 變數數量會自動根據 10x15 重新計算
num_cell_vars = BOARD_H * BOARD_W * NUM_PIECES
total_vars = num_placement_vars + num_cell_vars

def get_cell_var(r, c, p):
    """將 (r,c,p) 座標映射到一個全域唯一的變數 ID"""
    if not (0 <= r < BOARD_H and 0 <= c < BOARD_W and 0 <= p < NUM_PIECES):
        raise IndexError("get_cell_var 索引超出範圍")
    # get_cell_var 依賴 BOARD_W 來計算 offset，這會自動使用 15
    cell_index = (r * BOARD_W) + c
    offset = (cell_index * NUM_PIECES) + p
    return cell_var_start_id + offset

print(f"  > 建立 {num_cell_vars} 個格子變數, ID {cell_var_start_id}..{total_vars}")

# ---------- 
# --- 階段 3: 產生子句
# ----------
clauses = []

# --- 規則 1: 每塊拼圖剛好放置一次 (使用 v 變數) ---
print("階段 3 (1/4): 產生 'Exactly-One' (放置) 子句...")
for p_idx in range(NUM_PIECES):
    plcs = placements_by_piece.get(p_idx, [])
    if not plcs:
        raise SystemExit(f"錯誤：拼圖 {p_idx} 在 10x15 棋盤上沒有任何合法放置位置！")
    
    clauses.append([plc["var"] for plc in plcs])
    for a, b in itertools.combinations(plcs, 2):
        clauses.append([-a["var"], -b["var"]])

# --- 規則 2: 通道子句 (v -> c) ---
print("階段 3 (2/4): 產生通道子句 (v -> c)...")
for plc in placements:
    v_var = plc["var"]
    p_idx = plc["piece"]
    for (r, c) in plc["cells"]:
        c_var = get_cell_var(r, c, p_idx)
        clauses.append([-v_var, c_var])

# --- 規則 3: 通道子句 (c -> v) ---
print("階段 3 (3/4): 產生通道子句 (c -> v)...")
# 迴圈會自動使用 10x15 的範圍
for r, c, p in itertools.product(range(BOARD_H), range(BOARD_W), range(NUM_PIECES)):
    c_var = get_cell_var(r, c, p)
    v_list = placements_covering[(r, c)].get(p, [])
    clause = [-c_var] + v_list
    clauses.append(clause)

# --- 規則 4: 衝突子句 (使用 c 變數) ---
print("階段 3 (4/4): 產生衝突子句 (格子層)...")
# 迴圈會自動使用 10x15 的範圍
for r, c in itertools.product(range(BOARD_H), range(BOARD_W)):
    
    # (A) 無重疊
    cell_vars_for_rc = [get_cell_var(r, c, p) for p in range(NUM_PIECES)]
    for i in range(NUM_PIECES):
        for j in range(i + 1, NUM_PIECES):
            clauses.append([-cell_vars_for_rc[i], -cell_vars_for_rc[j]])

    # (B) 無相鄰
    for (dr, dc) in [(0, 1), (1, -1), (1, 0), (1, 1)]:
        nr, nc = r + dr, c + dc
        
        # 邊界檢查會自動使用 10x15
        if not (0 <= nr < BOARD_H and 0 <= nc < BOARD_W):
            continue
            
        for pA, pB in itertools.product(range(NUM_PIECES), repeat=2):
            if pA == pB:
                continue
            
            c_var_A = get_cell_var(r, c, pA)
            c_var_B = get_cell_var(nr, nc, pB)
            clauses.append([-c_var_A, -c_var_B])

num_clauses = len(clauses)
print(f"  > 產生子句總數: {num_clauses}")

# ---------- 
# --- 階段 4: 寫入檔案
# ----------
# 檔名會自動更新為 10x15
cnf_name = f"untouchable_{BOARD_H}x{BOARD_W}_hybrid.cnf"
placements_name = f"placements_{BOARD_H}x{BOARD_W}_hybrid.txt"

print(f"階段 4: 正在寫入 CNF 檔案: {cnf_name}")
with open(cnf_name, "w") as f:
    f.write(f"p cnf {total_vars} {num_clauses}\n")
    for cl in clauses:
        f.write(" ".join(map(str, cl)) + " 0\n")

print(f"階段 4: 正在寫入 Placements 對照表: {placements_name}")
with open(placements_name, "w") as f:
    f.write("var,piece,transform,x,y,cells\n")
    for plc in placements:
        # 注意：這裡的 cells 寫入格式與您上傳的 generate917.py 不同
        # 它使用 Python 原始的 list 格式，如 '[(1, 2), (1, 3)]'
        # 我們的 show_solution.py 使用 ast.literal_eval 來解析它，所以是相容的
        f.write(f"{plc['var']},{plc['piece']},{plc['transform']},{plc['x']},{plc['y']},{plc['cells']}\n")

print("\n--- 完成 ---")
print(f"CNF 檔案: {cnf_name} ({total_vars} vars, {num_clauses} clauses)")
print(f"對照表: {placements_name}")
print(f"接下來可以用 minisat {cnf_name} solution_10x15.txt 求解")