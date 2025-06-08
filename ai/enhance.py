import os
import json
import sys
import dotenv
import argparse
import time

import langchain_core.exceptions
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core import exceptions as google_exceptions
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()

# --- 文件加载 ---
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
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="使用AI摘要增强arXiv数据。")
    parser.add_argument("--data", type=str, required=True, help="要处理的JSONL数据文件。")
    parser.add_argument("--retries", type=int, default=3, help="对每篇论文的最大重试次数。")
    parser.add_argument("--timeout", type=int, default=1, help="重试之间的等待秒数。")
    return parser.parse_args()

def is_response_valid(result):
    """
    终极验证：检查所有字段都必须存在且为非空字符串。
    """
    if not result:
        return False
    
    all_fields = Structure.model_fields.keys()

    for field in all_fields:
        value = result.get(field)
        if value is None or not str(value).strip():
            return False
            
    return True

def main():
    """主函数，运行增强过程。"""
    args = parse_args()
    
    # --- 模型配置 ---
    # 更新了默认的主模型和备用模型列表
    primary_model_name = os.environ.get("MODEL_NAME", 'gemini-2.5-flash-preview-05-20')
    fallback_models_str = os.environ.get("FALLBACK_MODELS", "gemini-2.5-flash-preview-04-17,gemini-2.0-flash-001,gemini-2.0-flash-lite")
    
    model_list = [primary_model_name]
    if fallback_models_str:
        model_list.extend([name.strip() for name in fallback_models_str.split(',')])

    language = os.environ.get("LANGUAGE", 'Chinese') 

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("错误: 找不到 GOOGLE_API_KEY。", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: 在 {args.data} 找不到数据文件", file=sys.stderr)
        return
    except json.JSONDecodeError as e:
        print(f"错误: JSON解码失败 {args.data} - {e}", file=sys.stderr)
        return

    # 数据去重
    seen_ids = set()
    unique_data = []
    for item in data:
        if item.get('id') not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)
    data = unique_data
    print(f"从 {args.data} 加载了 {len(data)} 篇不重复的论文", file=sys.stderr)

    # --- 为所有可用模型创建LangChain链 ---
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template)
    ])
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

    
    # --- 主处理循环 ---
    enhanced_data = []
    total_failures = 0
    current_model_index = 0 # 从主模型开始

    for idx, d in enumerate(data):
        print(f"正在处理 {idx + 1}/{len(data)}: {d['id']}", file=sys.stderr)
        final_result = None
        
        # **核心逻辑：使用当前选定的模型进行处理**
        current_model_name = model_list[current_model_index]
        print(f"  使用当前模型: {current_model_name}")
        
        chain = model_chains.get(current_model_name)
        if not chain:
            print(f"  错误：当前模型 {current_model_name} 未成功初始化，跳过。", file=sys.stderr)
            final_result = None
        else:
            for attempt in range(args.retries):
                try:
                    response_data_list = chain.invoke({"language": language, "content": d['summary']})
                    if response_data_list:
                        result = response_data_list[0].model_dump()
                        if is_response_valid(result):
                            final_result = result
                            print(f"  > 第 {attempt + 1} 次尝试成功", file=sys.stderr)
                            break # 成功，跳出重试循环
                        else:
                            print(f"  > 第 {attempt + 1} 次尝试验证失败 (存在空字段)。", file=sys.stderr)
                    else:
                        print(f"  > 第 {attempt + 1} 次尝试失败 (模型未返回结构化数据)。", file=sys.stderr)
                
                except google_exceptions.ResourceExhausted as e:
                    print(f"  ! 模型 {current_model_name} 调用次数已耗尽。错误: {e}", file=sys.stderr)
                    # 如果还有备用模型，则切换到下一个模型
                    if current_model_index < len(model_list) - 1:
                        current_model_index += 1
                        print(f"  ! 永久切换到下一个模型: {model_list[current_model_index]}", file=sys.stderr)
                    else:
                        print("  ! 所有模型均已耗尽。", file=sys.stderr)
                    break # 无论如何，都停止对当前论文的尝试
                
                except Exception as e:
                    print(f"  > 第 {attempt + 1} 次尝试出错: {e}", file=sys.stderr)
                
                if attempt < args.retries - 1:
                    time.sleep(args.timeout)

        if not final_result:
            total_failures += 1
            print(f"  处理 {d['id']} 失败。", file=sys.stderr)
            d['AI'] = {
                "tldr": "错误：AI分析失败。", "motivation": None, "method": None,
                "result": None, "conclusion": None, "translation": None,
                "related_work": None, "potential_applications": None, "future_work": None
            }
        else:
            d['AI'] = final_result
            
        enhanced_data.append(d)
        
        # 遵守最严格模型的RPM限制 (10 RPM -> 6秒/次)
        time.sleep(6)

    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d_item in enhanced_data:
            f.write(json.dumps(d_item, ensure_ascii=False) + "\n")

    print(f"\n处理完成。成功处理: {len(enhanced_data) - total_failures}/{len(enhanced_data)}。输出文件: {output_filename}")

if __name__ == "__main__":
    main()
