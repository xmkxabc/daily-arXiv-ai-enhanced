import json
import os
import sys
import argparse
from collections import defaultdict
from itertools import count

def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Converts a JSONL file to a Markdown file with a ranked Table of Contents.")
    parser.add_argument("--input", type=str, required=True, help="The input JSONL file.")
    parser.add_argument("--template", type=str, required=True, help="The Markdown template file for each paper.")
    parser.add_argument("--output", type=str, required=True, help="The output Markdown file.")
    return parser.parse_args()

def main():
    """Main function to build the Markdown report."""
    args = parse_args()

    # --- 1. Load Data and Template ---
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

    # --- 2. Rank and Sort Categories ---
    preference_str = os.environ.get('CATEGORIES', 'cs.CV,cs.CL,cs.LG,cs.AI')
    preference = [cat.strip() for cat in preference_str.split(',')]

    def rank(category):
        """Assigns a rank to a category based on the preference list."""
        try:
            return preference.index(category)
        except ValueError:
            return len(preference)

    papers_by_category = defaultdict(list)
    for paper in data:
        # **FIX 1: Correctly get the primary category from the 'categories' list.**
        # Safely access the list and get the first item, default to "Uncategorized".
        categories_list = paper.get("categories", [])
        primary_category = categories_list[0] if categories_list else "Uncategorized"
        papers_by_category[primary_category].append(paper)
    
    sorted_categories = sorted(papers_by_category.keys(), key=rank)

    # --- 3. Generate Table of Contents ---
    markdown = "<div id=toc></div>\n\n# Table of Contents\n\n"
    for cate in sorted_categories:
        paper_count = len(papers_by_category[cate])
        markdown += f"- [{cate}](#{cate}) [Total: {paper_count}]\n"

    # --- 4. Generate Paper Content ---
    paper_idx_counter = count(1) 
    for cate in sorted_categories:
        markdown += f"\n\n<div id='{cate}'></div>\n\n"
        markdown += f"# {cate} [[Back]](#toc)\n\n"
        
        category_papers = papers_by_category[cate]
        
        paper_markdown_parts = []
        for item in category_papers:
            ai_data = item.get('AI', {})
            
            # **FIX 2: Correctly construct the full paper URL.**
            paper_id = item.get('id', '')
            # The 'id' from the spider is just the number, so we prepend the base URL.
            full_url = f"https://arxiv.org/abs/{paper_id}" if paper_id else "#"

            # Safely format the template
            formatted_paper = template.format(
                idx=next(paper_idx_counter),
                title=item.get("title", "N/A"),
                authors=", ".join(item.get("authors", ["N/A"])),
                summary=item.get("summary", "N/A").replace('\n', ' '),
                url=full_url, 
                cate=item.get("categories", ["N/A"])[0], # Use the correct key for category
                tldr=ai_data.get('tldr', 'N/A'),
                motivation=ai_data.get('motivation', 'N/A'),
                method=ai_data.get('method', 'N/A'),
                result=ai_data.get('result', 'N/A'),
                conclusion=ai_data.get('conclusion', 'N/A'),
                ai_summary=ai_data.get('summary', 'N/A'),
                translation=ai_data.get('translation', 'N/A')
            )
            paper_markdown_parts.append(formatted_paper)
            
        markdown += "\n\n".join(paper_markdown_parts)

    # --- 5. Write to Output File ---
    with open(args.output, "w", encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"Successfully converted {len(data)} papers to Markdown and saved to {args.output}")

if __name__ == "__main__":
    main()
