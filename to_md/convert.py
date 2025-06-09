import json
import os
import sys
from collections import defaultdict
from itertools import count
from datetime import datetime
from zoneinfo import ZoneInfo # Use the standard library for timezones (Python 3.9+)


def get_today_date():
    """
    Gets the current date in the Asia/Shanghai timezone.
    """
    tz = ZoneInfo('Asia/Shanghai')
    return datetime.now(tz).strftime('%Y-%m-%d')

def load_json_data(file_path):
    """
    Loads data from a JSON file with proper error handling.
    Returns None if the file is not found or is empty/invalid.
    """
    if not os.path.exists(file_path):
        print(f"信息: 文件未找到 {file_path}. 可能当天没有论文。", file=sys.stdout)
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data: # Check if the list is empty
                print(f"信息: JSON文件为空 {file_path}. 可能当天没有论文。", file=sys.stdout)
                return None
            return data
    except json.JSONDecodeError:
        print(f"错误: 解析JSON文件失败 {file_path}", file=sys.stderr)
        return None


def load_template(file_path):
    """
    Loads a template file with proper error handling.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"错误: 模板文件未找到 {file_path}", file=sys.stderr)
        sys.exit(1)


def main():
    """
    Main function to generate the markdown file from JSON data,
    with category grouping and a table of contents.
    """
    today_str = get_today_date()
    
    # Use project-consistent file paths
    input_file = 'daily_arxiv/papers.json'
    paper_template_file = 'to_md/paper_template.md'
    main_template_file = 'template.md'
    output_file = f'data/{today_str}.md'
    
    main_template = load_template(main_template_file)
    data = load_json_data(input_file)

    # If no data, create a simple report and exit
    if data is None:
        final_content = main_template.replace('{date}', today_str)
        final_content = final_content.replace('{content}', f"### 今日没有找到新论文。\n\n> 文件 '{input_file}' 未找到或为空。")
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(final_content)
        print(f"成功生成报告 (无新论文): {output_file}")
        sys.exit(0)
        
    paper_template = load_template(paper_template_file)

    # --- Your category preference and sorting logic ---
    preference_str = os.environ.get('CATEGORIES', 'cs.CV,cs.CL,cs.LG,cs.AI,stat.ML,eess.IV')
    preference = [cat.strip() for cat in preference_str.split(',')]
    def rank(category):
        try:
            return preference.index(category)
        except ValueError:
            return len(preference)

    papers_by_category = defaultdict(list)
    for paper in data:
        primary_category = paper.get("category", "Uncategorized")
        papers_by_category[primary_category].append(paper)
    
    sorted_categories = sorted(papers_by_category.keys(), key=rank)

    # --- Build Table of Contents and Paper Content ---
    total_papers = len(data)
    toc_parts = [f"## Total Papers Today: {total_papers}\n", "<div id='toc'></div>\n", "### Table of Contents\n"]
    for cate in sorted_categories:
        toc_parts.append(f"- [{cate}](#{cate}) [Total: {len(papers_by_category[cate])}]")
    
    paper_content_parts = []
    paper_idx_counter = count(1)
    for cate in sorted_categories:
        paper_content_parts.append(f"\n<div id='{cate}'></div>\n\n### {cate} [[Back]](#toc)\n")
        
        for item in papers_by_category[cate]:
            ai_data = item.get('AI', {})
            
            replacement_data = {
                "idx": next(paper_idx_counter),
                "title": item.get("title", "N/A"),
                "url": item.get('url', '#'),
                "authors": item.get("authors", "N/A"),
                "abstract": item.get("abstract", "N/A"),
                # AI generated fields
                "title_translation": ai_data.get('title_translation', ''),
                "keywords": ai_data.get('keywords', ''),
                "abstract_translation": ai_data.get('abstract_translation', ''),
                "comment": ai_data.get('comment', '')
            }
            
            temp_paper_content = paper_template
            for key, value in replacement_data.items():
                temp_paper_content = temp_paper_content.replace(f"{{{key}}}", str(value or ''))
            paper_content_parts.append(temp_paper_content)

    # --- Assemble Final Markdown ---
    final_paper_content = "\n".join(toc_parts) + "\n" + "\n".join(paper_content_parts)
    
    final_content = main_template.replace('{date}', today_str)
    final_content = final_content.replace('{content}', final_paper_content)

    with open(output_file, "w", encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"成功将 {total_papers} 篇论文转换为Markdown，并保存到 {output_file}")


if __name__ == "__main__":
    main()
