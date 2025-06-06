import os
import json
import sys
import dotenv
import argparse

import langchain_core.exceptions
from langchain_zhipu import ChatZhipuAI   # 改这里
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
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

    # 改这里
    llm = ChatZhipuAI(
        model=model_name,
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_API_BASE")
    ).with_structured_output(Structure, method="function_calling")

    print('Connect to:', model_name, file=sys.stderr)
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    chain = prompt_template | llm

    enhanced_data = []
    fail_count = 0

    for idx, d in enumerate(data):
        try:
            response: Structure = chain.invoke({
                "language": language,
                "content": d['summary']
            })
            if response is not None:
                d['AI'] = response.model_dump()
            else:
                raise ValueError("模型返回了None")
        except (langchain_core.exceptions.OutputParserException, ValueError, Exception) as e:
            print(f"{d['id']} 出错: {e}", file=sys.stderr)
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
