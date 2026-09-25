#!/usr/bin/env python3
# generate_12x12_modelA.py
# 產生 12x12 版本的 placement-level CNF (模型 A)
# 整理 repo 時由 generate_10x15_modelA.py 補上，只修改盤面大小，其餘邏輯相同
# *** 警告：此模型效率極低，產生的 CNF 巨大，求解非常緩慢 ***

import itertools
import json

# ---------- 參數：棋盤大小 ----------
BOARD_H = 12  # <<< 修改處
BOARD_W = 12  # <<< 修改處

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

# ---------- 產生所有合法 placement... (與之前相同) ----------
print("階段 1: 產生所有合法放置...")
placements = []
var_counter = 1
all_piece_transforms = [generate_transforms(p) for p in pieces]

for p_idx, transforms in enumerate(all_piece_transforms):
    for f_idx, t in enumerate(transforms):
        th = len(t); tw = len(t[0])
        # 迴圈會自動使用 12x12
        for x in range(BOARD_H - th + 1):
            for y in range(BOARD_W - tw + 1):
                cells = occupied_cells(t, x, y)
                valid = all(0 <= cx < BOARD_H and 0 <= cy < BOARD_W for (cx,cy) in cells)
                if not valid: continue
                placements.append({
                    "var": var_counter, "piece": p_idx, "transform": f_idx,
                    "x": x, "y": y, "cells": cells
                })
                var_counter += 1

num_vars = var_counter - 1
print(f"  > 找到 {len(placements)} 個合法放置, 分配變數 ID 1..{num_vars}")

# ---------- 建立索引... (與之前相同) ----------
placements_by_piece = {}
for plc in placements:
    placements_by_piece.setdefault(plc["piece"], []).append(plc)

# ---------- 產生子句 ----------
clauses = []
print("階段 2: 產生子句 (這可能會非常非常慢)...")

# --- 規則 1: 每塊至少放一次 (At-Least-One) ---
print("  > 正在產生 At-Least-One 子句...")
for p_idx in range(len(pieces)):
    plcs = placements_by_piece.get(p_idx, [])
    if not plcs:
        raise SystemExit(f"錯誤：拼圖 {p_idx} 在 12x12 棋盤上沒有任何合法放置位置！")
    clauses.append([plc["var"] for plc in plcs])

# --- 規則 2: 每塊最多放一次 (At-Most-One, Pairwise) ---
print("  > 正在產生 At-Most-One (成對) 子句 (O(N^2/P))...")
for p_idx, plcs in placements_by_piece.items():
    # itertools.combinations 會產生 O(k^2) 對
    for a, b in itertools.combinations(plcs, 2):
        clauses.append([-a["var"], -b["var"]])

# --- 規則 3: 不可相鄰/重疊 ---
print("  > 正在產生 不可相鄰/重疊 子句 (O(N^2)) - *** 這是主要的效能瓶頸 ***")
# itertools.combinations(range(len(pieces)), 2)
for p1_idx, p2_idx in itertools.combinations(range(len(pieces)), 2):
    pl1 = placements_by_piece.get(p1_idx, [])
    pl2 = placements_by_piece.get(p2_idx, [])
    # 這裡的三層迴圈導致了 O(N^2) 的複雜度
    for a in pl1:
        cells1 = set(a["cells"]) # 使用 set 加速檢查
        for b in pl2:
            cells2 = b["cells"]
            
            # 檢查重疊 (Overlap)
            if not cells1.isdisjoint(cells2): # set.isdisjoint 比 any(c in ...) 快
                clauses.append([-a["var"], -b["var"]])
                continue
                
            # 檢查相鄰 (Adjacency)
            adj = False
            # 這仍然是一個 O(S*S) 的檢查，但 S 很小
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
print(f"  > 產生子句總數: {num_clauses} (預計會非常多)")

# ---------- 寫 DIMACS CNF 與 placements 對照表 ----------
cnf_name = f"untouchable_{BOARD_H}x{BOARD_W}_simple.cnf" # 更新檔名
placements_name = f"placements_{BOARD_H}x{BOARD_W}_simple.txt" # 更新檔名

print(f"階段 3: 正在寫入 CNF 檔案: {cnf_name}")
with open(cnf_name, "w") as f:
    f.write(f"p cnf {num_vars} {num_clauses}\n")
    for cl in clauses:
        f.write(" ".join(map(str, cl)) + " 0\n")

print(f"階段 3: 正在寫入 Placements 對照表: {placements_name}")
with open(placements_name, "w") as f:
    f.write("var,piece,transform,x,y,cells\n") # 保持 CSV 格式
    for plc in placements:
        # 將 cells 列表轉換為字串 (與您上傳的版本一致)
        cells_str = str(plc['cells']) 
        f.write(f"{plc['var']},{plc['piece']},{plc['transform']},{plc['x']},{plc['y']},{cells_str}\n")


print("\n--- 完成 ---")
print(f"CNF 檔案: {cnf_name} ({num_vars} vars, {num_clauses} clauses)")
print(f"對照表: {placements_name}")
print(f"*** 再次警告：用 cadical 或 minisat 求解 {cnf_name} 可能需要極長時間 (數天或更久) ***")