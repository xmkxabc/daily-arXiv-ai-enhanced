import os
import json
import re
from datetime import datetime

# --- 配置区 ---
DATA_DIR = "data" 
# GitHub Pages的标准输出目录
OUTPUT_DIR = "docs" 
DATABASE_FILENAME = os.path.join(OUTPUT_DIR, "database.json")

def get_enhanced_files(directory):
    """扫描data目录，找到所有AI增强后的jsonl文件。"""
    all_files = []
    for filename in os.listdir(directory):
        # 使用正则表达式确保我们只匹配正确格式的文件
        if re.match(r"\d{4}-\d{2}-\d{2}_AI_enhanced_.*\.jsonl$", filename):
            all_files.append(os.path.join(directory, filename))
    # 按文件名（即日期）降序排序，最新的在最前面
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
                        # 为每篇论文增加一个日期字段，方便前端排序
                        # 我们从文件名中提取日期
                        date_str = os.path.basename(filepath).split('_')[0]
                        paper_data['date'] = date_str
                        all_papers.append(paper_data)
                    except json.JSONDecodeError:
                        print(f"警告：跳过文件 {filepath} 中的一个无效JSON行。")
        except Exception as e:
            print(f"错误：处理文件 {filepath} 时出错: {e}")

    # 按日期对所有论文进行最终排序（最新的在前）
    # 这确保了网站在加载时，默认展示的就是最新的内容
    all_papers.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 将所有论文数据写入最终的数据库文件
    try:
        with open(DATABASE_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(all_papers, f, ensure_ascii=False, indent=2)
        print(f"\n数据库构建成功！总共处理了 {len(all_papers)} 篇论文。")
        print(f"数据已保存到: {DATABASE_FILENAME}")
    except Exception as e:
        print(f"错误：写入数据库文件时出错: {e}")


if __name__ == "__main__":
    main()
