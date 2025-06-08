import os
import json
import sys
import dotenv
import argparse
import time

import langchain_core.exceptions
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()

# --- File Loading ---
script_dir = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(script_dir, "template.txt"), "r", encoding="utf-8") as f:
        template = f.read()
    with open(os.path.join(script_dir, "system.txt"), "r", encoding="utf-8") as f:
        system = f.read()
except FileNotFoundError as e:
    print(f"Error: Required template file not found: {e}. Searched in {script_dir}", file=sys.stderr)
    sys.exit(1)


def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Enhance arXiv data with AI-generated summaries.")
    parser.add_argument("--data", type=str, required=True, help="The JSONL data file to process.")
    parser.add_argument("--retries", type=int, default=3, help="Maximum number of retries for each paper.")
    parser.add_argument("--timeout", type=int, default=1, help="Seconds to wait between retries.")
    return parser.parse_args()

def is_response_valid(result):
    """
    Checks if the AI response is valid.
    """
    if not result:
        return False
    
    tldr = result.get("tldr")
    if not tldr or "one-sentence summary" in tldr.lower() or tldr == "Error" or "?" in tldr:
        return False
        
    translation = result.get("translation")
    if not translation or "?" in translation:
        return False

    # Check that at least a few analytical fields were successfully populated
    other_fields = ["motivation", "method", "result", "conclusion", "related_work", "potential_applications"]
    meaningful_answers = 0
    for field in other_fields:
        content = result.get(field)
        if content and "?" not in content:
            meaningful_answers += 1
            
    # We require at least 2 other fields to have meaningful answers, as not every abstract contains all info.
    return meaningful_answers >= 2

def main():
    """Main function to run the enhancement process."""
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'gemini-2.0-flash')
    language = os.environ.get("LANGUAGE", 'English') # Defaulting to English now

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.", file=sys.stderr)
        print("Please set the GOOGLE_API_KEY in your .env file or as an environment variable.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.data, "r", encoding="utf-8") as f:
            data = [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Data file not found at {args.data}", file=sys.stderr)
        return
    except json.JSONDecodeError as e:
        print(f"Error: JSON decoding failed for {args.data} - {e}", file=sys.stderr)
        return

    seen_ids = set()
    unique_data = []
    for item in data:
        if item.get('id') not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)
    data = unique_data
    print(f"Loaded {len(data)} unique papers from: {args.data}", file=sys.stderr)

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        convert_system_message_to_human=True
    )
    print(f'Connecting to model: {model_name}', file=sys.stderr)

    llm_with_tools = llm.bind_tools([Structure])
    output_parser = PydanticToolsParser(tools=[Structure])
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    chain = prompt_template | llm_with_tools | output_parser

    enhanced_data = []
    total_failures = 0

    for idx, d in enumerate(data):
        print(f"Processing {idx + 1}/{len(data)}: {d['id']}", file=sys.stderr)
        final_result = None
        
        for attempt in range(args.retries):
            try:
                response_data_list = chain.invoke({"language": language, "content": d['summary']})
                if response_data_list:
                    result = response_data_list[0].model_dump()
                    if is_response_valid(result):
                        final_result = result
                        print(f"  Success on attempt {attempt + 1}", file=sys.stderr)
                        break
                    else:
                        print(f"  Attempt {attempt + 1} failed validation (incomplete data). Response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
                else:
                    print(f"  Attempt {attempt + 1} failed (model returned no structured data).", file=sys.stderr)
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed with error: {e}", file=sys.stderr)
            
            if attempt < args.retries - 1:
                time.sleep(args.timeout)

        if not final_result:
            total_failures += 1
            print(f"  Failed to process {d['id']} after {args.retries} attempts.", file=sys.stderr)
            d['AI'] = {
                "tldr": "Error: Failed to generate summary.", "motivation": None, "method": None,
                "result": None, "conclusion": None, "translation": None,
                "related_work": None, "potential_applications": None
            }
        else:
            d['AI'] = final_result
            
        enhanced_data.append(d)
        # Delay to respect API rate limits (30 RPM means 2 seconds per request)
        time.sleep(2)

    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d_item in enhanced_data:
            f.write(json.dumps(d_item, ensure_ascii=False) + "\n")

    print(f"\nProcessing complete. Successfully processed: {len(enhanced_data) - total_failures}/{len(enhanced_data)}. Output file: {output_filename}")

if __name__ == "__main__":
    main()
