#!/usr/bin/env python3
# show_solution.py (修正版 v3)
# - 相容 CaDiCaL / MiniSAT 的完整日誌輸出
# - 修正 UnicodeDecodeError (使用 latin-1 編碼)
# - 只解析 'v ' 開頭的解答行
# - 修正 'var' 標頭解析警告

import sys
import ast # 用於安全地解析字串形式的 list '[(1,2), (3,4)]'

# ---------- 1. 參數設定 ----------
# (請確認這些參數符合您的 10x15 檔案名稱)
BOARD_H = 10
BOARD_W = 15
SOLUTION_FILE = 'solution_10x15_modelA.txt'
PLACEMENTS_FILE = 'placements_10x15_simple.txt' # (請確認這是您產生的對照表名稱)

# 用於在終端機顯示顏色的 ANSI 代碼 (背景顏色)
COLORS = [
    '\033[41m',  # 紅色
    '\033[42m',  # 綠色
    '\033[43m',  # 黃色
    '\033[44m',  # 藍色
    '\033[45m',  # 洋紅色
    '\033[46m',  # 青色
    '\033[100m', # 亮黑色 (深灰)
    '\033[101m', # 亮紅色
    '\033[102m', # 亮綠色
    '\033[104m', # 亮藍色
    '\033[105m', # 亮洋紅色
]
RESET_COLOR = '\033[0m'  # 重設所有顏色/格式
EMPTY_CELL_CHAR = '.'   # 用於表示空格子

# ---------- 2. 讀取 solution (此函數已大幅修改) ----------
def parse_solution(filename):
    """
    讀取 SAT Solver 的輸出檔案 (相容 CaDiCaL 完整日誌)，
    並回傳所有 'True' 變數的 set。
    """
    print(f"正在讀取解答檔案: {filename}")
    true_vars = set()
    try:
        # 修正 1: 使用 'latin-1' 編碼來讀取，避免 UnicodeDecodeError
        with open(filename, 'r', encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                
                # 修正 2: 只找 'v ' (v + 空格) 開頭的行，這才是解答行
                if line.startswith('v '):
                    # 去掉 'v ' 標記
                    solution_part = line[2:]
                    words = solution_part.split()
                    for word in words:
                        try:
                            var = int(word)
                            if var > 0:
                                true_vars.add(var)
                            # (我們不在乎 < 0 或 == 0 的)
                        except ValueError:
                            # 忽略任何非數字的字 (雖然 'v ' 行中不該有)
                            continue
        
        if not true_vars:
            print("警告: 在檔案中未找到任何以 'v ' 開頭的解答行。")
            print(f"       請檢查 {filename} 內容，確認 Solver 是否回報 's SATISFIABLE'？")
        else:
            print(f"成功從 'v ' 行中解析出 {len(true_vars)} 個為 'True' 的變數。")
            
        return true_vars
        
    except FileNotFoundError:
        print(f"錯誤: 解答檔案 '{filename}' 不存在。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        # 捕捉其他可能的錯誤
        print(f"讀取解答檔案時發生錯誤: {e}", file=sys.stderr)
        sys.exit(1)

# ---------- 3. 讀取 placements.txt (此函數已小幅修改) ----------
def get_chosen_placements(filename, true_vars):
    """
    讀取 placements.txt，比對 true_vars，
    回傳一個 list，包含 (piece_index, cells_list) 的元組。
    """
    print(f"正在讀取變數對照表: {filename}")
    chosen_placements = []
    found_matches = 0
    try:
        with open(filename, 'r') as f:
            
            # 修正 3: 明確跳過第一行 (CSV 標頭)
            try:
                next(f)
            except StopIteration:
                print("錯誤: Placements 檔案是空的。")
                return []
            
            # --- 修改結束 ---
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(',', 5)
                    if len(parts) != 6:
                        continue
                        
                    var_id = int(parts[0])
                    
                    if var_id in true_vars:
                        piece_index = int(parts[1])
                        cells_list = ast.literal_eval(parts[5])
                        chosen_placements.append((piece_index, cells_list))
                        found_matches += 1
                        
                except (ValueError, IndexError, SyntaxError) as e:
                    print(f"警告: 解析行時出錯，已忽略: {line} (錯誤: {e})")
        
        if found_matches != 11:
            print(f"警告: 成功對應的拼圖數量為 {found_matches}，而不是 11！")
        else:
            print(f"成功從解答中對應到 {found_matches} 個拼圖放置方式。")
            
        return chosen_placements
        
    except FileNotFoundError:
        print(f"錯誤: 變數對照表 '{filename}' 不存在。", file=sys.stderr)
        print("請確認您已經執行過 generate...py 來產生此檔案。", file=sys.stderr)
        sys.exit(1)

# ---------- 4. 建立網格並印出 (與前一版相同) ----------
def build_and_print_grid(placements, use_color=True):
    grid = [[None for _ in range(BOARD_W)] for _ in range(BOARD_H)]
    
    for piece_index, cells_list in placements:
        for (r, c) in cells_list:
            if 0 <= r < BOARD_H and 0 <= c < BOARD_W:
                if grid[r][c] is not None:
                    print(f"嚴重錯誤: 拼圖在 ({r},{c}) 處發生重疊！", file=sys.stderr)
                grid[r][c] = piece_index
            else:
                print(f"嚴重錯誤: 座標 ({r},{c}) 超出網格範圍！", file=sys.stderr)

    print("\n" + "="* (BOARD_W * 2 + 1))
    print(f"--- {BOARD_H}x{BOARD_W} 拼圖解答 ({'彩色' if use_color else '純文字'}) ---")
    print("="* (BOARD_W * 2 + 1))
    
    for r in range(BOARD_H):
        line_str = ""
        for c in range(BOARD_W):
            piece_index = grid[r][c]
            if piece_index is None:
                line_str += f"{EMPTY_CELL_CHAR} "
            else:
                if use_color:
                    display_char = " "
                    color = COLORS[piece_index % len(COLORS)]
                    line_str += f"{color}{display_char} {RESET_COLOR}"
                else:
                    display_char = "#"
                    line_str += f"{display_char} "
        print(line_str)
    print("="* (BOARD_W * 2 + 1))

# ---------- 5. 主程式 (與前一版相同) ----------
def main():
    use_color = True
    if '--no-color' in sys.argv:
        use_color = False
        print("已停用顏色輸出。")
    
    if sys.platform == "win32":
        try:
            import os
            os.system('')
        except:
            pass 

    true_vars = parse_solution(SOLUTION_FILE)
    if not true_vars:
        print("未能在解答檔案中解析出任何變數。程式終止。")
        return
        
    placements = get_chosen_placements(PLACEMENTS_FILE, true_vars)
    if not placements:
        print("無法從解答中對應到任何拼圖。請檢查檔案是否正確。")
        return

    build_and_print_grid(placements, use_color=use_color)
    
    if use_color:
        print("\n(如果顏色顯示為亂碼，請嘗試使用 `python3 show_10x15_modelA.py --no-color` 指令執行)")
    else:
        print("\n(您可以嘗試執行 `python3 show_10x15_modelA.py` 來查看彩色版本)")


if __name__ == "__main__":
    main()