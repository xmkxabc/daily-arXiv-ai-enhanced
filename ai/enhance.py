import argparse
import json
import os
import sys
import time
from pathlib import Path
import google.generativeai as genai

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="使用Google Gemini API增强ArXiv论文数据。")
    parser.add_argument("--data", type=str, required=True, help="输入的JSONL文件路径。")
    return parser.parse_args()

def load_papers(filepath):
    """从JSONL文件加载论文数据，并去除重复项。"""
    if not os.path.exists(filepath):
        print(f"警告: 文件 {filepath} 不存在。")
        return []
    
    papers = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                paper = json.loads(line)
                papers[paper['id']] = paper
            except json.JSONDecodeError:
                print(f"警告: 无法解析行: {line.strip()}")
    
    unique_papers = list(papers.values())
    print(f"从 {filepath} 加载了 {len(unique_papers)} 篇不重复的论文")
    return unique_papers

def get_model(api_key, model_name, fallback_models_str):
    """获取生成模型，如果主模型不可用，则尝试备用模型。"""
    genai.configure(api_key=api_key)
    models_to_try = [model_name] + [m.strip() for m in fallback_models_str.split(',') if m.strip()]
    
    for name in models_to_try:
        try:
            model = genai.GenerativeModel(name)
            print(f"模型已设置: {name}")
            return model
        except Exception as e:
            print(f"警告: 无法加载模型 {name}: {e}")
    
    sys.exit("错误: 所有指定模型均无法加载。请检查模型名称和API密钥。")

def call_gemini_with_json_mode(model, prompt, retries=3, delay=5):
    """
    使用JSON模式调用Gemini API，强制输出结构化数据。
    """
    # --- 关键修正: 定义期望的JSON输出格式 ---
    json_schema = {
        "type": "object",
        "properties": {
            "title_translation": {"type": "string", "description": "论文标题的中文翻译"},
            "keywords": {"type": "string", "description": "5个中文关键词，用逗号分隔"},
            "abstract_translation": {"type": "string", "description": "论文摘要的中文翻译"},
            "comment": {"type": "string", "description": "对论文的简短中文评论或总结"}
        },
        "required": ["title_translation", "keywords", "abstract_translation", "comment"]
    }

    # --- 关键修正: 配置模型以使用JSON模式 ---
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=json_schema
    )

    for attempt in range(retries):
        try:
            print(f"  > 第 {attempt + 1} 次尝试...", end='')
            response = model.generate_content(prompt, generation_config=generation_config)
            
            # 在JSON模式下，响应直接是JSON字符串
            parsed_json = json.loads(response.text)
            
            # 验证返回的JSON是否包含所有必需的字段
            if all(key in parsed_json and parsed_json[key] for key in json_schema["required"]):
                print("成功")
                return parsed_json
            else:
                print("失败 (返回的JSON缺少字段)。")

        except Exception as e:
            print(f"失败 (API错误: {e})。")
        
        if attempt < retries - 1:
            time.sleep(delay)
            
    return None

def main():
    args = parse_args()
    
    # 从环境变量加载配置
    api_key = os.environ.get("GOOGLE_API_KEY")
    language = os.environ.get("LANGUAGE", "Chinese")
    model_name = os.environ.get("MODEL_NAME", "gemini-2.0-flash")
    fallback_models = os.environ.get("FALLBACK_MODELS", "gemini-2.5-flash-preview-04-17,gemini-2.0-flash-001,gemini-2.0-flash-lite")

    if not api_key:
        sys.exit("错误: GOOGLE_API_KEY 环境变量未设置。")

    # 加载数据和模板
    papers = load_papers(args.data)
    if not papers:
        # 如果没有论文，创建一个空的输出文件并退出
        output_filename = f"data/{datetime.now().strftime('%Y-%m-%d')}_AI_enhanced_{language}.jsonl"
        Path(output_filename).touch()
        print("没有论文需要处理，已创建空输出文件。")
        return

    # 加载系统和用户提示模板
    try:
        system_prompt = Path('ai/system.txt').read_text(encoding='utf-8')
        user_template = Path('ai/template.txt').read_text(encoding='utf-8')
    except FileNotFoundError as e:
        sys.exit(f"错误: 无法找到模板文件: {e}")

    # 获取模型
    model = get_model(api_key, model_name, fallback_models)

    # 处理每篇论文
    enhanced_papers = []
    total = len(papers)
    success_count = 0

    output_filename = os.path.basename(args.data).replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    output_path = os.path.join('data', output_filename)

    for i, paper in enumerate(papers):
        print(f"正在处理 {i + 1}/{total}: {paper.get('id', 'N/A')}")
        
        # 构建提示
        paper_info = f"Title: {paper.get('title', '')}\nAuthors: {paper.get('authors', '')}\nAbstract: {paper.get('abstract', '')}"
        prompt = f"{system_prompt}\n\n{user_template}\n\n{paper_info}"

        # 调用API
        ai_data = call_gemini_with_json_mode(model, prompt)

        if ai_data:
            paper['AI'] = ai_data
            enhanced_papers.append(paper)
            success_count += 1
        else:
            print(f"  处理 {paper.get('id', 'N/A')} 失败。")

    # 将结果写入新的JSONL文件
    with open(output_path, 'w', encoding='utf-8') as f:
        for paper in enhanced_papers:
            f.write(json.dumps(paper, ensure_ascii=False) + '\n')

    print(f"处理完成。成功处理: {success_count}/{total}。输出文件: {output_path}")

if __name__ == "__main__":
    main()
