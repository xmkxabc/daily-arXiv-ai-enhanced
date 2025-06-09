import json
import os
import sys
import argparse
import re
from collections import defaultdict
from itertools import count

def parse_arguments():
    """
    Parses command-line arguments.
    Accepts --data, as called by the user's run.sh script.
    """
    parser = argparse.ArgumentParser(description="将JSONL文件转换为带目录的Markdown文件。")
    parser.add_argument("--data", type=str, required=True, help="输入的 JSONL 文件路径")
    return parser.parse_args()

def load_jsonl_data(file_path):
    """
    Loads data from a JSONL file (one JSON object per line).
    Returns None if the file is not found or is empty/invalid.
    """
    if not os.path.exists(file_path):
        print(f"错误: 输入文件未找到 {file_path}", file=sys.stderr)
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f if line.strip()]
            if not data:
                print(f"信息: JSONL文件为空 {file_path}.", file=sys.stdout)
                return None
            return data
    except json.JSONDecodeError as e:
        print(f"错误: 解析JSONL文件失败 {file_path}: {e}", file=sys.stderr)
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
    Main function to generate the markdown file from JSONL data.
    """
    args = parse_arguments()
    
    input_file = args.data
    
    # 从输入文件名中提取日期
    match = re.search(r'(\d{4}-\d{2}-\d{2})', input_file)
    if not match:
        print(f"错误: 无法从输入文件名 '{input_file}' 中提取日期。文件名格式应为 YYYY-MM-DD*.jsonl", file=sys.stderr)
        sys.exit(1)
    date_str = match.group(1)

    # --- 关键修正: 根据在根目录执行的事实，修正所有文件路径 ---
    paper_template_file = 'to_md/paper_template.md' # 纸张模板在 to_md/ 子目录中
    main_template_file = 'template.md'              # 主模板在根目录中
    output_file = f'data/{date_str}.md'             # 输出文件在 data/ 子目录中

    main_template = load_template(main_template_file)
    data = load_jsonl_data(input_file)

    if data is None:
        final_content = main_template.replace('{date}', date_str)
        final_content = final_content.replace('{content}', f"### 今日没有找到新论文。\n\n> 输入文件 '{input_file}' 未找到或为空。")
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(final_content)
        print(f"成功生成报告 (无新论文或输入文件丢失): {output_file}")
        sys.exit(0)
        
    paper_template = load_template(paper_template_file)

    # --- 分类和排序逻辑 (保持不变) ---
    preference_str = os.environ.get('CATEGORIES', 'cs.CV,cs.CL,cs.LG,cs.AI,stat.ML,eess.IV')
    preference = [cat.strip() for cat in preference_str.split(',')]
    def rank(category):
        try:
            return preference.index(category)
        except ValueError:
            return len(preference)

    papers_by_category = defaultdict(list)
    for paper in data:
        primary_category = (paper.get("categories") or [paper.get("cate")])[0] or "Uncategorized"
        papers_by_category[primary_category].append(paper)
    
    sorted_categories = sorted(papers_by_category.keys(), key=rank)

    # --- Markdown 内容生成 (保持不变) ---
    total_papers = len(data)
    toc_parts = [f"## Total Papers Today: {total_papers}\n", "<div id='toc'></div>\n", "### Table of Contents"]
    for cate in sorted_categories:
        toc_parts.append(f"- [{cate}](#{cate}) [Total: {len(papers_by_category[cate])}]")
    
    category_content_blocks = []
    paper_idx_counter = count(1)
    for cate in sorted_categories:
        category_header = f"## <div id='{cate}'></div> {cate} [[Back]](#toc)"
        
        papers_in_category_list = []
        for item in papers_by_category[cate]:
            ai_data = item.get('AI', {})
            
            replacement_data = {
                "idx": next(paper_idx_counter),
                "title": item.get("title", "N/A"),
                "url": item.get('url', '#'),
                "authors": item.get("authors", "N/A"),
                "abstract": item.get("abstract", "N/A"),
                "comment": item.get("comment", ""), # 这是来自 arXiv 的原始备注
                "title_translation": ai_data.get('title_translation', ''),
                "keywords": ai_data.get('keywords', ''),
                "abstract_translation": ai_data.get('abstract_translation', ''),
                "ai_comment": ai_data.get('comment', '') # 这是 AI 生成的备注
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
    
    final_content = main_template.replace('{date}', date_str)
    final_content = final_content.replace('{content}', final_paper_content)

    with open(output_file, "w", encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"成功将 {total_papers} 篇论文转换为Markdown，并保存到 {output_file}")

if __name__ == "__main__":
    main()
