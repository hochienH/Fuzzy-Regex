import json
import re
import os
import shutil

def check_if_flag_exists(judgment_content, flags_config):
    """
    檢查判決書內容中是否存在必要的標記
    
    Args:
        judgment_content: 判決書內容字符串
        flags_config: 標記配置
    
    Returns:
        bool: 是否所有必要標記都存在
    """
    necessary_flags = flags_config['necessary_flags']
    
    # 檢查每個必要標記類別
    for flag_type, flag_list in necessary_flags.items():
        category_found = False
        
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
                category_found = True
                break
        
        # 如果該類別完全沒有匹配，返回 False
        if not category_found:
            return False
    
    # 所有必要標記都找到了
    return True

def check_missing_flags(judgment_file_path):
    """
    檢查單個判決書檔案缺少哪些必要標記
    
    Args:
        judgment_file_path: 判決書檔案的絕對路徑
    
    Returns:
        dict: 包含檢查結果的字典
        {
            'has_all_flags': bool,           # 是否包含所有必要標記
            'missing_flags': list,           # 缺少的標記類別列表
            'found_flags': dict,             # 找到的標記 {flag_type: [matched_flags]}
            'error': str or None             # 錯誤訊息（如果有的話）
        }
    """
    try:
        # 讀取標記配置
        with open('judgment_parsing_flag.json', 'r', encoding='utf-8') as f:
            flags_config = json.load(f)
        
        # 讀取判決書檔案
        with open(judgment_file_path, 'r', encoding='utf-8') as f:
            judgment_data = json.load(f)
        
        # 取得判決書內容
        judgment_content = judgment_data.get('JFULL', '')
        
        necessary_flags = flags_config['necessary_flags']
        missing_flags = []
        found_flags = {}
        
        # 檢查每個必要標記類別
        for flag_type, flag_list in necessary_flags.items():
            category_found = False
            matched_flags_in_category = []
            
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
                    category_found = True
                    matched_flags_in_category.append(flag)
            
            # 記錄結果
            if category_found:
                found_flags[flag_type] = matched_flags_in_category
            else:
                missing_flags.append(flag_type)
        
        return {
            'has_all_flags': len(missing_flags) == 0,
            'missing_flags': missing_flags,
            'found_flags': found_flags,
            'error': None
        }
        
    except FileNotFoundError:
        return {
            'has_all_flags': False,
            'missing_flags': [],
            'found_flags': {},
            'error': f"檔案不存在: {judgment_file_path}"
        }
    except json.JSONDecodeError:
        return {
            'has_all_flags': False,
            'missing_flags': [],
            'found_flags': {},
            'error': f"JSON 格式錯誤: {judgment_file_path}"
        }
    except Exception as e:
        return {
            'has_all_flags': False,
            'missing_flags': [],
            'found_flags': {},
            'error': f"處理檔案時發生錯誤: {str(e)}"
        }

def filter_judgments(input_path, output_path):
    """
    過濾判決書檔案，將符合條件的移動到輸出目錄
    
    Args:
        input_path: 輸入目錄路徑
        output_path: 輸出目錄路徑
    """
    # 讀取標記配置（只讀取一次）
    with open('judgment_parsing_flag.json', 'r', encoding='utf-8') as f:
        flags_config = json.load(f)
    
    # 創建輸出目錄（如果不存在）
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        print(f"Created output directory: {output_path}")
    
    # 取得所有 .json 檔案
    json_files = [filename for filename in os.listdir(input_path) if filename.endswith('.json')]
    total_files = len(json_files)
    moved_count = 0
    
    print(f"Found {total_files} JSON files to process...")
    
    # 處理每個檔案
    for i, filename in enumerate(json_files, 1):
        judgment_file = os.path.join(input_path, filename)
        
        try:
            # 讀取判決書 JSON 檔案
            with open(judgment_file, 'r', encoding='utf-8') as f:
                judgment_data = json.load(f)
            
            # 取得判決書內容
            judgment_content = judgment_data.get('JFULL', '')
            
            # 檢查是否符合條件
            if check_if_flag_exists(judgment_content, flags_config):
                # 移動到輸出目錄
                destination_file = os.path.join(output_path, filename)
                shutil.move(judgment_file, destination_file)
                moved_count += 1
                # 只有當檔案名稱不包含「小」字時才顯示訊息
                if '小' not in filename:
                    print(f"[{i}/{total_files}] Moved: {os.path.join(output_path, filename)}")
            else:
                # 只有當檔案名稱不包含「小」字時才顯示訊息
                if '小' not in filename:
                    print(f"[{i}/{total_files}] Skipped: {os.path.join(input_path, filename)}")

        except Exception as e:
            print(f"[{i}/{total_files}] Error processing {filename}: {e}")
    
    print(f"\nFiltering completed!")
    print(f"Total files processed: {total_files}")
    print(f"Files moved: {moved_count}")
    print(f"Files remaining in original directory: {total_files - moved_count}")

def main():
    # 設定路徑
    input_path = '/Users/hochienhuang/JRAR/projects/Fuzzy-Regex/data/filtered_judgments'
    output_path = '/Users/hochienhuang/JRAR/projects/Fuzzy-Regex/data/filtered_judgments_3'
    
    filter_judgments(input_path, output_path)

def test_single_judgment(judgment_file_path):
    """
    測試函式：檢查單個判決書的標記情況
    
    Args:
        judgment_file_path: 判決書檔案的絕對路徑
    """
    result = check_missing_flags(judgment_file_path)
    
    print(f"檢查檔案: {judgment_file_path}")
    print(f"檔案名稱: {os.path.basename(judgment_file_path)}")
    
    if result['error']:
        print(f"❌ 錯誤: {result['error']}")
        return
    
    if result['has_all_flags']:
        print("✅ 包含所有必要標記")
    else:
        print("❌ 缺少必要標記")
        print(f"   缺少的標記類別: {result['missing_flags']}")
    
    if result['found_flags']:
        print("📋 找到的標記:")
        for flag_type, flags in result['found_flags'].items():
            print(f"   {flag_type}: {flags}")
    
    print("-" * 50)

if __name__ == '__main__':
    main()
