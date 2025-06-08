import os
import re
from datetime import datetime, date
from collections import defaultdict
import calendar

# --- 配置区 ---
DATA_DIR = "data"
README_PATH = "README.md"
TEMPLATE_PATH = "readme_content_template.md"

def get_report_files():
    """扫描data目录，获取所有报告文件并按日期排序。"""
    files = []
    for filename in os.listdir(DATA_DIR):
        # 确保只处理符合 YYYY-MM-DD.md 格式的文件
        if re.match(r"\d{4}-\d{2}-\d{2}\.md$", filename):
            files.append(os.path.join(DATA_DIR, filename))
    # 按文件名（即日期）降序排序，最新的在最前面
    files.sort(reverse=True)
    return files

def parse_latest_report_toc(filepath):
    """解析最新报告文件，提取其目录。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        # 使用正则表达式查找Table of Contents部分
        toc_match = re.search(r'# Table of Contents\n\n(.*?)\n\n<hr>', content, re.DOTALL)
        if not toc_match:
            return ""
        
        toc_lines = toc_match.group(1).strip().split('\n')
        # 将Markdown列表转换为更紧凑的格式
        mini_toc = " | ".join([line.strip().replace("- [", "").split("]")[0] for line in toc_lines])
        return mini_toc
    except Exception:
        return ""

def generate_dashboard_section(latest_file, recent_files):
    """生成动态摘要仪表盘模块。"""
    if not latest_file:
        return "## 最新速报\n\n暂无报告。\n"

    latest_date_str = os.path.basename(latest_file).replace('.md', '')
    dashboard_md = f"## **最新速报：{latest_date_str}**\n\n"
    
    mini_toc = parse_latest_report_toc(latest_file)
    if mini_toc:
        dashboard_md += f"**今日领域分布:** {mini_toc}\n\n"
    
    dashboard_md += f"> [**阅读 {latest_date_str} 的完整报告...**](./{latest_file})\n"
    
    # 增加“本周回顾”
    dashboard_md += "\n---\n\n### **本周回顾 (Past 7 Days)**\n\n"
    for file in recent_files:
        date_str = os.path.basename(file).replace('.md', '')
        dashboard_md += f"- [{date_str}](./{file})\n"
        
    return dashboard_md

def generate_calendar_md(year, month, files_by_date):
    """为指定月份生成日历热图的Markdown表格。"""
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
                    # 高亮当天
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
    """生成折叠存档模块。"""
    md = "### **历史存档 (Full Archive)**\n\n"
    
    # 按年份降序排序
    for year in sorted(files_by_year_month.keys(), reverse=True):
        md += f"<details>\n<summary><strong>{year}</strong></summary>\n\n"
        # 按月份降序排序
        for month in sorted(files_by_year_month[year].keys(), reverse=True):
            md += f"<details>\n<summary>{date(year, int(month), 1).strftime('%B')}</summary>\n\n"
            for file in sorted(files_by_year_month[year][month], reverse=True):
                date_str = os.path.basename(file).replace('.md', '')
                md += f"- [{date_str}](./{file})\n"
            md += "\n</details>\n"
        md += "\n</details>\n"
    return md

def main():
    """主函数，生成并更新README.md。"""
    report_files = get_report_files()
    if not report_files:
        print("在data目录中未找到任何报告文件。")
        return

    # --- 准备数据 ---
    latest_report = report_files[0]
    # 取最近的7个报告（不包括最新的那个）
    recent_reports = report_files[1:8] 
    
    files_by_date = {os.path.basename(f).replace('.md', ''): f for f in report_files}
    files_by_year_month = defaultdict(lambda: defaultdict(list))
    for f in report_files:
        basename = os.path.basename(f)
        year, month, _ = basename.split('-')
        files_by_year_month[int(year)][int(month)].append(f)

    # --- 生成各个模块 ---
    dashboard_md = generate_dashboard_section(latest_report, recent_reports)
    
    today = date.today()
    current_month_cal = generate_calendar_md(today.year, today.month, files_by_date)
    
    # 如果今天是月初，可能还想显示上个月的日历
    last_month_date = today.replace(day=1) - timedelta(days=1)
    # 修正了对timedelta的调用
    from datetime import timedelta

    last_month_cal = ""
    if today.day < 7: # 比如，如果还没到7号，就显示上个月的日历
        last_month_cal = generate_calendar_md(last_month_date.year, last_month_date.month, files_by_date)

    # 从存档中排除最近的月份，避免重复
    archive_files = defaultdict(lambda: defaultdict(list))
    for year, months in files_by_year_month.items():
        for month, files in months.items():
            # 不在日历中显示的才加入存档
            if not (year == today.year and month == today.month) and \
               not (year == last_month_date.year and month == last_month_date.month and today.day < 7):
                archive_files[year][month].extend(files)

    archive_md = generate_archive_md(archive_files)
    
    # --- 组合最终内容 ---
    content_parts = [
        dashboard_md,
        "---",
        "### 近期日历 (Recent Calendar)",
        current_month_cal
    ]
    if last_month_cal:
        content_parts.append(last_month_cal)
        
    content_parts.extend([
        "---",
        archive_md
    ])
    
    final_content = "\n\n".join(content_parts)

    # --- 读取模板并写入README.md ---
    try:
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            readme_template = f.read()
        
        final_readme = readme_template.format(content=final_content)
        
        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(final_readme)
            
        print("README.md 已成功更新！")
    except FileNotFoundError:
        print(f"错误：找不到README模板文件 {TEMPLATE_PATH}")

if __name__ == "__main__":
    main()
