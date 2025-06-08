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
    Validation: Checks that all fields defined in the Structure model exist and are not empty.
    """
    if not result:
        return False
    
    # Get all fields defined in the Structure model
    all_fields = Structure.model_fields.keys()

    for field in all_fields:
        value = result.get(field)
        # If any field is None or an empty string, validation fails
        if value is None or not str(value).strip():
            return False
            
    # All fields are present and valid
    return True

def main():
    """Main function to run the enhancement process."""
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'gemini-2.0-flash')
    language = os.environ.get("LANGUAGE", 'Chinese') 

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
        google_api_key=api_key
    )
    print(f'Connecting to model: {model_name}', file=sys.stderr)

    llm_with_tools = llm.bind_tools([Structure])
    output_parser = PydanticToolsParser(tools=[Structure])
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template)
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
                        print(f"  Attempt {attempt + 1} failed validation (empty fields). Response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
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
                "tldr": "Error: Failed to generate content.", "motivation": None, "method": None,
                "result": None, "conclusion": None, "translation": None, "summary": None
            }
        else:
            d['AI'] = final_result
            
        enhanced_data.append(d)
        time.sleep(2)

    output_filename = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    with open(output_filename, "w", encoding="utf-8") as f:
        for d_item in enhanced_data:
            f.write(json.dumps(d_item, ensure_ascii=False) + "\n")

    print(f"\nProcessing complete. Successfully processed: {len(enhanced_data) - total_failures}/{len(enhanced_data)}. Output file: {output_filename}")

if __name__ == "__main__":
    main()
# This script enhances arXiv data with AI-generated summaries using Google Generative AI.
# It reads a JSONL file, processes each paper, and outputs the enhanced data to a new JSONL file.
# It includes error handling, retries, and validation of the AI-generated content.
# The script is designed to be run from the command line with specified arguments.
# It requires a valid GOOGLE_API_KEY in the environment or .env file.
# The output is structured according to the Structure model defined in the structure module.
# The script uses LangChain for prompt management and tool integration.
# The model used can be configured via the MODEL_NAME environment variable.
# The language for the AI-generated content can be set via the LANGUAGE environment variable.
# The script ensures that all required fields in the AI-generated content are present and valid.
# It also handles unique IDs to avoid processing duplicates.
# The script is robust against common errors such as file not found or JSON decoding issues.
# It provides detailed logging to stderr for monitoring the processing status.
# The script is modular and can be easily extended or modified for different use cases.
# It is designed to be efficient, processing each paper in sequence with a configurable retry mechanism.
# The script is intended for use in enhancing academic papers with AI-generated summaries,
# making it a valuable tool for researchers and developers working with arXiv data.
# The output file is named based on the input file, with a suffix indicating it has been enhanced with AI content.
# The script is compatible with Python 3.7 and above, leveraging modern Python features.
# It is recommended to run the script in a virtual environment with the required dependencies installed.
# The script can be executed directly from the command line, making it user-friendly for quick enhancements.
# The script is part of a larger project focused on leveraging AI for academic research,
# and can be integrated with other components for a complete workflow.
# The script is open-source and can be modified or redistributed under the terms of the MIT License.
# The script is designed to be run in a controlled environment with access to the necessary API keys and dependencies. 