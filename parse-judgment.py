import json
import re
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple


class JudgmentParser:
    """
    判決書解析器 - 支援正向與逆向工程
    處理判決書的 JFULL 屬性，將其分解為結構化元件或重新組合
    """
    
    def __init__(self):
        # 寫死的目錄路徑
        self.input_dir = '../data/filtered_judgments/'
        self.output_dir = '../data/parsed_judgments/'
        
        # 支援的分段模式 - 特殊四段式模式優先處理
        self.special_four_part_pattern = ['中華民國年月日', '主文', '事實', '理由']
        
        # 一般三段式模式
        self.supported_patterns = [
            ['中華民國年月日', '主文', '事實及理由'],
            ['中華民國年月日', '主文', '事實及理由要領'],
            ['中華民國年月日', '主文', '理由要領'],
            ['中華民國年月日', '主文', '理由'],
            ['中華民國年月日', '主文', '判決事實及理由要領'],
            ['中華民國年月日', '主文', '訴訟標的及理由要領'],
            ['中華民國年月日', '主文', '爭執事項及理由要領'],
            ['中華民國年月日', '主文', '事實'],
            ['中華民國年月日', '主文', '事實與理由']
        ]
    
    def _create_pattern(self, flag: str) -> str:
        """
        為指定的 flag 創建正則表達式模式
        """
        if flag == "中華民國年月日":
            pattern = r'^\s*' + r'\s*'.join(re.escape(char) for char in "中華民國") + r'.*?' + r'\s*'.join(re.escape(char) for char in "年") + r'.*?' + r'\s*'.join(re.escape(char) for char in "月") + r'.*?' + r'\s*'.join(re.escape(char) for char in "日") + r'\s*$'
        else:
            # 建立正則表達式模式：允許字符間有空白，並允許在行結束前有各種冒號
            pattern = r'^\s*' + r'\s*'.join(re.escape(char) for char in flag) + r'\s*[：:︰]?\s*$'
        return pattern
    
    def _find_pattern_positions(self, lines: List[str], pattern_flags: List[str]) -> Dict[str, int]:
        """
        在文本行中找到各個標記的位置
        """
        positions = {}
        
        for flag in pattern_flags:
            pattern = self._create_pattern(flag)
            
            for i, line in enumerate(lines):
                if re.match(pattern, line.strip()):
                    positions[flag] = i
                    break
        
        return positions
    
    def _is_parse_result_valid(self, parsed_result: Dict[str, str]) -> bool:
        """
        檢查解析結果是否有效
        
        Args:
            parsed_result: 解析結果字典
            
        Returns:
            如果解析結果有效則返回 True，否則返回 False
        """
        # 如果有錯誤或沒有找到模式，視為無效
        if 'error' in parsed_result or not parsed_result.get('pattern'):
            return False
        
        pattern = parsed_result.get('pattern')
        
        # 檢查主要部分是否為空
        main_content = parsed_result.get('Main', '').strip()
        if not main_content:
            return False
        
        # 根據模式檢查相應的部分
        if pattern == self.special_four_part_pattern:
            # 四段式：檢查事實和理由是否為空
            fact_content = parsed_result.get('Fact', '').strip()
            reason_content = parsed_result.get('Reason', '').strip()
            if not fact_content or not reason_content:
                return False
        else:
            # 三段式：檢查事實及理由是否為空
            fact_reason = parsed_result.get('Fact and Reason', '').strip()
            if not fact_reason:
                return False
        
        return True
    
    def parse_judgment(self, jfull_text: str) -> Dict[str, str]:
        """
        正向工程：將 JFULL 文本解析為結構化部分
        
        Args:
            jfull_text: 原始判決書全文
            
        Returns:
            Dict 包含 'Pre-Information', 'Main', 'Fact and Reason', 'Post-Information', 'pattern'
        """
        if not jfull_text or not isinstance(jfull_text, str):
            return {
                'Pre-Information': '',
                'Main': '',
                'Fact and Reason': '',
                'Post-Information': '',
                'pattern': None,
                'error': 'Invalid input text'
            }
        
        lines = jfull_text.split('\n')
        
        # 先檢查特殊的四段式模式
        four_part_positions = self._find_pattern_positions(lines, self.special_four_part_pattern)
        
        if all(flag in four_part_positions for flag in self.special_four_part_pattern):
            main_pos = four_part_positions['主文']
            fact_pos = four_part_positions['事實']
            reason_pos = four_part_positions['理由']
            date_pos = four_part_positions['中華民國年月日']
            
            # 確保位置順序正確：主文 → 事實 → 理由 → 中華民國年月日
            if main_pos < fact_pos < reason_pos < date_pos:
                # 提取各部分內容
                pre_info = '\n'.join(lines[:main_pos]).strip()
                main_content = '\n'.join(lines[main_pos+1:fact_pos]).strip()
                fact_content = '\n'.join(lines[fact_pos+1:reason_pos]).strip()
                reason_content = '\n'.join(lines[reason_pos+1:date_pos]).strip()
                post_info = '\n'.join(lines[date_pos+1:]).strip()
                
                return {
                    'Pre-Information': pre_info,
                    'Main': main_content,
                    'Fact': fact_content,
                    'Reason': reason_content,
                    'Post-Information': post_info,
                    'pattern': self.special_four_part_pattern
                }
        
        # 嘗試每個支援的三段式模式
        for pattern_flags in self.supported_patterns:
            positions = self._find_pattern_positions(lines, pattern_flags)
            
            # 檢查是否找到所有必要的標記
            if all(flag in positions for flag in pattern_flags):
                main_pos = positions['主文']
                fact_reason_flag_pos = positions[pattern_flags[2]]  # list[2] 如 '事實及理由'
                date_pos = positions['中華民國年月日']
                
                # 確保位置順序正確：主文 → list[2] → 中華民國年月日
                if main_pos < fact_reason_flag_pos < date_pos:
                    # 提取各部分內容
                    pre_info = '\n'.join(lines[:main_pos]).strip()
                    main_content = '\n'.join(lines[main_pos+1:fact_reason_flag_pos]).strip()
                    fact_reason = '\n'.join(lines[fact_reason_flag_pos+1:date_pos]).strip()
                    post_info = '\n'.join(lines[date_pos+1:]).strip()
                    
                    return {
                        'Pre-Information': pre_info,
                        'Main': main_content,
                        'Fact and Reason': fact_reason,
                        'Post-Information': post_info,
                        'pattern': pattern_flags
                    }
        
        # 如果沒有找到匹配的模式
        return {
            'Pre-Information': '',
            'Main': '',
            'Fact and Reason': '',
            'Post-Information': jfull_text,
            'pattern': None,
            'error': 'No matching pattern found'
        }
    
    def reconstruct_judgment(self, components: Dict[str, str]) -> str:
        """
        逆向工程：從結構化部分重建 JFULL 文本
        
        Args:
            components: 包含結構化部分的字典
            
        Returns:
            重建的 JFULL 文本
        """
        if not isinstance(components, dict):
            return ""
        
        pattern = components.get('pattern')
        if not pattern:
            return ""
        
        pre_info = components.get('Pre-Information', '').strip()
        main_content = components.get('Main', '').strip()
        post_info = components.get('Post-Information', '').strip()
        
        # 重建文本
        parts = []
        
        if pre_info:
            parts.append(pre_info)
        
        # 檢查是否為四段式模式
        if pattern == self.special_four_part_pattern:
            # 四段式：主文 → 事實 → 理由 → 中華民國年月日
            fact_content = components.get('Fact', '').strip()
            reason_content = components.get('Reason', '').strip()
            
            # 添加主文標記
            parts.append(pattern[1])  # '主文'
            
            if main_content:
                parts.append(main_content)
            
            # 添加事實標記
            parts.append(pattern[2])  # '事實'
            
            if fact_content:
                parts.append(fact_content)
            
            # 添加理由標記
            parts.append(pattern[3])  # '理由'
            
            if reason_content:
                parts.append(reason_content)
            
            # 添加日期標記
            parts.append(pattern[0])  # '中華民國年月日'
            
        elif len(pattern) == 3:
            # 三段式：主文 → list[2] → 中華民國年月日
            fact_reason = components.get('Fact and Reason', '').strip()
            
            # 添加主文標記
            parts.append(pattern[1])  # '主文'
            
            if main_content:
                parts.append(main_content)
            
            # 添加事實理由標記
            parts.append(pattern[2])  # 如 '事實及理由'
            
            if fact_reason:
                parts.append(fact_reason)
            
            # 添加日期標記
            parts.append(pattern[0])  # '中華民國年月日'
        
        if post_info:
            parts.append(post_info)
        
        return '\n'.join(parts)
    
    def process_json_file(self, file_path: str, output_path: str, delete_original: bool = True) -> bool:
        """
        處理單個 JSON 檔案，解析其中的 JFULL 屬性並替換為 parsed_judgment
        
        Args:
            file_path: 輸入 JSON 檔案路徑
            output_path: 輸出檔案路徑
            delete_original: 是否刪除原檔案
            
        Returns:
            處理是否成功
        """
        try:
            # 確保輸出目錄存在
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # 處理 JSON 陣列
                for item in data:
                    if isinstance(item, dict) and 'JFULL' in item:
                        parsed = self.parse_judgment(item['JFULL'])
                        
                        # 檢查解析結果是否有效（任何主要部分為空則視為失敗）
                        if self._is_parse_result_valid(parsed):
                            # 移除原本的 JFULL，替換為 parsed_judgment
                            del item['JFULL']
                            item['parsed_judgment'] = parsed
                        else:
                            print(f"解析結果無效，跳過處理: {file_path}")
                            return False
            
            elif isinstance(data, dict) and 'JFULL' in data:
                # 處理單一 JSON 物件
                parsed = self.parse_judgment(data['JFULL'])
                
                # 檢查解析結果是否有效
                if self._is_parse_result_valid(parsed):
                    # 移除原本的 JFULL，替換為 parsed_judgment
                    del data['JFULL']
                    data['parsed_judgment'] = parsed
                else:
                    print(f"解析結果無效，跳過處理: {file_path}")
                    return False
            
            # 儲存結果到輸出路徑
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 驗證輸出檔案是否成功創建
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # 如果成功處理且需要刪除原檔案
                if delete_original:
                    os.remove(file_path)
                    print(f"已刪除原檔案: {file_path}")
                return True
            else:
                print(f"輸出檔案創建失敗或為空: {output_path}")
                return False
            
        except Exception as e:
            print(f"處理檔案 {file_path} 時發生錯誤: {e}")
            return False
    
    def _process_file_batch(self, file_batch: List[str], thread_id: int) -> Dict[str, int]:
        """
        處理一批檔案（單一執行緒）
        
        Args:
            file_batch: 要處理的檔案列表
            thread_id: 執行緒 ID
            
        Returns:
            處理統計結果
        """
        stats = {
            'processed_files': 0,
            'failed_files': 0
        }
        
        print(f"執行緒 {thread_id}: 開始處理 {len(file_batch)} 個檔案")
        
        for filename in file_batch:
            input_path = os.path.join(self.input_dir, filename)
            
            # 生成新的檔名：{原檔名}_parsed.json
            name_without_ext = os.path.splitext(filename)[0]
            new_filename = f"{name_without_ext}_parsed.json"
            output_path = os.path.join(self.output_dir, new_filename)
            
            if self.process_json_file(input_path, output_path, delete_original=True):
                stats['processed_files'] += 1
                print(f"執行緒 {thread_id}: 成功處理 {filename} -> {new_filename}")
            else:
                stats['failed_files'] += 1
                print(f"執行緒 {thread_id}: 處理失敗 {filename}")
        
        print(f"執行緒 {thread_id}: 完成處理，成功 {stats['processed_files']} 個，失敗 {stats['failed_files']} 個")
        return stats

    def process_directory_multithreaded(self, max_threads: int = 8) -> Dict[str, int]:
        """
        使用多執行緒處理目錄中的所有 JSON 檔案
        
        Args:
            max_threads: 最大執行緒數量
            
        Returns:
            處理統計結果
        """
        if not os.path.exists(self.input_dir):
            raise FileNotFoundError(f"目錄不存在: {self.input_dir}")
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # 收集所有 JSON 檔案
        json_files = [f for f in os.listdir(self.input_dir) if f.endswith('.json')]
        total_files = len(json_files)
        
        if total_files == 0:
            print("沒有找到 JSON 檔案")
            return {
                'total_files': 0,
                'processed_files': 0,
                'failed_files': 0
            }
        
        print(f"找到 {total_files} 個 JSON 檔案，將使用 {max_threads} 個執行緒處理")
        
        # 將檔案平均分配給各個執行緒
        files_per_thread = total_files // max_threads
        remainder = total_files % max_threads
        
        file_batches = []
        start_idx = 0
        
        for i in range(max_threads):
            # 如果有餘數，前幾個執行緒多分配一個檔案
            batch_size = files_per_thread + (1 if i < remainder else 0)
            if batch_size > 0:
                batch = json_files[start_idx:start_idx + batch_size]
                file_batches.append(batch)
                start_idx += batch_size
        
        # 使用 ThreadPoolExecutor 執行多執行緒處理
        total_stats = {
            'total_files': total_files,
            'processed_files': 0,
            'failed_files': 0
        }
        
        with ThreadPoolExecutor(max_workers=len(file_batches)) as executor:
            # 提交所有任務
            future_to_thread = {
                executor.submit(self._process_file_batch, batch, i): i 
                for i, batch in enumerate(file_batches)
            }
            
            # 收集結果
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    result = future.result()
                    total_stats['processed_files'] += result['processed_files']
                    total_stats['failed_files'] += result['failed_files']
                except Exception as exc:
                    print(f'執行緒 {thread_id} 產生異常: {exc}')
                    # 假設該執行緒的所有檔案都失敗
                    total_stats['failed_files'] += len(file_batches[thread_id])
        
        return total_stats
    def process_directory(self, dir_path: str = None, output_dir: str = None) -> Dict[str, int]:
        """
        處理目錄中的所有 JSON 檔案（單執行緒版本，保持向後相容）
        
        Args:
            dir_path: 輸入目錄路徑（可選，使用預設路徑）
            output_dir: 輸出目錄路徑（可選，使用預設路徑）
            
        Returns:
            處理統計結果
        """
        # 如果沒有指定路徑，使用預設路徑
        input_path = dir_path if dir_path else self.input_dir
        output_path = output_dir if output_dir else self.output_dir
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"目錄不存在: {input_path}")
        
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0
        }
        
        # 處理所有 JSON 檔案
        for filename in os.listdir(input_path):
            if filename.endswith('.json'):
                stats['total_files'] += 1
                
                input_file_path = os.path.join(input_path, filename)
                
                # 生成新的檔名：{原檔名}_parsed.json
                name_without_ext = os.path.splitext(filename)[0]
                new_filename = f"{name_without_ext}_parsed.json"
                output_file_path = os.path.join(output_path, new_filename)
                
                if self.process_json_file(input_file_path, output_file_path, delete_original=True):
                    stats['processed_files'] += 1
                    print(f"成功處理: {filename} -> {new_filename}")
                else:
                    stats['failed_files'] += 1
                    print(f"處理失敗: {filename}")
        
        return stats


def main():
    """
    主函式 - 示範用法
    """
    parser = JudgmentParser()
    
    print("=== 多執行緒目錄處理 ===")
    print(f"輸入目錄: {parser.input_dir}")
    print(f"輸出目錄: {parser.output_dir}")
    
    try:
        # 使用多執行緒處理（預設 4 個執行緒）
        stats = parser.process_directory_multithreaded(max_threads=16)
        
        print(f"\n=== 處理完成 ===")
        print(f"總檔案數: {stats['total_files']}")
        print(f"成功處理: {stats['processed_files']}")
        print(f"處理失敗: {stats['failed_files']}")
        print(f"成功率: {stats['processed_files']/stats['total_files']*100:.1f}%" if stats['total_files'] > 0 else "無檔案")
        
        if stats['processed_files'] > 0:
            print(f"\n所有原始檔案已被刪除，處理結果保存在 {parser.output_dir}")
            
    except FileNotFoundError as e:
        print(f"錯誤: {e}")
    except Exception as e:
        print(f"處理過程中發生錯誤: {e}")
    
    print("\n=== 其他使用方式 ===")
    print("# 使用單執行緒處理:")
    print("stats = parser.process_directory()")
    print("# 使用多執行緒處理:")
    print("stats = parser.process_directory_multithreaded(max_threads=8)")
    print("# 自訂執行緒數量（建議根據 CPU 核心數調整）")


if __name__ == "__main__":
    main()
