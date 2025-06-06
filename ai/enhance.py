import os
import json
import sys
import dotenv
import argparse

import langchain_core.exceptions
from langchain_zhipu import ChatZhipuAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
# Corrected import statement
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()
template = open("template.txt", "r").read()
system = open("system.txt", "r").read()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    return parser.parse_args()

def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'glm-4-flash')
    language = os.environ.get("LANGUAGE", 'Chinese')

    data = []
    with open(args.data, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                # 确保summary存在且非空
                if obj.get('summary'):
                    data.append(obj)
                else:
                    print(f"跳过无summary数据: {obj.get('id', '未知ID')}", file=sys.stderr)
            except Exception as e:
                print(f"数据解析失败: {e}", file=sys.stderr)

    # 去重
    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)
    data = unique_data

    print('Open:', args.data, file=sys.stderr)

    llm = ChatZhipuAI(
        model=model_name,
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_API_BASE")
    )
    print('Connect to:', model_name, file=sys.stderr)

    # 1. 将Pydantic模型作为"工具"绑定到LLM
    llm_with_tools = llm.bind_tools([Structure])
    # 2. 创建一个能够解析这个工具调用的解析器
    # Corrected class name
    output_parser = PydanticToolsParser(tools=[Structure])

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    
    # 3. 将 prompt | llm | parser 串联起来
    chain = prompt_template | llm_with_tools | output_parser

    enhanced_data = []
    fail_count = 0

    for idx, d in enumerate(data):
        response_data_list = None  # 记录原始模型返回
        try:
            # 解析器会返回一个列表，因为模型理论上可以一次调用多个工具
            response_data_list = chain.invoke({
                "language": language,
                "content": d['summary']
            })
            if response_data_list:
                # 我们只取第一个工具调用的结果
                response_raw = response_data_list[0]
                result = response_raw.model_dump() if hasattr(response_raw, "model_dump") else response_raw
                d['AI'] = result
            else:
                raise ValueError("模型未按预期返回结构化数据")
        except (langchain_core.exceptions.OutputParserException, ValueError, Exception) as e:
            print(f"{d['id']} 出错: {e}", file=sys.stderr)
            print(f"原始返回内容: {response_data_list}", file=sys.stderr)  # 打印原始返回
            fail_count += 1
            # 兼容Structure定义
            d['AI'] = {
                "tldr": "Error",
                "motivation": d.get("motivation", "Error"),
                "method": d.get("method", "Error"),
                "result": d.get("result", "Error"),
                "conclusion": d.get("conclusion", "Error")
            }
        enhanced_data.append(d)
        print(f"已完成 {idx+1}/{len(data)}", file=sys.stderr)

    out_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(out_file, "w", encoding="utf-8") as f:
        for d in enhanced_data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"全部完成，失败{fail_count}条，输出文件：{out_file}", file=sys.stderr)

if __name__ == "__main__":
    main()
