import json
import re
import os
from typing import Dict, List, Optional, Tuple


class JudgmentParser:
    """
    判決書解析器 - 支援正向與逆向工程
    處理判決書的 JFULL 屬性，將其分解為結構化元件或重新組合
    """
    
    def __init__(self):
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
    
    def process_json_file(self, file_path: str, output_path: str) -> bool:
        """
        處理單個 JSON 檔案，解析其中的 JFULL 屬性並替換為 parsed_judgment
        
        Args:
            file_path: 輸入 JSON 檔案路徑
            output_path: 輸出檔案路徑
            
        Returns:
            處理是否成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # 處理 JSON 陣列
                for item in data:
                    if isinstance(item, dict) and 'JFULL' in item:
                        parsed = self.parse_judgment(item['JFULL'])
                        # 移除原本的 JFULL，替換為 parsed_judgment
                        del item['JFULL']
                        item['parsed_judgment'] = parsed
            
            elif isinstance(data, dict) and 'JFULL' in data:
                # 處理單一 JSON 物件
                parsed = self.parse_judgment(data['JFULL'])
                # 移除原本的 JFULL，替換為 parsed_judgment
                del data['JFULL']
                data['parsed_judgment'] = parsed
            
            # 儲存結果到輸出路徑
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"處理檔案 {file_path} 時發生錯誤: {e}")
            return False
    
    def process_directory(self, dir_path: str, output_dir: str) -> Dict[str, int]:
        """
        處理目錄中的所有 JSON 檔案
        
        Args:
            dir_path: 輸入目錄路徑
            output_dir: 輸出目錄路徑
            
        Returns:
            處理統計結果
        """
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"目錄不存在: {dir_path}")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0
        }
        
        # 處理所有 JSON 檔案
        for filename in os.listdir(dir_path):
            if filename.endswith('.json'):
                stats['total_files'] += 1
                
                input_path = os.path.join(dir_path, filename)
                
                # 生成新的檔名：{原檔名}_parsed.json
                name_without_ext = os.path.splitext(filename)[0]
                new_filename = f"{name_without_ext}_parsed.json"
                output_path = os.path.join(output_dir, new_filename)
                
                if self.process_json_file(input_path, output_path):
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
    
    # 示範四段式模式
    four_part_sample = """臺灣臺中地方法院民事判決
右當事人間請求清償借款事件，本院判決如左：
    主文
被告應給付原告新台幣壹拾貳萬捌仟玖佰陸拾玖元。
訴訟費用由被告負擔。
    事實
一、原告主張：訴外人即債務人駱慧禎於民國八十七年六月八日，邀同被告為連帶保證人...
    理由
二、原告主張之事實，業據原告提出與所述相符之借據及授信約定書各一紙為證...
三、據上論結，本件原告之訴為有理由，依民事訴訟法第四百三十六條第二項...
中　  　華　  　民　　　國　    九十　　年　　　七  　　月　  三十一   日
臺灣臺中地方法院臺中簡易庭
法　官  曾  佩  琦"""
    
    print("=== 四段式模式測試 ===")
    parsed_four = parser.parse_judgment(four_part_sample)
    for key, value in parsed_four.items():
        print(f"{key}: {value}")
    
    print("\n=== 四段式逆向工程 ===")
    reconstructed_four = parser.reconstruct_judgment(parsed_four)
    print("重建的文本:")
    print(reconstructed_four)
    
    # 示範三段式模式  
    three_part_sample = """臺灣臺中地方法院民事判決
右當事人間請求清償借款事件，本院判決如左：
    主文
被告應給付原告新台幣壹拾貳萬捌仟玖佰陸拾玖元。
訴訟費用由被告負擔。
    事實及理由
一、原告主張：訴外人即債務人駱慧禎於民國八十七年六月八日，邀同被告為連帶保證人...
二、原告主張之事實，業據原告提出與所述相符之借據及授信約定書各一紙為證...
三、據上論結，本件原告之訴為有理由，依民事訴訟法第四百三十六條第二項...
中　  　華　  　民　　　國　    九十　　年　　　七  　　月　  三十一   日
臺灣臺中地方法院臺中簡易庭
法　官  曾  佩  琦"""
    
    print("\n=== 三段式模式測試 ===")
    parsed_three = parser.parse_judgment(three_part_sample)
    for key, value in parsed_three.items():
        print(f"{key}: {value}")
    
    print("\n=== 三段式逆向工程 ===")
    reconstructed_three = parser.reconstruct_judgment(parsed_three)
    print("重建的文本:")
    print(reconstructed_three)
    
    print("\n=== 目錄處理示範 ===")
    print("使用方式:")
    print("parser = JudgmentParser()")
    print("stats = parser.process_directory('/path/to/input/dir', '/path/to/output/dir')")
    print("print(f'處理了 {stats[\"processed_files\"]} / {stats[\"total_files\"]} 個檔案')")


if __name__ == "__main__":
    main()
