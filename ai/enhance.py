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
# **优化点 1: 导入更稳定、更适合此场景的 PydanticOutputParser**
from langchain_core.output_parsers import PydanticOutputParser
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()

# --- 文件加载 (保持不变) ---
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
    """解析命令行参数。(保持不变)"""
    parser = argparse.ArgumentParser(description="使用AI摘要增强arXiv数据。")
    parser.add_argument("--data", type=str, required=True, help="要处理的JSONL数据文件。")
    parser.add_argument("--retries", type=int, default=3, help="对每篇论文的最大重试次数。")
    parser.add_argument("--timeout", type=int, default=1, help="重试之间的等待秒数。")
    return parser.parse_args()

def is_response_valid(result: Structure):
    """
    终极验证：检查所有字段都必须存在且为非空字符串。
    参数类型现在是 Structure 对象。
    """
    if not result:
        return False
    
    # 将 Pydantic 对象转为字典进行验证
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
    
    primary_model_name = os.environ.get("MODEL_NAME", 'gemini-1.5-flash-latest')
    fallback_models_str = os.environ.get("FALLBACK_MODELS", "gemini-1.5-pro-latest,gemini-1.0-pro")
    
    model_list = [primary_model_name]
    if fallback_models_str:
        model_list.extend([name.strip() for name in fallback_models_str.split(',') if name.strip()])

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

    # 数据去重 (保持不变)
    seen_ids = set()
    unique_data = [item for item in data if item.get('id') not in seen_ids and not seen_ids.add(item['id'])]
    data = unique_data
    print(f"从 {args.data} 加载了 {len(data)} 篇不重复的论文", file=sys.stderr)

    # **优化点 2: 设置 PydanticOutputParser**
    output_parser = PydanticOutputParser(pydantic_object=Structure)

    # **优化点 3: 将格式化指令注入到提示模板中**
    # 这会告诉LLM如何格式化输出以匹配Structure模型
    human_template = template_content + "\n\n{format_instructions}\n"
    
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(human_template)
    ], partial_variables={"format_instructions": output_parser.get_format_instructions()})


    # 初始化模型和链
    model_chains = {}
    for model_name in model_list:
        try:
            llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
            # **优化点 4: 构建新的、更稳定的链，移除 .bind_tools()**
            chain = prompt_template | llm | output_parser
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
                    response_object = chain.invoke({
                        "title": d['title'],
                        "content": d['summary'],
                        "language": language
                    })
                    
                    if response_object and is_response_valid(response_object):
                        final_result = response_object.model_dump() # 从Pydantic对象获取字典
                        print(f"  > 第 {attempt + 1} 次尝试成功", file=sys.stderr)
                        break
                    else:
                        print(f"  > 第 {attempt + 1} 次尝试返回数据无效或验证失败。", file=sys.stderr)

                except google_exceptions.ResourceExhausted as e:
                    print(f"  ! 模型 {current_model_name} 调用次数已耗尽。错误: {e}", file=sys.stderr)
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
            d['AI'] = {"title_translation": "错误：AI分析失败."} # 简化错误信息
        else:
            d['AI'] = final_result
            
        enhanced_data.append(d)
        time.sleep(2) # 降低请求频率

    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d_item in enhanced_data:
            f.write(json.dumps(d_item, ensure_ascii=False) + "\n")

    print(f"\n处理完成。成功处理: {len(enhanced_data) - total_failures}/{len(enhanced_data)}。输出文件: {output_filename}")

if __name__ == "__main__":
    main()
