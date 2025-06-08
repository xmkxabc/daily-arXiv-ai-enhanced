import os
import re
from datetime import datetime, date, timedelta # Correctly import timedelta here
from collections import defaultdict
import calendar

# --- Configuration ---
DATA_DIR = "data"
README_PATH = "README.md"
TEMPLATE_PATH = "readme_content_template.md"

def get_report_files():
    """Scans the data directory, gets all report files, and sorts them by date."""
    files = []
    for filename in os.listdir(DATA_DIR):
        # Ensure we only process files with the YYYY-MM-DD.md format
        if re.match(r"\d{4}-\d{2}-\d{2}\.md$", filename):
            files.append(os.path.join(DATA_DIR, filename))
    # Sort files by name (i.e., by date) in descending order, latest first
    files.sort(reverse=True)
    return files

def parse_latest_report_toc(filepath):
    """Parses the latest report file to extract its Table of Contents."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # Use regex to find the Table of Contents section
        toc_match = re.search(r'# Table of Contents\n\n(.*?)\n\n<hr>', content, re.DOTALL)
        if not toc_match:
            return ""
        
        toc_lines = toc_match.group(1).strip().split('\n')
        # Convert the Markdown list to a more compact format
        mini_toc = " | ".join([line.strip().replace("- [", "").split("]")[0] for line in toc_lines])
        return mini_toc
    except Exception:
        return ""

def generate_dashboard_section(latest_file, recent_files):
    """Generates the Dynamic Digest Dashboard module."""
    if not latest_file:
        return "## Latest Report\n\nNo reports found.\n"

    latest_date_str = os.path.basename(latest_file).replace('.md', '')
    dashboard_md = f"## **Latest Report: {latest_date_str}**\n\n"
    
    mini_toc = parse_latest_report_toc(latest_file)
    if mini_toc:
        dashboard_md += f"**Today's Fields:** {mini_toc}\n\n"
    
    dashboard_md += f"> [**Read the full report for {latest_date_str}...**](./{latest_file})\n"
    
    # Add the "Past 7 Days" section
    dashboard_md += "\n---\n\n### **Past 7 Days**\n\n"
    for file in recent_files:
        date_str = os.path.basename(file).replace('.md', '')
        dashboard_md += f"- [{date_str}](./{file})\n"
        
    return dashboard_md

def generate_calendar_md(year, month, files_by_date):
    """Generates a Calendar Heatmap Markdown table for a given month."""
    cal = calendar.Calendar()
    month_name = date(year, month, 1).strftime('%B')
    
    md = f"#### {month_name} {year}\n\n"
    md += "| Mon | Tue | Wed | Thu | Fri | Sat | Sun |\n"
    md += "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
    
    for week in cal.monthdayscalendar(year, month):
        week_md = []
        for day in week:
            if day == 0:
                week_md.append(" ")
            else:
                day_str = f"{year}-{month:02d}-{day:02d}"
                if day_str in files_by_date:
                    link = f"[{day}](./{files_by_date[day_str]})"
                    # Highlight today's date
                    if date(year, month, day) == date.today():
                        link = f"**{link}**"
                    week_md.append(link)
                else:
                    day_val = str(day)
                    if date(year, month, day) == date.today():
                        day_val = f"**{day}**"
                    week_md.append(day_val)
        md += f"| {' | '.join(week_md)} |\n"
    return md

def generate_archive_md(files_by_year_month):
    """Generates the collapsible archive module."""
    md = "### **Full Archive**\n\n"
    
    # Sort by year in descending order
    for year in sorted(files_by_year_month.keys(), reverse=True):
        md += f"<details>\n<summary><strong>{year}</strong></summary>\n\n"
        # Sort by month in descending order
        for month in sorted(files_by_year_month[year].keys(), reverse=True):
            md += f"<details>\n<summary>{date(year, int(month), 1).strftime('%B')}</summary>\n\n"
            for file in sorted(files_by_year_month[year][month], reverse=True):
                date_str = os.path.basename(file).replace('.md', '')
                md += f"- [{date_str}](./{file})\n"
            md += "\n</details>\n"
        md += "\n</details>\n"
    return md

def main():
    """Main function to generate and update README.md."""
    report_files = get_report_files()
    if not report_files:
        print("No report files found in the data directory.")
        return

    # --- Prepare Data ---
    latest_report = report_files[0]
    # Get the last 7 reports (excluding the latest one)
    recent_reports = report_files[1:8] 
    
    files_by_date = {os.path.basename(f).replace('.md', ''): f for f in report_files}
    files_by_year_month = defaultdict(lambda: defaultdict(list))
    for f in report_files:
        basename = os.path.basename(f)
        year, month, _ = basename.split('-')
        files_by_year_month[int(year)][int(month)].append(f)

    # --- Generate Sections ---
    dashboard_md = generate_dashboard_section(latest_report, recent_reports)
    
    today = date.today()
    current_month_cal = generate_calendar_md(today.year, today.month, files_by_date)
    
    last_month_date = today.replace(day=1) - timedelta(days=1)

    last_month_cal = ""
    # If it's early in the month, show last month's calendar as well
    if today.day < 7: 
        last_month_cal = generate_calendar_md(last_month_date.year, last_month_date.month, files_by_date)

    # Exclude recent months from the archive to avoid duplication
    archive_files = defaultdict(lambda: defaultdict(list))
    for year, months in files_by_year_month.items():
        for month, files in months.items():
            is_in_calendar = (year == today.year and month == today.month) or \
                             (year == last_month_date.year and month == last_month_date.month and today.day < 7)
            if not is_in_calendar:
                archive_files[year][month].extend(files)

    archive_md = generate_archive_md(archive_files)
    
    # --- Combine Final Content ---
    content_parts = [
        dashboard_md,
        "---",
        "### Recent Calendar",
        current_month_cal
    ]
    if last_month_cal:
        content_parts.append(last_month_cal)
        
    content_parts.extend([
        "---",
        archive_md
    ])
    
    final_content = "\n\n".join(content_parts)

    # --- Read Template and Write to README.md ---
    try:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            readme_template = f.read()
        
        final_readme = readme_template.format(content=final_content)
        
        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(final_readme)
            
        print("README.md has been successfully updated!")
    except FileNotFoundError:
        print(f"Error: README template not found at {TEMPLATE_PATH}")

if __name__ == "__main__":
    main()
