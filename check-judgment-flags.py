import json
import re
import os
import shutil

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