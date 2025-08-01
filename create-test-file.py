import os
import json
import random
import shutil
from typing import List, Optional


def get_json_files(directory: str) -> List[str]:
    """
    獲取目錄中所有 JSON 檔案的路徑
    
    Args:
        directory: 目錄路徑
        
    Returns:
        JSON 檔案路徑列表
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(f"目錄不存在: {directory}")
    
    json_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            json_files.append(os.path.join(directory, filename))
    
    return json_files


def select_random_files(input_directory: str, n: int, output_directory: str, seed: Optional[int] = None) -> dict:
    """
    從輸入目錄中隨機選擇 n 個 JSON 檔案並複製到輸出目錄
    
    Args:
        input_directory: 輸入目錄路徑
        n: 要選擇的檔案數量
        output_directory: 輸出目錄路徑
        seed: 隨機種子（可選，用於重現結果）
        
    Returns:
        操作結果統計
    """
    # 設定隨機種子（如果提供）
    if seed is not None:
        random.seed(seed)
    
    # 獲取所有 JSON 檔案
    json_files = get_json_files(input_directory)
    
    if len(json_files) == 0:
        return {
            'status': 'error',
            'message': f'在目錄 {input_directory} 中沒有找到 JSON 檔案',
            'total_files': 0,
            'requested_files': n,
            'selected_files': 0,
            'copied_files': []
        }
    
    # 檢查請求的檔案數量
    if n > len(json_files):
        print(f"警告: 請求 {n} 個檔案，但只有 {len(json_files)} 個檔案可用。將複製所有檔案。")
        n = len(json_files)
    
    # 隨機選擇檔案
    selected_files = random.sample(json_files, n)
    
    # 創建輸出目錄（如果不存在）
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        print(f"創建輸出目錄: {output_directory}")
    
    # 複製檔案
    copied_files = []
    failed_files = []
    
    for file_path in selected_files:
        try:
            filename = os.path.basename(file_path)
            output_path = os.path.join(output_directory, filename)
            
            # 如果目標檔案已存在，添加編號避免覆蓋
            counter = 1
            original_output_path = output_path
            while os.path.exists(output_path):
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{counter}{ext}"
                output_path = os.path.join(output_directory, new_filename)
                counter += 1
            
            shutil.copy2(file_path, output_path)
            copied_files.append({
                'source': file_path,
                'destination': output_path,
                'filename': os.path.basename(output_path)
            })
            print(f"複製: {filename} -> {os.path.basename(output_path)}")
            
        except Exception as e:
            failed_files.append({
                'file': file_path,
                'error': str(e)
            })
            print(f"複製失敗: {filename} - {e}")
    
    # 返回結果統計
    result = {
        'status': 'success' if len(failed_files) == 0 else 'partial_success',
        'total_files': len(json_files),
        'requested_files': n,
        'selected_files': len(selected_files),
        'copied_files': copied_files,
        'failed_files': failed_files,
        'output_directory': output_directory
    }
    
    return result


def print_summary(result: dict):
    """
    打印操作結果摘要
    
    Args:
        result: select_random_files 函式的返回結果
    """
    print("\n" + "="*50)
    print("操作摘要")
    print("="*50)
    print(f"狀態: {result['status']}")
    print(f"輸入目錄中的 JSON 檔案總數: {result['total_files']}")
    print(f"請求的檔案數量: {result['requested_files']}")
    print(f"實際選擇的檔案數量: {result['selected_files']}")
    print(f"成功複製的檔案數量: {len(result['copied_files'])}")
    print(f"複製失敗的檔案數量: {len(result['failed_files'])}")
    print(f"輸出目錄: {result['output_directory']}")
    
    if result['copied_files']:
        print("\n複製的檔案:")
        for i, file_info in enumerate(result['copied_files'], 1):
            print(f"  {i}. {file_info['filename']}")
    
    if result['failed_files']:
        print("\n失敗的檔案:")
        for i, file_info in enumerate(result['failed_files'], 1):
            print(f"  {i}. {os.path.basename(file_info['file'])} - {file_info['error']}")


def main():
    """
    主函式 - 示範用法
    """
    # 寫死的路徑設定
    input_dir = "/Users/hochienhuang/JRAR/projects/Fuzzy-Regex/data/filtered_judgments_2/"
    output_dir = "./test_data"
    
    print("JSON 檔案隨機選擇工具")
    print("="*30)
    print(f"輸入目錄: {input_dir}")
    print(f"輸出目錄: {output_dir}")
    print()
    
    try:
        n = int(input("請輸入要選擇的檔案數量: ").strip())
    except ValueError:
        n = 5  # 預設值
        print(f"使用預設數量: {n}")
    
    # 詢問是否使用隨機種子
    seed_input = input("請輸入隨機種子（可選，按 Enter 跳過）: ").strip()
    seed = int(seed_input) if seed_input else None
    
    try:
        # 執行檔案選擇和複製
        result = select_random_files(input_dir, n, output_dir, seed)
        
        # 打印結果摘要
        print_summary(result)
        
    except Exception as e:
        print(f"錯誤: {e}")


# 直接使用的便捷函式
def quick_select(n: int, seed: Optional[int] = None):
    """
    便捷函式：快速選擇和複製檔案（使用固定路徑）
    
    Args:
        n: 要選擇的檔案數量
        seed: 隨機種子（可選）
    """
    input_dir = "/Users/hochienhuang/JRAR/projects/Fuzzy-Regex/data/filtered_judgments_2/"
    output_dir = "./test_data"

    result = select_random_files(input_dir, n, output_dir, seed)
    print_summary(result)
    return result


if __name__ == "__main__":
    main()
