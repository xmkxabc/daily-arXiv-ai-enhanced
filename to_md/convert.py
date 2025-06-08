import json
import os
import argparse
from collections import defaultdict

def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Converts a JSONL file to a Markdown file with a Table of Contents.")
    parser.add_argument("--input", type=str, required=True, help="The input JSONL file.")
    parser.add_argument("--template", type=str, required=True, help="The Markdown template file for each paper.")
    parser.add_argument("--output", type=str, required=True, help="The output Markdown file.")
    return parser.parse_args()

def generate_anchor(name):
    """Creates a URL-friendly anchor from a category name by removing special characters."""
    return "".join(char for char in name if char.isalnum()).lower()

def main():
    """Main function, executes the conversion process."""
    args = parse_args()
    
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

    # Group papers by category
    papers_by_category = defaultdict(list)
    for paper in data:
        category = paper.get('cate', 'Uncategorized')
        papers_by_category[category].append(paper)
    
    # Sort categories alphabetically for a consistent order
    sorted_categories = sorted(papers_by_category.keys())

    # --- Generate Table of Contents ---
    # The <a name="..."> tag creates an anchor for the "Back to Top" links to target.
    toc_content = "## Table of Contents\n<a name=\"table-of-contents\"></a>\n\n"
    for category in sorted_categories:
        count = len(papers_by_category[category])
        anchor = generate_anchor(category)
        # Create a clickable link for each category in the TOC
        toc_content += f"- [{category} ({count} papers)](#{anchor})\n"
    toc_content += "\n<hr>\n\n"

    # --- Generate Paper Content, Organized by Category ---
    paper_content = ""
    global_idx = 1
    for category in sorted_categories:
        anchor = generate_anchor(category)
        # Create a section header with an anchor that the TOC can link to
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
                "potential_applications": ai_data.get('potential_applications', 'N/A')
            }

            paper_output = template
            for key, value in replacement_data.items():
                str_value = str(value) if value is not None else 'N/A'
                paper_output = paper_output.replace(f"{{{key}}}", str_value)
            
            paper_content += paper_output + '\n'
            global_idx += 1
            
    # Combine TOC and content into the final output
    final_output = toc_content + paper_content
        
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(final_output)

    print(f"Successfully converted {len(data)} papers to Markdown with TOC and saved to {args.output}")

if __name__ == '__main__':
    main()
