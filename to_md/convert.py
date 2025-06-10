import json
import os
import sys
import argparse
import re
from collections import defaultdict
from itertools import count

def parse_arguments():
    """解析命令行参数以匹配 run.yml"""
    parser = argparse.ArgumentParser(description="将JSONL文件转换为带目录的Markdown文件。")
    parser.add_argument("--input", type=str, required=True, help="输入的 JSONL 文件路径")
    parser.add_argument("--template", type=str, required=True, help="单篇论文的模板文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出的 Markdown 文件路径")
    return parser.parse_args()

def load_jsonl_data(file_path):
    """从JSONL文件加载数据"""
    if not os.path.exists(file_path):
        print(f"错误: 输入文件未找到 {file_path}", file=sys.stderr)
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f if line.strip()]
            return data if data else None
    except json.JSONDecodeError as e:
        print(f"错误: 解析JSONL文件失败 {file_path}: {e}", file=sys.stderr)
        return None

def load_template(file_path):
    """加载模板文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 模板文件未找到 {file_path}", file=sys.stderr)
        sys.exit(1)

def main():
    """主函数"""
    args = parse_arguments()
    
    input_file = args.input
    paper_template_file = args.template
    output_file = args.output
    main_template_file = 'template.md'
    
    match = re.search(r'(\d{4}-\d{2}-\d{2})', output_file)
    if not match:
        sys.exit(f"错误: 无法从输出文件名 '{output_file}' 中提取日期。")
    date_str = match.group(1)

    main_template = load_template(main_template_file)
    data = load_jsonl_data(input_file)

    if data is None:
        final_content = main_template.replace('{date}', date_str).replace('{content}', f"### 今日没有找到新论文。\n\n> 输入文件 '{input_file}' 未找到或为空。")
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(final_content)
        print(f"成功生成报告 (无新论文或输入文件丢失): {output_file}")
        sys.exit(0)
        
    paper_template = load_template(paper_template_file)

    preference_str = os.environ.get('CATEGORIES', 'cs.CV,cs.CL,cs.LG,cs.AI,stat.ML,eess.IV')
    preference = [cat.strip() for cat in preference_str.split(',')]
    rank = lambda category: preference.index(category) if category in preference else len(preference)

    papers_by_category = defaultdict(list)
    for paper in data:
        primary_category = (paper.get("categories") or [paper.get("cate", "N/A")])[0]
        papers_by_category[primary_category].append(paper)
    
    sorted_categories = sorted(papers_by_category.keys(), key=rank)

    toc_parts = [f"## Total Papers Today: {len(data)}\n", "<div id='toc'></div>\n", "### Table of Contents"]
    for cate in sorted_categories:
        toc_parts.append(f"- [{cate}](#{cate}) [Total: {len(papers_by_category[cate])}]")
    
    category_content_blocks = []
    paper_idx_counter = count(1)
    for cate in sorted_categories:
        category_header = f"## <div id='{cate}'></div> {cate} [[Back]](#toc)"
        
        papers_in_category_list = []
        for item in papers_by_category[cate]:
            ai_data = item.get('AI', {})
            
            # --- 关键修正: 添加所有新字段的映射 ---
            replacement_data = {
                "idx": next(paper_idx_counter),
                "title": item.get("title", "N/A"),
                "url": item.get('url', '#'),
                "authors": ', '.join(item.get("authors", ["N/A"])),
                "cate": (item.get("categories") or [item.get("cate", "N/A")])[0],
                "comment": item.get("comment", ""),
                
                # AI Fields mapped to placeholders
                "title_translation": ai_data.get('title_translation', ''),
                "keywords": ai_data.get('keywords', ''),
                "tldr": ai_data.get('tldr', ''),
                "ai_comment": ai_data.get('ai_comment', ''),
                "motivation": ai_data.get('motivation', ''),
                "method": ai_data.get('method', ''),
                "result": ai_data.get('result', ''),
                "conclusion": ai_data.get('conclusion', ''),
                "ai_summary": ai_data.get('ai_summary', ''),
                "translation": ai_data.get('abstract_translation', '')
            }
            
            temp_paper_content = paper_template
            for key, value in replacement_data.items():
                temp_paper_content = temp_paper_content.replace(f"{{{key}}}", str(value or ''))
            papers_in_category_list.append(temp_paper_content)

        full_category_block = category_header + "\n\n" + "\n\n---\n\n".join(papers_in_category_list)
        category_content_blocks.append(full_category_block)

    final_toc = "\n".join(toc_parts)
    all_papers_content = "\n\n".join(category_content_blocks)
    
    final_paper_content = f"{final_toc}\n\n{all_papers_content}"
    final_content = main_template.replace('{date}', date_str).replace('{content}', final_paper_content)

    with open(output_file, "w", encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"成功将 {len(data)} 篇论文转换为Markdown，并保存到 {output_file}")

if __name__ == "__main__":
    main()
