import json
import re
import os
import random
import shutil

def check_if_flag_exists(judgment):
    """
    檢查判決書中是否存在必要的標記
    
    Args:
        judgment: 判決書的路徑（.json 檔案）
    
    Returns:
        tuple: (bool, str, int, dict) - (是否所有必要標記都存在, 缺少的標記類型, 總匹配flag數, 詳細匹配結果)
    """
    # 讀取 judgment_parsing_flag.json
    with open('judgment_parsing_flag.json', 'r', encoding='utf-8') as f:
        flags_config = json.load(f)
    
    # 讀取判決書 JSON 檔案
    with open(judgment, 'r', encoding='utf-8') as f:
        judgment_data = json.load(f)
    
    # 假設判決書內容在 'JFULL' 欄位中
    judgment_content = judgment_data.get('JFULL', '')
    
    # 取得必要標記
    necessary_flags = flags_config['necessary_flags']
    
    # 記錄詳細匹配結果
    detailed_matches = {}
    total_matched_flags = 0
    
    # 檢查每個必要標記類別
    for flag_type, flag_list in necessary_flags.items():
        matched_flags_in_category = []
        
        # 檢查該類別中的每個標記
        for flag in flag_list:
            # 特殊處理日期標記
            if flag == "中華民國年月日":
                pattern = r'^\s*' + r'\s*'.join(re.escape(char) for char in "中華民國") + r'.*?' + r'\s*'.join(re.escape(char) for char in "年") + r'.*?' + r'\s*'.join(re.escape(char) for char in "月") + r'.*?' + r'\s*'.join(re.escape(char) for char in "日") + r'\s*$'
            else:
                # 建立正則表達式模式：允許字符間有空白，並強制執行開頭和結尾的空白匹配
                pattern = r'^\s*' + r'\s*'.join(re.escape(char) for char in flag) + r'\s*$'
            
            # 使用 multiline 和 dotall 模式進行匹配
            if re.search(pattern, judgment_content, re.MULTILINE | re.DOTALL):
                matched_flags_in_category.append(flag)
        
        # 記錄該類別的匹配結果
        detailed_matches[flag_type] = matched_flags_in_category
        category_match_count = len(matched_flags_in_category)
        total_matched_flags += category_match_count
        
        # 如果該類別完全沒有匹配，返回錯誤
        if category_match_count == 0:
            return False, flag_type, total_matched_flags, detailed_matches
    
    # 所有必要標記都找到了
    return True, "", total_matched_flags, detailed_matches

def main():
    # judgment in ../data/filtered_judgments
    judgment_path = '/Users/hochienhuang/JRAR/projects/Fuzzy-Regex/data/filtered_judgments'
    output_path = '/Users/hochienhuang/JRAR/projects/Fuzzy-Regex/data/filtered_judgments_2'
    
    # 創建輸出目錄（如果不存在）
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Created output directory: {output_path}")
    
    # 取得所有 .json 檔案
    json_files = [filename for filename in os.listdir(judgment_path) if filename.endswith('.json')]
    
    # 統計變數
    total_files = len(json_files)
    successful_files = 0
    moved_files = 0
    flag_count_stats = {}  # 統計每種flag數量的檔案數
    
    # 處理每個檔案
    for i, filename in enumerate(json_files):
        judgment_file = os.path.join(judgment_path, filename)
        print(f"Processing file {i+1}/{total_files}: {judgment_file}")
        has_flags, missing_flag, total_flag_count, detailed_matches = check_if_flag_exists(judgment_file)
        
        # 統計總flag數量
        if total_flag_count in flag_count_stats:
            flag_count_stats[total_flag_count] += 1
        else:
            flag_count_stats[total_flag_count] = 1
            
        if not has_flags:
            # 如果缺少任何必要標記，保留在原目錄
            print(f"Missing {missing_flag} in {judgment_file} - Keeping in original directory")
            print(f"  Total matched flags: {total_flag_count}")
            print(f"  Detailed matches: {detailed_matches}")
        else:
            # 如果所有必要標記都找到，移動到新目錄
            destination_file = os.path.join(output_path, filename)
            shutil.move(judgment_file, destination_file)
            print(f"Necessary flags found in {judgment_file} - Moved to {destination_file}")
            print(f"  Total matched flags: {total_flag_count}")
            print(f"  Detailed matches: {detailed_matches}")
            successful_files += 1
            moved_files += 1
    
    # 顯示統計結果
    remaining_files = total_files - moved_files
    if moved_files > 0:
        success_rate = (successful_files / total_files) * 100
        print(f"\n=== 統計結果 ===")
        print(f"總檔案數: {total_files}")
        print(f"移動檔案數 (成功匹配): {moved_files}")
        print(f"剩餘檔案數 (保留在原目錄): {remaining_files}")
        print(f"成功檔案數: {successful_files}")
        print(f"成功率: {success_rate:.2f}%")
        
        print(f"\n=== Flag 數量統計 ===")
        for flag_count in sorted(flag_count_stats.keys()):
            file_count = flag_count_stats[flag_count]
            percentage = (file_count / total_files) * 100
            print(f"{flag_count} 個 flag: {file_count} 個檔案 ({percentage:.2f}%)")
    else:
        print(f"\n=== 統計結果 ===")
        print(f"總檔案數: {total_files}")
        print(f"沒有檔案符合條件被移動")
        
        print(f"\n=== Flag 數量統計 ===")
        for flag_count in sorted(flag_count_stats.keys()):
            file_count = flag_count_stats[flag_count]
            percentage = (file_count / total_files) * 100
            print(f"{flag_count} 個 flag: {file_count} 個檔案 ({percentage:.2f}%)")

if __name__ == '__main__':
    main()
