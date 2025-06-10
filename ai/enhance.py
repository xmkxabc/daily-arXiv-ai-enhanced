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
from langchain_core.output_parsers import PydanticOutputParser
from structure import Structure

# 加载环境变量
if os.path.exists('.env'):
    dotenv.load_dotenv()

# --- 文件加载 ---
# 从脚本所在目录加载提示模板文件，增强可移植性
script_dir = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(script_dir, "template.txt"), "r", encoding="utf-8") as f:
        template_content = f.read()
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

def is_response_valid(result: Structure):
    """
    验证响应：检查所有字段都必须存在且为非空字符串。
    由于Structure模型已强制所有字段为必需，此函数主要作为防止AI返回空字符串的额外防线。
    """
    if not result:
        return False
    
    # 将 Pydantic 对象转为字典进行验证
    result_dict = result.model_dump()
    all_fields = Structure.model_fields.keys()

    for field in all_fields:
        value = result_dict.get(field)
        # 确保值不是None（理论上不会发生）并且不是一个空的或只包含空格的字符串
        if value is None or (isinstance(value, str) and not value.strip()):
            return False
            
    return True

def main():
    """主函数，运行增强过程。"""
    args = parse_args()
    
    # 从环境变量获取模型配置，提供默认值
    primary_model_name = os.environ.get("MODEL_NAME", 'gemini-1.5-flash-latest')
    fallback_models_str = os.environ.get("FALLBACK_MODELS", "gemini-1.5-pro-latest,gemini-1.0-pro")
    
    model_list = [primary_model_name]
    if fallback_models_str:
        model_list.extend([name.strip() for name in fallback_models_str.split(',') if name.strip()])

    language = os.environ.get("LANGUAGE", 'Chinese')

    # 检查API密钥
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("错误: 找不到环境变量 GOOGLE_API_KEY。", file=sys.stderr)
        sys.exit(1)

    # 读取并解析输入的JSONL文件
    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"错误: 处理文件 {args.data} 时出错: {e}", file=sys.stderr)
        return

    # 根据ID对数据去重
    seen_ids = set()
    unique_data = [item for item in data if item.get('id') not in seen_ids and not seen_ids.add(item['id'])]
    data = unique_data
    print(f"从 {args.data} 加载了 {len(data)} 篇不重复的论文", file=sys.stderr)

    # 设置Pydantic输出解析器
    output_parser = PydanticOutputParser(pydantic_object=Structure)

    # 将格式化指令注入到提示模板中
    human_template = template_content + "\n\n{format_instructions}\n"
    
    # 创建完整的提示模板
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(human_template)
    ])
    
    # 使用 .partial() 方法注入格式化指令
    prompt_template = prompt.partial(
        format_instructions=output_parser.get_format_instructions()
    )

    # 初始化所有指定的模型和链
    model_chains = {}
    for model_name in model_list:
        try:
            llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
            # 构建稳定、可靠的链
            chain = prompt_template | llm | output_parser
            model_chains[model_name] = chain
            print(f"模型已成功设置: {model_name}", file=sys.stderr)
        except Exception as e:
            print(f"警告：无法初始化模型 {model_name}。错误：{e}", file=sys.stderr)

    
    enhanced_data = []
    total_failures = 0
    current_model_index = 0

    for idx, d in enumerate(data):
        print(f"正在处理 {idx + 1}/{len(data)}: {d['id']}", file=sys.stderr)
        final_result = None
        
        # 循环尝试，直到成功或模型耗尽
        while current_model_index < len(model_list):
            current_model_name = model_list[current_model_index]
            print(f"  使用当前模型: {current_model_name}")
            
            chain = model_chains.get(current_model_name)
            if not chain:
                print(f"  错误：当前模型 {current_model_name} 未成功初始化，跳过。", file=sys.stderr)
                # 直接尝试下一个模型
                current_model_index += 1
                continue

            for attempt in range(args.retries):
                try:
                    response_object = chain.invoke({
                        "title": d['title'],
                        "content": d['summary'],
                        "language": language
                    })
                    
                    if response_object and is_response_valid(response_object):
                        final_result = response_object.model_dump() # 从Pydantic对象获取字典
                        print(f"  > 第 {attempt + 1} 次尝试成功", file=sys.stderr)
                        break # 当前论文处理成功，跳出重试循环
                
                except langchain_core.exceptions.OutputParserException as e:
                    print(f"  > 第 {attempt + 1} 次尝试输出解析失败: {e}", file=sys.stderr)
                except google_exceptions.ResourceExhausted as e:
                    print(f"  ! 模型 {current_model_name} 配额耗尽。错误: {e}", file=sys.stderr)
                    current_model_index += 1 # 永久切换到下一个模型
                    print(f"  ! 切换到下一个模型: {model_list[current_model_index] if current_model_index < len(model_list) else '无可用模型'}", file=sys.stderr)
                    break # 跳出重试循环，使用新模型
                except Exception as e:
                    print(f"  > 第 {attempt + 1} 次尝试时发生未知错误: {e}", file=sys.stderr)
                
                if attempt < args.retries - 1:
                    time.sleep(args.timeout)
            
            if final_result or current_model_index >= len(model_list):
                # 如果成功，或因配额问题切换模型，则跳出外层while循环
                break
        
        if not final_result:
            total_failures += 1
            print(f"  处理 {d['id']} 失败。", file=sys.stderr)
            # **优化点**: 失败时，生成一个符合Structure结构的完整错误记录
            error_message = "错误：AI分析失败。"
            d['AI'] = {field: error_message for field in Structure.model_fields.keys()}
        else:
            d['AI'] = final_result
            
        enhanced_data.append(d)
        time.sleep(2) # 友好地降低请求频率，避免触发速率限制

    # 构造输出文件名并写入结果
    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d_item in enhanced_data:
            f.write(json.dumps(d_item, ensure_ascii=False) + "\n")

    print(f"\n处理完成。成功处理: {len(enhanced_data) - total_failures}/{len(enhanced_data)}。输出文件: {output_filename}")

if __name__ == "__main__":
    main()

