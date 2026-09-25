#!/usr/bin/env python3
# show_9x17_modelB.py
# 讀取 SAT Solver 的解 (solution2.txt) 和
# 變數對照表 (placements.txt) 來視覺化拼圖結果。
# (版本 2: 不顯示數字，只顯示色塊)

import sys
import ast # 用於安全地解析字串形式的 list '[(1,2), (3,4)]'

# ---------- 1. 參數設定 ----------
BOARD_H = 9
BOARD_W = 17
SOLUTION_FILE = 'solution_9x17_modelB.txt'
PLACEMENTS_FILE = 'placements_9x17_hybrid.txt'

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

# ---------- 2. 讀取 solution2.txt (與前一版相同) ----------
def parse_solution(filename):
    print(f"正在讀取解答檔案: {filename}")
    true_vars = set()
    try:
        with open(filename, 'r') as f:
            all_text = "".join(f.readlines())
            if all_text.strip().startswith("SAT"):
                all_text = all_text.strip()[3:]
            words = all_text.split()
            for word in words:
                try:
                    var = int(word)
                    if var > 0:
                        true_vars.add(var)
                except ValueError:
                    continue
        
        print(f"找到 {len(true_vars)} 個為 'True' 的變數 (即被放置的拼圖)。")
        if len(true_vars) != 11:
            print(f"警告：找到的拼圖數量 ({len(true_vars)}) 不是 11 塊！")
            
        return true_vars
        
    except FileNotFoundError:
        print(f"錯誤: 解答檔案 '{filename}' 不存在。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"讀取解答檔案時發生錯誤: {e}", file=sys.stderr)
        sys.exit(1)

# ---------- 3. 讀取 placements.txt 並比對 (與前一版相同) ----------
def get_chosen_placements(filename, true_vars):
    print(f"正在讀取變數對照表: {filename}")
    chosen_placements = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(',', 5)
                    if len(parts) != 6:
                        print(f"警告: 忽略格式錯誤的行: {line}")
                        continue
                    var_id = int(parts[0])
                    if var_id in true_vars:
                        piece_index = int(parts[1])
                        cells_list = ast.literal_eval(parts[5])
                        chosen_placements.append((piece_index, cells_list))
                except (ValueError, IndexError, SyntaxError) as e:
                    print(f"警告: 解析行時出錯，已忽略: {line} (錯誤: {e})")
                        
        print(f"成功從解答中對應到 {len(chosen_placements)} 個拼圖放置方式。")
        return chosen_placements
        
    except FileNotFoundError:
        print(f"錯誤: 變數對照表 '{filename}' 不存在。", file=sys.stderr)
        print("請確認您已經執行過 generate917.py 來產生此檔案。", file=sys.stderr)
        sys.exit(1)

# ---------- 4. 建立網格並印出 (此函數已修改) ----------
def build_and_print_grid(placements, use_color=True):
    """
    建立 9x17 網格並將解答印在上面。
    """
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
    print(f"--- 9x17 拼圖解答 ({'彩色' if use_color else '純文字'}) ---")
    print("="* (BOARD_W * 2 + 1))
    
    for r in range(BOARD_H):
        line_str = ""
        for c in range(BOARD_W):
            piece_index = grid[r][c]
            
            if piece_index is None:
                # 這是空格子
                line_str += f"{EMPTY_CELL_CHAR} "
            else:
                # 這是拼圖
                
                # ******** 主要修改處 ********
                if use_color:
                    # 在彩色模式下，不顯示數字，只顯示一個空格
                    # 這樣 (display_char + " ") 就會變成 (" " + " ")
                    display_char = " "
                    color = COLORS[piece_index % len(COLORS)]
                    line_str += f"{color}{display_char} {RESET_COLOR}"
                else:
                    # 在純文字模式下，我們用 '#' 來代表拼圖
                    display_char = "#"
                    line_str += f"{display_char} "
                # ******** 修改結束 ********

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
        print("解答檔案中未找到任何為 'True' 的變數。")
        print("請確認 SAT Solver 的結果是否為 SATISFIABLE？")
        return
        
    placements = get_chosen_placements(PLACEMENTS_FILE, true_vars)
    if not placements:
        print("無法從解答中對應到任何拼圖。請檢查檔案是否正確。")
        return

    build_and_print_grid(placements, use_color=use_color)
    
    if use_color:
        print("\n(如果顏色顯示為亂碼，請嘗試使用 `python show_9x17_modelB.py --no-color` 指令執行)")
    else:
        print("\n(您可以嘗試執行 `python show_9x17_modelB.py` 來查看彩色版本)")


if __name__ == "__main__":
    main()