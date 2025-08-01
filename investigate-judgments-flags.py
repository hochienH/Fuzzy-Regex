import json
import re
import os
from collections import defaultdict, Counter

def get_matched_flags(judgment_content, flags_config):
    """
    獲取判決書內容中匹配到的具體標記
    
    Args:
        judgment_content: 判決書內容字符串
        flags_config: 標記配置
    
    Returns:
        list: 匹配到的標記列表，如果所有類別都有匹配則返回匹配的標記，否則返回空列表
    """
    necessary_flags = flags_config['necessary_flags']
    matched_flags = []
    
    # 檢查每個必要標記類別
    for flag_type, flag_list in necessary_flags.items():
        category_matched_flags = []
        
        # 檢查該類別中的每個標記
        for flag in flag_list:
            # 特殊處理日期標記
            if flag == "中華民國年月日":
                pattern = r'^\s*' + r'\s*'.join(re.escape(char) for char in "中華民國") + r'.*?' + r'\s*'.join(re.escape(char) for char in "年") + r'.*?' + r'\s*'.join(re.escape(char) for char in "月") + r'.*?' + r'\s*'.join(re.escape(char) for char in "日") + r'\s*$'
            else:
                # 建立正則表達式模式：允許字符間有空白，並允許在行結束前有各種冒號
                pattern = r'^\s*' + r'\s*'.join(re.escape(char) for char in flag) + r'\s*[：:︰]?\s*$'
            
            # 使用 multiline 和 dotall 模式進行匹配
            if re.search(pattern, judgment_content, re.MULTILINE | re.DOTALL):
                category_matched_flags.append(flag)
        
        # 如果該類別完全沒有匹配，返回空列表
        if not category_matched_flags:
            return []
        
        # 添加該類別匹配到的標記到總列表
        matched_flags.extend(category_matched_flags)
    
    # 所有必要標記類別都有匹配
    return matched_flags

def check_if_flag_exists(judgment_content, flags_config):
    """
    檢查判決書內容中是否存在必要的標記
    
    Args:
        judgment_content: 判決書內容字符串
        flags_config: 標記配置
    
    Returns:
        bool: 是否所有必要標記都存在
    """
    matched_flags = get_matched_flags(judgment_content, flags_config)
    return len(matched_flags) > 0

def analyze_judgment_flags(directory_path, flags_config_path):
    """
    分析目錄中所有判決書檔案的標記匹配情況
    
    Args:
        directory_path: 包含判決書 JSON 檔案的目錄路徑
        flags_config_path: 標記配置檔案路徑
    """
    print(f"開始分析目錄: {directory_path}")
    
    # 載入標記配置
    print(f"載入標記配置檔案: {flags_config_path}")
    with open(flags_config_path, 'r', encoding='utf-8') as f:
        flags_config = json.load(f)
    
    # 儲存每個檔案匹配到的標記
    file_flags = {}
    flag_combinations = []
    
    # 遍歷目錄中的所有 JSON 檔案
    json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
    print(f"找到 {len(json_files)} 個 JSON 檔案")
    print("開始處理檔案...")
    print("-" * 50)
    
    for i, filename in enumerate(json_files, 1):
        print(f"處理檔案 {i}/{len(json_files)}: {filename}")
        filepath = os.path.join(directory_path, filename)
        
        try:
            # 讀取判決書內容
            with open(filepath, 'r', encoding='utf-8') as f:
                judgment_data = json.load(f)
                judgment_content = judgment_data.get('JFULL', '')
            
            print(f"  → 檔案大小: {len(judgment_content)} 字符")
            
            # 獲取匹配到的標記
            matched_flags = get_matched_flags(judgment_content, flags_config)
            
            if matched_flags:
                file_flags[filename] = matched_flags
                # 排序標記以便統計相同組合
                sorted_flags = sorted(matched_flags)
                flag_combinations.append(tuple(sorted_flags))
                print(f"  → 匹配到的標記: {matched_flags}")
            else:
                print(f"  → 未找到所有必要標記")
                
        except Exception as e:
            print(f"  → 處理檔案 {filename} 時發生錯誤: {e}")
            continue
    
    print("-" * 50)
    print("檔案處理完成，開始統計結果...")
    
    # 統計標記組合
    combination_counts = Counter(flag_combinations)
    
    print("\n" + "=" * 60)
    print("統計結果")
    print("=" * 60)
    
    # 第一階段：顯示標記數量統計
    print("=== 第一階段：標記數量統計 ===")
    flag_count_stats = defaultdict(int)
    for flags in file_flags.values():
        flag_count_stats[len(flags)] += 1
    
    for count, cases in sorted(flag_count_stats.items()):
        print(f"{count} 個標記：{cases} 個案件")
    
    print(f"\n總共分析了 {len(file_flags)} 個有效案件")
    
    # 第二階段：顯示標記組合統計
    print("\n=== 第二階段：標記組合統計 ===")
    for combination, count in combination_counts.most_common():
        print(f"{list(combination)}: {count} 個案件")
    
    return file_flags, combination_counts

if __name__ == "__main__":
    import sys
    
    print("判決書標記分析工具")
    print("=" * 60)
    
    if len(sys.argv) != 2:
        print("使用方式: python investigate-judgments-flags.py <判決書目錄路徑>")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    flags_config_path = "judgment_parsing_flag.json"
    
    print(f"檢查目錄路徑: {directory_path}")
    if not os.path.exists(directory_path):
        print(f"錯誤：目錄 {directory_path} 不存在")
        sys.exit(1)
    
    print(f"檢查配置檔案: {flags_config_path}")
    if not os.path.exists(flags_config_path):
        print(f"錯誤：配置檔案 {flags_config_path} 不存在")
        sys.exit(1)
    
    print("所有檢查通過，開始分析...")
    print("=" * 60)
    analyze_judgment_flags(directory_path, flags_config_path)