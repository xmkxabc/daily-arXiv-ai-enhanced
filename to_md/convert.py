import json
import os
import argparse
from collections import defaultdict

def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="将JSONL文件转换为带目录的Markdown文件。")
    parser.add_argument("--input", type=str, required=True, help="输入的JSONL文件。")
    parser.add_argument("--template", type=str, required=True, help="每篇论文的Markdown模板文件。")
    parser.add_argument("--output", type=str, required=True, help="输出的Markdown文件。")
    return parser.parse_args()

def generate_anchor(name):
    """从分类名称创建URL友好的锚点。"""
    return "".join(char for char in name if char.isalnum()).lower()

def main():
    """主函数，执行转换过程。"""
    args = parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = [json.loads(line) for line in f]
    except FileNotFoundError:
        print(f"错误: 在 {args.input} 找不到输入文件", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(f"错误: 无法解析 {args.input}。请确保是有效的JSONL格式。", file=sys.stderr)
        return
        
    try:
        with open(args.template, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"错误: 在 {args.template} 找不到模板文件", file=sys.stderr)
        return

    # 按分类对论文进行分组
    papers_by_category = defaultdict(list)
    for paper in data:
        category = paper.get('cate', 'Uncategorized')
        papers_by_category[category].append(paper)
    
    # 对分类进行排序以保持一致的顺序
    sorted_categories = sorted(papers_by_category.keys())

    # --- 生成目录 ---
    toc_content = "## Table of Contents\n<a name=\"table-of-contents\"></a>\n\n"
    for category in sorted_categories:
        count = len(papers_by_category[category])
        anchor = generate_anchor(category)
        toc_content += f"- [{category} ({count} papers)](#{anchor})\n"
    toc_content += "\n<hr>\n\n"

    # --- 生成论文内容 ---
    paper_content = ""
    global_idx = 1
    for category in sorted_categories:
        anchor = generate_anchor(category)
        paper_content += f"## {category}\n<a name=\"{anchor}\"></a>\n\n"
        
        for paper in papers_by_category[category]:
            ai_data = paper.get('AI', {})
            
            replacement_data = {
                "idx": global_idx,
                "title": paper.get('title', 'N/A'),
                "url": paper.get('id', '#'),
                "authors": ', '.join(paper.get('authors', ['N/A'])),
                "cate": paper.get('cate', 'N/A'),
                "summary": paper.get('summary', 'N/A').replace('\n', ' '),
                "translation": ai_data.get('translation', 'N/A'),
                "tldr": ai_data.get('tldr', 'N/A'),
                "motivation": ai_data.get('motivation', 'N/A'),
                "method": ai_data.get('method', 'N/A'),
                "result": ai_data.get('result', 'N/A'),
                "conclusion": ai_data.get('conclusion', 'N/A'),
                "related_work": ai_data.get('related_work', 'N/A'),
                "potential_applications": ai_data.get('potential_applications', 'N/A'),
                "future_work": ai_data.get('future_work', 'N/A')
            }

            paper_output = template
            for key, value in replacement_data.items():
                str_value = str(value) if value is not None else 'N/A'
                paper_output = paper_output.replace(f"{{{key}}}", str_value)
            
            paper_content += paper_output + '\n'
            global_idx += 1
            
    # 合并目录和内容
    final_output = toc_content + paper_content
        
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(final_output)

    print(f"成功将 {len(data)} 篇论文转换为带目录的Markdown，并保存到 {args.output}")

if __name__ == '__main__':
    main()
