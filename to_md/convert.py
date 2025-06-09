import json
import os
import argparse
from collections import defaultdict
from itertools import count

def parse_args():
    parser = argparse.ArgumentParser(description="将JSONL文件转换为带目录的Markdown文件。")
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--template", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f]
    except Exception as e:
        print(f"错误: 处理文件 {args.input} 时出错: {e}", file=sys.stderr)
        return
    
    try:
        with open(args.template, 'r', encoding='utf-8') as f:
            template = f.read()
    except Exception as e:
        print(f"错误: 处理文件 {args.template} 时出错: {e}", file=sys.stderr)
        return

    preference_str = os.environ.get('CATEGORIES', 'cs.CV,cs.CL,cs.LG,cs.AI')
    preference = [cat.strip() for cat in preference_str.split(',')]
    def rank(category):
        try: return preference.index(category)
        except ValueError: return len(preference)

    papers_by_category = defaultdict(list)
    for paper in data:
        primary_category = (paper.get("categories") or [paper.get("cate")])[0] or "Uncategorized"
        papers_by_category[primary_category].append(paper)
    
    sorted_categories = sorted(papers_by_category.keys(), key=rank)

    total_papers = len(data)
    markdown = f"## Total Papers Today: {total_papers}\n\n"
    markdown += "<div id=toc></div>\n\n# Table of Contents\n\n"
    for cate in sorted_categories:
        markdown += f"- [{cate}](#{cate}) [Total: {len(papers_by_category[cate])}]\n"

    paper_idx_counter = count(1)
    for cate in sorted_categories:
        markdown += f"\n\n<div id='{cate}'></div>\n\n# {cate} [[Back]](#toc)\n\n"
        paper_markdown_parts = []
        for item in papers_by_category[cate]:
            ai_data = item.get('AI', {})
            full_url = item.get('url', f"[https://arxiv.org/abs/](https://arxiv.org/abs/){item.get('id', '')}")
            
            replacement_data = {
                "idx": next(paper_idx_counter), "title": item.get("title", "N/A"),
                "authors": ", ".join(item.get("authors", ["N/A"])), "url": full_url, 
                "cate": (item.get("categories") or ["N/A"])[0], "summary": item.get("summary", "N/A"),
                "comment": item.get("comment", ""), # arXiv comment
                "tldr": ai_data.get('tldr', 'N/A'), "motivation": ai_data.get('motivation', 'N/A'),
                "method": ai_data.get('method', 'N/A'), "result": ai_data.get('result', 'N/A'),
                "conclusion": ai_data.get('conclusion', 'N/A'),
                "ai_summary": ai_data.get('summary', 'N/A'), # AI summary
                "translation": ai_data.get('translation', 'N/A'),
                "comments": ai_data.get('comments', 'N/A') # AI comments
            }
            
            paper_output = template
            for key, value in replacement_data.items():
                paper_output = paper_output.replace(f"{{{key}}}", str(value or ''))
            paper_markdown_parts.append(paper_output)
        markdown += "\n\n".join(paper_markdown_parts)

    with open(args.output, "w", encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"成功将 {len(data)} 篇论文转换为Markdown，并保存到 {args.output}")

if __name__ == "__main__":
    main()