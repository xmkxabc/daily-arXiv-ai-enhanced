import os
import json
import re
from datetime import datetime

# --- 配置区 ---
DATA_DIR = "data" 
OUTPUT_DIR = "docs" 
DATABASE_FILENAME = os.path.join(OUTPUT_DIR, "database.json")

def get_enhanced_files(directory):
    """扫描data目录，找到所有AI增强后的jsonl文件。"""
    all_files = []
    for filename in os.listdir(directory):
        if re.match(r"\d{4}-\d{2}-\d{2}_AI_enhanced_.*\.jsonl$", filename):
            all_files.append(os.path.join(directory, filename))
    all_files.sort(reverse=True)
    return all_files

def main():
    """主函数，合并所有jsonl文件到一个单一的数据库文件。"""
    print("开始构建数据库...")
    
    enhanced_files = get_enhanced_files(DATA_DIR)
    if not enhanced_files:
        print("在data目录中未找到任何AI增强后的文件。")
        return

    all_papers = []
    for filepath in enhanced_files:
        print(f"正在处理文件: {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        paper_data = json.loads(line)
                        date_str = os.path.basename(filepath).split('_')[0]
                        paper_data['date'] = date_str
                        
                        # **核心URL修正逻辑**
                        # 优先使用爬虫提供的'url'字段，因为它可能包含版本号(v1, v2等)
                        # 如果'url'字段不存在或为空，则尝试用'id'字段来构建
                        if 'url' not in paper_data or not paper_data['url']:
                            paper_id = paper_data.get('id', '')
                            if paper_id:
                                paper_data['url'] = f"https://arxiv.org/abs/{paper_id}"
                            else:
                                paper_data['url'] = '#' # 最终回退
                        
                        all_papers.append(paper_data)
                    except json.JSONDecodeError:
                        print(f"警告：跳过文件 {filepath} 中的一个无效JSON行。")
        except Exception as e:
            print(f"错误：处理文件 {filepath} 时出错: {e}")

    all_papers.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        with open(DATABASE_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(all_papers, f, ensure_ascii=False, indent=2)
        print(f"\n数据库构建成功！总共处理了 {len(all_papers)} 篇论文。")
        print(f"数据已保存到: {DATABASE_FILENAME}")
    except Exception as e:
        print(f"错误：写入数据库文件时出错: {e}")


if __name__ == "__main__":
    main()
