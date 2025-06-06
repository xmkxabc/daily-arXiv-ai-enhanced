import os
import json
import sys
import dotenv
import argparse
import time

import langchain_core.exceptions
from langchain_zhipu import ChatZhipuAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()

# --- Corrected File Loading ---
# Get the absolute path of the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load templates from files using absolute paths
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
    parser.add_argument("--data", type=str, required=True, help="JSONL data file to process.")
    parser.add_argument("--retries", type=int, default=3, help="Maximum number of retries for each paper.")
    parser.add_argument("--timeout", type=int, default=1, help="Seconds to wait between retries.")
    return parser.parse_args()

def is_response_valid(result):
    """
    Checks if the AI response is valid and not just placeholder text or questions.
    """
    if not result:
        return False
        
    # Check if tldr is present, not a placeholder, and not a question
    tldr = result.get("tldr")
    if not tldr or "one-sentence summary" in tldr.lower() or tldr == "Error" or "?" in tldr:
        return False
        
    # Check that at least one other field has a meaningful answer, not a question or None
    other_fields = ["motivation", "method", "result", "conclusion"]
    meaningful_answers = 0
    for field in other_fields:
        content = result.get(field)
        # Check if content is not None and doesn't contain a question mark
        if content and "?" not in content:
            meaningful_answers += 1
            
    # We require at least one other field to have a meaningful answer.
    return meaningful_answers > 0

def main():
    """Main function to run the enhancement process."""
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'glm-4-flash')
    language = os.environ.get("LANGUAGE", 'Chinese')

    # --- Check for API Key ---
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found.", file=sys.stderr)
        print("Please set the OPENAI_API_KEY in your .env file or as an environment variable.", file=sys.stderr)
        sys.exit(1)


    # --- Load and prepare data ---
    try:
        data = []
        with open(args.data, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    if obj.get('summary'): # Ensure summary exists
                        data.append(obj)
                    else:
                        print(f"Skipping entry with no summary: {obj.get('id', 'Unknown ID')}", file=sys.stderr)
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode a line in {args.data}", file=sys.stderr)
    except FileNotFoundError:
        print(f"Error: Data file not found at {args.data}", file=sys.stderr)
        return

    # Remove duplicates
    seen_ids = set()
    unique_data = []
    for item in data:
        if item.get('id') not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)
    data = unique_data
    print(f"Loaded {len(data)} unique papers from: {args.data}", file=sys.stderr)

    # --- Set up LangChain ---
    llm = ChatZhipuAI(
        model=model_name,
        api_key=api_key, # Use the validated API key
        base_url=os.environ.get("OPENAI_API_BASE")
    )
    print(f'Connecting to model: {model_name}', file=sys.stderr)

    llm_with_tools = llm.bind_tools([Structure])
    output_parser = PydanticToolsParser(tools=[Structure])

    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    
    chain = prompt_template | llm_with_tools | output_parser

    # --- Process data with retries ---
    enhanced_data = []
    total_failures = 0

    for idx, d in enumerate(data):
        print(f"Processing {idx + 1}/{len(data)}: {d['id']}", file=sys.stderr)
        final_result = None
        
        for attempt in range(args.retries):
            try:
                # Invoke the model
                response_data_list = chain.invoke({
                    "language": language,
                    "content": d['summary']
                })

                if response_data_list:
                    # We only take the first tool call's result
                    response_raw = response_data_list[0]
                    result = response_raw.model_dump()

                    # Validate the response content
                    if is_response_valid(result):
                        final_result = result
                        print(f"  Success on attempt {attempt + 1}", file=sys.stderr)
                        break # Exit retry loop on success
                    else:
                        # Log the invalid data for debugging
                        print(f"  Attempt {attempt + 1} failed validation (incomplete data). Response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
                else:
                    print(f"  Attempt {attempt + 1} failed (model returned no structured data).", file=sys.stderr)

            except Exception as e:
                print(f"  Attempt {attempt + 1} failed with error: {e}", file=sys.stderr)
            
            # Wait before retrying
            if attempt < args.retries - 1:
                time.sleep(args.timeout)

        if final_result:
            d['AI'] = final_result
        else:
            total_failures += 1
            print(f"  Failed to process {d['id']} after {args.retries} attempts.", file=sys.stderr)
            d['AI'] = {
                "tldr": "Error: Failed to generate summary.",
                "motivation": None,
                "method": None,
                "result": None,
                "conclusion": None
            }
        enhanced_data.append(d)

    # --- Save results ---
    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d in enhanced_data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print("\n" + "="*20)
    print("Processing Complete.")
    print(f"Successfully processed: {len(enhanced_data) - total_failures}/{len(enhanced_data)}")
    print(f"Total failures: {total_failures}")
    print(f"Output file: {output_filename}")
    print("="*20)


if __name__ == "__main__":
    main()
