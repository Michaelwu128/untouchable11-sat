#!/usr/bin/env python3
# generate_cnf_hybrid.py
# 產生 9x17 版本的 "混合式" CNF，效能更高。
# 它使用兩種變數：
# 1. 放置變數 v(p,o,x,y) [ID: 1 ... N]
# 2. 格子變數 c(r,c,p)   [ID: N+1 ... M]
# 並在兩者之間建立 "通道" (Channeling) 子句。

import itertools
import json
import collections

# ---------- 參數：棋盤大小 ----------
BOARD_H = 9
BOARD_W = 17
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
                
                # 填入輔助索引
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
num_cell_vars = BOARD_H * BOARD_W * NUM_PIECES
total_vars = num_placement_vars + num_cell_vars

def get_cell_var(r, c, p):
    """將 (r,c,p) 座標映射到一個全域唯一的變數 ID"""
    if not (0 <= r < BOARD_H and 0 <= c < BOARD_W and 0 <= p < NUM_PIECES):
        raise IndexError("get_cell_var 索引超出範圍")
    # (r,c) pair -> 0.. (BOARD_H*BOARD_W - 1)
    # (p) piece -> 0.. (NUM_PIECES - 1)
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
        raise SystemExit(f"錯誤：拼圖 {p_idx} 沒有任何合法放置位置！")
    
    # At-Least-One
    clauses.append([plc["var"] for plc in plcs])
    
    # At-Most-One (Pairwise)
    for a, b in itertools.combinations(plcs, 2):
        clauses.append([-a["var"], -b["var"]])

# --- 規則 2: 通道子句 (v -> c) ---
# 意義: 如果我選擇了放置 v，那麼 v 所佔據的所有格子 (r,c)
#      都必須標記為被拼圖 p 佔據 (即 c(r,c,p) 為真)
# 形式: (-v OR c(r1,c1,p)) AND (-v OR c(r2,c2,p)) ...
print("階段 3 (2/4): 產生通道子句 (v -> c)...")
for plc in placements:
    v_var = plc["var"]
    p_idx = plc["piece"]
    for (r, c) in plc["cells"]:
        c_var = get_cell_var(r, c, p_idx)
        clauses.append([-v_var, c_var]) # (-v) OR (c)  <=>  v => c

# --- 規則 3: 通道子句 (c -> v) ---
# 意義: 如果格子 (r,c) 被拼圖 p 佔據了 (c(r,c,p) 為真)，
#      那麼 *必定* 是某一個能覆蓋 (r,c) 的放置 v 被選擇了。
# 形式: (-c(r,c,p) OR v1 OR v2 OR ...)
print("階段 3 (3/4): 產生通道子句 (c -> v)...")
for r, c, p in itertools.product(range(BOARD_H), range(BOARD_W), range(NUM_PIECES)):
    c_var = get_cell_var(r, c, p)
    # 從預先建立的索引中找出所有能覆蓋 (r,c) 的 p 拼圖的放置
    v_list = placements_covering[(r, c)].get(p, [])
    
    # v_list 可能為空 (例如拼圖p永遠無法蓋到(r,c))
    # 在此情況下，子句為 [-c_var]，意思是 c(r,c,p) 永遠為假，這是正確的。
    clause = [-c_var] + v_list
    clauses.append(clause)

# --- 規則 4: 衝突子句 (使用 c 變數) ---
# 意義: 這是問題的核心規則，現在在 c 變數上實現，效率高得多。
print("階段 3 (4/4): 產生衝突子句 (格子層)...")

for r, c in itertools.product(range(BOARD_H), range(BOARD_W)):
    
    # (A) 無重疊: 一個格子 (r,c) 最多只能被 1 塊拼圖佔據。
    # 形式: AtMostOne( c(r,c,p0), c(r,c,p1), ... )
    cell_vars_for_rc = [get_cell_var(r, c, p) for p in range(NUM_PIECES)]
    for i in range(NUM_PIECES):
        for j in range(i + 1, NUM_PIECES):
            # (-c(r,c,pi) OR -c(r,c,pj))
            clauses.append([-cell_vars_for_rc[i], -cell_vars_for_rc[j]])

    # (B) 無相鄰: (r,c) 上的拼圖 pA 不能與其 "鄰居" (nr,nc) 上的
    #      拼圖 pB 相鄰 (pA != pB)。
    # 
    # 為了避免重複檢查 (例如 (1,1)v(1,2) 和 (1,2)v(1,1))，
    # 我們只檢查 4 個方向的鄰居：
    # (r, c+1) -> 右
    # (r+1, c-1) -> 左下
    # (r+1, c) -> 下
    # (r+1, c+1) -> 右下
    for (dr, dc) in [(0, 1), (1, -1), (1, 0), (1, 1)]:
        nr, nc = r + dr, c + dc
        
        # 檢查鄰居是否在邊界內
        if not (0 <= nr < BOARD_H and 0 <= nc < BOARD_W):
            continue
            
        # 對於每一對不同的拼圖 (pA, pB)
        for pA, pB in itertools.product(range(NUM_PIECES), repeat=2):
            if pA == pB:
                # 拼圖可以和自己相鄰
                continue
            
            # 取得兩個格子變數
            c_var_A = get_cell_var(r, c, pA)
            c_var_B = get_cell_var(nr, nc, pB)
            
            # 規則: cA 和 cB 不能同時為真
            # 形式: (-cA OR -cB)
            clauses.append([-c_var_A, -c_var_B])

num_clauses = len(clauses)
print(f"  > 產生子句總數: {num_clauses}")

# ---------- 
# --- 階段 4: 寫入檔案
# ----------
cnf_name = f"untouchable_{BOARD_H}x{BOARD_W}_hybrid.cnf"
placements_name = f"placements_{BOARD_H}x{BOARD_W}_hybrid.txt"

print(f"階段 4: 正在寫入 CNF 檔案: {cnf_name}")
with open(cnf_name, "w") as f:
    f.write(f"p cnf {total_vars} {num_clauses}\n")
    for cl in clauses:
        f.write(" ".join(map(str, cl)) + " 0\n")

print(f"階段 4: 正在寫入 Placements 對照表: {placements_name}")
with open(placements_name, "w") as f:
    # 寫入 CSV 標頭
    f.write("var,piece,transform,x,y,cells\n")
    # 只寫入 "放置變數"，因為這才是我們解讀答案所需的
    for plc in placements:
        f.write(f"{plc['var']},{plc['piece']},{plc['transform']},{plc['x']},{plc['y']},{plc['cells']}\n")

print("\n--- 完成 ---")
print(f"CNF 檔案: {cnf_name} ({total_vars} vars, {num_clauses} clauses)")
print(f"對照表: {placements_name}")
print(f"接下來可以用 minisat {cnf_name} solution.txt 求解")
print("求解後，可使用 'show_solution.py' 並將 PLACEMENTS_FILE 變數")
print(f"指向 '{placements_name}' 來視覺化解答。")