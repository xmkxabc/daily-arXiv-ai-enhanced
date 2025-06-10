import os
import json
import sys
import dotenv
import argparse
import time

import langchain_core.exceptions
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core import exceptions as google_exceptions
from langchain.prompts import ChatPromptTemplate
from structure import Structure

# 加载环境变量
if os.path.exists('.env'):
    dotenv.load_dotenv()

# --- 文件加载 ---
script_dir = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(script_dir, "template.txt"), "r", encoding="utf-8") as f:
        template_content = f.read()
    with open(os.path.join(script_dir, "system.txt"), "r", encoding="utf-8") as f:
        system_prompt_template = f.read()
except FileNotFoundError as e:
    print(f"错误：找不到必需的模板文件: {e}。搜索路径: {script_dir}", file=sys.stderr)
    sys.exit(1)


def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="使用AI摘要增强arXiv数据。")
    parser.add_argument("--data", type=str, required=True, help="要处理的JSONL数据文件。")
    # **语义已恢复**: retries是针对每个模型/密钥组合的重试次数。
    parser.add_argument("--retries", type=int, default=3, help="对每个模型任务的最大重试次数。")
    parser.add_argument("--timeout", type=int, default=1, help="失败尝试之间的等待秒数。")
    return parser.parse_args()

def is_response_valid(result: Structure):
    """验证响应，确保所有字段都为非空字符串。"""
    if not result:
        return False
    result_dict = result.model_dump()
    all_fields = Structure.model_fields.keys()
    for field in all_fields:
        value = result_dict.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False
    return True

def main():
    """主函数，运行增强过程。"""
    args = parse_args()
    
    # --- 加载密钥和模型配置 ---
    primary_api_key = os.environ.get("GOOGLE_API_KEY")
    secondary_api_key = os.environ.get("SECONDARY_GOOGLE_API_KEY")
    primary_model_name = os.environ.get("MODEL_NAME", 'gemini-1.5-flash-latest')
    fallback_models_str = os.environ.get("FALLBACK_MODELS", "gemini-1.5-pro-latest,gemini-1.0-pro")
    
    # 构建级联调用计划
    cascade_plan = []
    if primary_api_key:
        cascade_plan.append({
            "key_name": "主密钥", 
            "api_key": primary_api_key, 
            "model_name": primary_model_name
        })
    if secondary_api_key:
        secondary_model_names = [primary_model_name]
        if fallback_models_str:
            secondary_model_names.extend([name.strip() for name in fallback_models_str.split(',') if name.strip()])
        for model_name in secondary_model_names:
            cascade_plan.append({
                "key_name": "副密钥", 
                "api_key": secondary_api_key, 
                "model_name": model_name
            })
            
    if not cascade_plan:
        print("错误: 找不到任何可用的API密钥来构建调用计划。", file=sys.stderr)
        sys.exit(1)

    language = os.environ.get("LANGUAGE", 'Chinese')

    # 读取和预处理数据
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"错误: 处理文件 {args.data} 时出错: {e}", file=sys.stderr)
        return
    seen_ids = set()
    unique_data = [item for item in data if item.get('id') not in seen_ids and not seen_ids.add(item['id'])]
    data = unique_data
    print(f"从 {args.data} 加载了 {len(data)} 篇不重复的论文", file=sys.stderr)

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt_template),
        ("human", template_content)
    ])

    # 预先初始化所有需要的调用链
    model_chains = {}
    for task in cascade_plan:
        key = (task["api_key"], task["model_name"])
        if key in model_chains: continue
        try:
            llm = ChatGoogleGenerativeAI(model=task["model_name"], google_api_key=task["api_key"])
            structured_llm = llm.with_structured_output(Structure)
            chain = prompt_template | structured_llm
            model_chains[key] = chain
            print(f"模型已为<{task['key_name']}>成功设置: {task['model_name']}", file=sys.stderr)
        except Exception as e:
            model_chains[key] = None
            print(f"警告：无法为<{task['key_name']}>初始化模型 {task['model_name']}。错误：{e}", file=sys.stderr)

    enhanced_data = []
    total_failures = 0

    for idx, d in enumerate(data):
        print(f"\n正在处理 {idx + 1}/{len(data)}: {d['id']}", file=sys.stderr)
        final_result = None
        
        # --- **新逻辑**: 经典重试与级联 ---
        # 外层循环遍历级联计划
        for task in cascade_plan:
            key = (task["api_key"], task["model_name"])
            chain = model_chains.get(key)
            
            if not chain:
                print(f"  跳过: <{task['key_name']}> - {task['model_name']} 未成功初始化。", file=sys.stderr)
                continue

            # 内层循环对当前任务进行重试
            for attempt in range(args.retries):
                print(f"  使用: <{task['key_name']}> - {task['model_name']} (尝试 {attempt + 1}/{args.retries})", file=sys.stderr)
                try:
                    response_object = chain.invoke({
                        "title": d['title'],
                        "content": d['summary'],
                        "language": language
                    })
                    if response_object and is_response_valid(response_object):
                        final_result = response_object.model_dump()
                        print(f"  > 尝试成功", file=sys.stderr)
                        break  # 成功，跳出内层重试循环

                except google_exceptions.ResourceExhausted as e:
                    print(f"  ! 配额耗尽: <{task['key_name']}> - {task['model_name']}。将切换到下一个任务...", file=sys.stderr)
                    break # 配额耗尽，跳出内层重试循环，让外层循环执行下一个任务

                except Exception as e:
                    print(f"  > 发生错误: {e}", file=sys.stderr)
                    if attempt < args.retries - 1:
                        print(f"  > 准备下一次尝试...", file=sys.stderr)
                        time.sleep(args.timeout)
            
            # 如果内层循环成功获得了结果，则无需再尝试级联计划中的下一个任务
            if final_result:
                break
        
        if not final_result:
            total_failures += 1
            print(f"  处理 {d['id']} 失败。所有级联任务均已尝试失败。", file=sys.stderr)
            error_message = "错误：AI分析失败。"
            d['AI'] = {field: error_message for field in Structure.model_fields.keys()}
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
