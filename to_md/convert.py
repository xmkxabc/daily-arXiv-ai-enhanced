import json
import os
import sys
import argparse
from collections import defaultdict
from itertools import count

def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="将JSONL文件转换为带目录的Markdown文件。")
    parser.add_argument("--input", type=str, required=True, help="输入的JSONL文件。")
    parser.add_argument("--template", type=str, required=True, help="每篇论文的Markdown模板文件。")
    parser.add_argument("--output", type=str, required=True, help="输出的Markdown文件。")
    return parser.parse_args()

def main():
    """主函数，构建Markdown报告。"""
    args = parse_args()

    # --- 1. 加载数据和模板 ---
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f]
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input}", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(f"Error: Could not parse {args.input}. Please ensure it is a valid JSONL file.", file=sys.stderr)
        return

    try:
        with open(args.template, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found at {args.template}", file=sys.stderr)
        return

    # --- 2. 排序和分组 ---
    preference_str = os.environ.get('CATEGORIES', 'cs.CV,cs.CL,cs.LG,cs.AI')
    preference = [cat.strip() for cat in preference_str.split(',')]

    def rank(category):
        """根据偏好列表为分类分配排名。"""
        try:
            return preference.index(category)
        except ValueError:
            return len(preference)

    papers_by_category = defaultdict(list)
    for paper in data:
        categories_list = paper.get("categories", [])
        primary_category = categories_list[0] if categories_list else "Uncategorized"
        papers_by_category[primary_category].append(paper)
    
    sorted_categories = sorted(papers_by_category.keys(), key=rank)

    # --- 3. 生成目录 ---
    total_papers = len(data)
    markdown = f"## Total Papers Today: {total_papers}\n\n"
    markdown += "<div id=toc></div>\n\n# Table of Contents\n\n"
    for cate in sorted_categories:
        paper_count = len(papers_by_category[cate])
        markdown += f"- [{cate}](#{cate}) [Total: {paper_count}]\n"

    # --- 4. 生成论文内容 ---
    paper_idx_counter = count(1) 
    for cate in sorted_categories:
        markdown += f"\n\n<div id='{cate}'></div>\n\n"
        markdown += f"# {cate} [[Back]](#toc)\n\n"
        
        category_papers = papers_by_category[cate]
        
        paper_markdown_parts = []
        for item in category_papers:
            ai_data = item.get('AI', {})
            paper_id = item.get('id', '')
            full_url = f"https://arxiv.org/abs/{paper_id}" if paper_id else "#"

            # 准备一个清晰的数据字典用于替换
            replacement_data = {
                "idx": next(paper_idx_counter),
                "title": item.get("title", "N/A"),
                "authors": ", ".join(item.get("authors", ["N/A"])),
                "url": full_url, 
                "cate": item.get("categories", ["N/A"])[0],
                # 'summary' 来自原始数据 'item'
                "summary": item.get("summary", "N/A").replace('\n', ' '),
                "tldr": ai_data.get('tldr', 'N/A'),
                "motivation": ai_data.get('motivation', 'N/A'),
                "method": ai_data.get('method', 'N/A'),
                "result": ai_data.get('result', 'N/A'),
                "conclusion": ai_data.get('conclusion', 'N/A'),
                # 'ai_summary' 来自AI分析结果 'ai_data'
                "ai_summary": ai_data.get('summary', 'N/A'), 
                "translation": ai_data.get('translation', 'N/A')
            }

            paper_output = template
            for key, value in replacement_data.items():
                str_value = str(value) if value is not None else 'N/A'
                paper_output = paper_output.replace(f"{{{key}}}", str_value)

            paper_markdown_parts.append(paper_output)
            
        markdown += "\n\n".join(paper_markdown_parts)

    # --- 5. 写入输出文件 ---
    with open(args.output, "w", encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"Successfully converted {len(data)} papers to Markdown and saved to {args.output}")

if __name__ == "__main__":
    main()
