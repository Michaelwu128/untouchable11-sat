#!/usr/bin/env python3
# generate_10x15_amo.py
#
# 10x15 版本的「模型 C」:
# 1. 混合式通道 (Hybrid Channeling)
# 2. 循序計數器 (Sequential Counter AMO)

import itertools
import json
import collections

# ---------- 參數：棋盤大小 ----------
BOARD_H = 10  # <<< 修改處
BOARD_W = 15  # <<< 修改處
NUM_PIECES = 11

# ---------- 你的 11 塊拼圖... (與之前相同) ----------
pieces_raw = [
    ["10","10","11","01","01"], ["011","010","110","010"],
    ["100","111","010","010"], ["111","010","010","010"],
    ["010","011","110","100"], ["001","011","110","100"],
    ["010","011","110","010"], ["110","010","011","001"],
    ["0001","1111","0010"], ["0010","1111","0010"],
    ["1000","1111","0001"],
]

# ---------- 輔助函式... (與之前相同) ----------
def str_rows_to_matrix(rows):
    return [[1 if c=='1' else 0 for c in row] for row in rows]
pieces = [str_rows_to_matrix(r) for r in pieces_raw]
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
        if k>0: m = rotate90(m)
        for cand in (m, flip_h(m), flip_v(m)):
            t = mat_to_tuple(cand)
            if t not in seen:
                seen.add(t)
                out.append([list(row) for row in t])
    return out
def occupied_cells(mat, x, y):
    cells = []
    h = len(mat); w = len(mat[0])
    for i in range(h):
        for j in range(w):
            if mat[i][j]: cells.append((x+i, y+j))
    return cells

# ---------- 
# --- 階段 1: 建立 "放置變數" v(p,o,x,y)
# ----------
print("階段 1: 建立 '放置變數' v(p,o,x,y)")
placements = []
placements_by_piece = collections.defaultdict(list)
placements_covering = collections.defaultdict(lambda: collections.defaultdict(list))
var_counter = 1
all_piece_transforms = [generate_transforms(p) for p in pieces]

for p_idx, transforms in enumerate(all_piece_transforms):
    for f_idx, t in enumerate(transforms):
        th = len(t); tw = len(t[0])
        # 迴圈會自動使用 10x15
        for x in range(BOARD_H - th + 1):
            for y in range(BOARD_W - tw + 1):
                
                cells = occupied_cells(t, x, y)
                valid = all(0 <= cx < BOARD_H and 0 <= cy < BOARD_W for (cx,cy) in cells)
                if not valid: continue
                
                plc = {"var": var_counter, "piece": p_idx, "transform": f_idx, "x": x, "y": y, "cells": cells}
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
num_cell_vars = BOARD_H * BOARD_W * NUM_PIECES # 10 * 15 * 11
total_vars = num_placement_vars + num_cell_vars

def get_cell_var(r, c, p):
    if not (0 <= r < BOARD_H and 0 <= c < BOARD_W and 0 <= p < NUM_PIECES):
        raise IndexError("get_cell_var 索引超出範圍")
    cell_index = (r * BOARD_W) + c # BOARD_W = 15
    offset = (cell_index * NUM_PIECES) + p
    return cell_var_start_id + offset

print(f"  > 建立 {num_cell_vars} 個格子變數, ID {cell_var_start_id}..{total_vars}")

# ---------- 
# --- 階段 3: 產生子句
# ----------
clauses = []
current_aux_var = total_vars + 1

# --- 規則 1: 每塊拼圖剛好放置一次 (使用 v 變數) ---
print("階段 3 (1/4): 產生 'Exactly-One' (放置) 子句 (使用循序計數器)...")
for p_idx in range(NUM_PIECES):
    plcs = placements_by_piece.get(p_idx, [])
    if not plcs:
        raise SystemExit(f"錯誤：拼圖 {p_idx} 在 10x15 棋盤上沒有任何合法放置位置！")
    
    # (A) At-Least-One
    clauses.append([plc["var"] for plc in plcs])
    
    # (B) At-Most-One (使用循序計數器)
    v_vars = [plc["var"] for plc in plcs]
    k = len(v_vars)
    if k <= 1:
        continue
    
    s_vars = list(range(current_aux_var, current_aux_var + k - 1))
    current_aux_var += (k - 1)
    
    clauses.append([-v_vars[0], s_vars[0]])
    clauses.append([-v_vars[-1], -s_vars[-1]])
    
    for i in range(1, k - 1):
        v_i = v_vars[i]
        s_prev = s_vars[i-1]
        s_i = s_vars[i]
        clauses.append([-v_i, s_i])
        clauses.append([-s_prev, s_i])
        clauses.append([-v_i, -s_prev])

total_vars = current_aux_var - 1
print(f"  > AMO 優化完成。總變數數量 (含輔助變數) 增加到: {total_vars}")

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
for r, c, p in itertools.product(range(BOARD_H), range(BOARD_W), range(NUM_PIECES)):
    c_var = get_cell_var(r, c, p)
    v_list = placements_covering[(r, c)].get(p, [])
    clause = [-c_var] + v_list
    clauses.append(clause)

# --- 規則 4: 衝突子句 (使用 c 變數) ---
print("階段 3 (4/4): 產生衝突子句 (格子層)...")
for r, c in itertools.product(range(BOARD_H), range(BOARD_W)):
    # (A) 無重疊
    cell_vars_for_rc = [get_cell_var(r, c, p) for p in range(NUM_PIECES)]
    for i in range(NUM_PIECES):
        for j in range(i + 1, NUM_PIECES):
            clauses.append([-cell_vars_for_rc[i], -cell_vars_for_rc[j]])
    # (B) 無相鄰
    for (dr, dc) in [(0, 1), (1, -1), (1, 0), (1, 1)]:
        nr, nc = r + dr, c + dc
        if not (0 <= nr < BOARD_H and 0 <= nc < BOARD_W): continue
        for pA, pB in itertools.product(range(NUM_PIECES), repeat=2):
            if pA == pB: continue
            c_var_A = get_cell_var(r, c, pA)
            c_var_B = get_cell_var(nr, nc, pB)
            clauses.append([-c_var_A, -c_var_B])

num_clauses = len(clauses)
print(f"  > 產生子句總數: {num_clauses}")

# ---------- 
# --- 階段 4: 寫入檔案
# ----------
cnf_name = f"untouchable_{BOARD_H}x{BOARD_W}_hybrid_amo.cnf"
placements_name = f"placements_{BOARD_H}x{BOARD_W}_hybrid_amo.txt"

print(f"階段 4: 正在寫入 CNF 檔案: {cnf_name}")
with open(cnf_name, "w") as f:
    f.write(f"p cnf {total_vars} {num_clauses}\n")
    for cl in clauses:
        f.write(" ".join(map(str, cl)) + " 0\n")

print(f"階段 4: 正在寫入 Placements 對照表: {placements_name}")
with open(placements_name, "w") as f:
    f.write("var,piece,transform,x,y,cells\n")
    for plc in placements:
        f.write(f"{plc['var']},{plc['piece']},{plc['transform']},{plc['x']},{plc['y']},{plc['cells']}\n")

print("\n--- 完成 ---")
print(f"CNF 檔案: {cnf_name} ({total_vars} vars, {num_clauses} clauses)")
print(f"對照表: {placements_name}")
print(f"接下來可以用 cadical {cnf_name} solution_10x15_amo.txt 求解")