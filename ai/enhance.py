import os
import json
import sys
import dotenv
import argparse
import time
import langchain_core.exceptions
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core import exceptions as google_exceptions
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(script_dir, "template.txt"), "r", encoding="utf-8") as f:
        template = f.read()
    with open(os.path.join(script_dir, "system.txt"), "r", encoding="utf-8") as f:
        system = f.read()
except FileNotFoundError as e:
    print(f"错误：找不到必需的模板文件: {e}。搜索路径: {script_dir}", file=sys.stderr)
    sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="使用AI摘要增强arXiv数据。")
    parser.add_argument("--data", type=str, required=True, help="要处理的JSONL数据文件。")
    parser.add_argument("--retries", type=int, default=3, help="对每篇论文的最大重试次数。")
    parser.add_argument("--timeout", type=int, default=1, help="重试之间的等待秒数。")
    return parser.parse_args()

def is_response_valid(result):
    if not result: return False
    all_fields = Structure.model_fields.keys()
    for field in all_fields:
        if result.get(field) is None or not str(result.get(field)).strip():
            return False
    return True

def main():
    args = parse_args()
    primary_model_name = os.environ.get("MODEL_NAME", 'gemini-1.5-flash-preview-0520')
    fallback_models_str = os.environ.get("FALLBACK_MODELS", "gemini-1.5-flash-preview-0417,gemini-1.0-flash-001")
    model_list = [primary_model_name] + [name.strip() for name in fallback_models_str.split(',') if name.strip()] if fallback_models_str else [primary_model_name]
    language = os.environ.get("LANGUAGE", 'Chinese') 
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("错误: 找不到 GOOGLE_API_KEY。", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"错误: 处理文件 {args.data} 时出错: {e}", file=sys.stderr)
        return

    seen_ids = set()
    unique_data = [d for d in data if d.get('id') not in seen_ids and not seen_ids.add(d['id'])]
    print(f"从 {args.data} 加载了 {len(unique_data)} 篇不重复的论文", file=sys.stderr)
    data = unique_data

    prompt_template = ChatPromptTemplate.from_messages([SystemMessagePromptTemplate.from_template(system), HumanMessagePromptTemplate.from_template(template)])
    output_parser = PydanticToolsParser(tools=[Structure])
    model_chains = {}
    for model_name in model_list:
        try:
            llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
            chain = prompt_template | llm.bind_tools([Structure]) | output_parser
            model_chains[model_name] = chain
            print(f"模型已设置: {model_name}", file=sys.stderr)
        except Exception as e:
            print(f"警告：无法初始化模型 {model_name}。错误：{e}", file=sys.stderr)

    enhanced_data = []
    total_failures = 0
    current_model_index = 0

    for idx, d in enumerate(data):
        print(f"正在处理 {idx + 1}/{len(data)}: {d['id']}", file=sys.stderr)
        final_result = None
        current_model_name = model_list[current_model_index]
        print(f"  使用当前模型: {current_model_name}")
        chain = model_chains.get(current_model_name)
        if not chain:
            print(f"  错误：当前模型 {current_model_name} 未成功初始化，跳过。", file=sys.stderr)
        else:
            for attempt in range(args.retries):
                try:
                    # **核心修正**: 在调用AI时，同时传递 'title' 和 'content' (摘要)
                    response_data_list = chain.invoke({
                        "title": d.get('title', ''), 
                        "content": d.get('summary', ''), 
                        "language": language
                    })
                    if response_data_list:
                        result = response_data_list[0].model_dump()
                        if is_response_valid(result):
                            final_result = result
                            print(f"  > 第 {attempt + 1} 次尝试成功", file=sys.stderr)
                            break
                        else:
                            print(f"  > 第 {attempt + 1} 次尝试验证失败 (存在空字段)。", file=sys.stderr)
                    else:
                        print(f"  > 第 {attempt + 1} 次尝试失败 (模型未返回结构化数据)。", file=sys.stderr)
                except google_exceptions.ResourceExhausted as e:
                    print(f"  ! 模型 {current_model_name} 调用次数已耗尽。", file=sys.stderr)
                    if current_model_index < len(model_list) - 1:
                        current_model_index += 1
                        print(f"  ! 永久切换到下一个模型: {model_list[current_model_index]}", file=sys.stderr)
                    else:
                        print("  ! 所有模型均已耗尽。", file=sys.stderr)
                    break 
                except Exception as e:
                    print(f"  > 第 {attempt + 1} 次尝试出错: {e}", file=sys.stderr)
                if attempt < args.retries - 1:
                    time.sleep(args.timeout)
        if not final_result:
            total_failures += 1
            print(f"  处理 {d['id']} 失败。", file=sys.stderr)
            d['AI'] = {"title_translation": "错误：AI分析失败。", "tldr": None, "motivation": None, "method": None, "result": None, "conclusion": None, "translation": None, "summary": None, "comments": None, "keywords": None}
        else:
            d['AI'] = final_result
        enhanced_data.append(d)
        time.sleep(6)

    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d_item in enhanced_data:
            f.write(json.dumps(d_item, ensure_ascii=False) + "\n")
    print(f"\n处理完成。成功处理: {len(enhanced_data) - total_failures}/{len(enhanced_data)}。输出文件: {output_filename}")

if __name__ == "__main__":
    main()
