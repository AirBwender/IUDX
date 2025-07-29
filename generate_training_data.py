import os
import json

INPUT_DIR = "samples_for_finetuning"
OUTPUT_FILE = "finetune_data.jsonl"

ALLOWED_TYPES = [
    "iudx:Text",
    "iudx:Number",
    "iudx:Integer",
    "iudx:DateTime",
    "iudx:Point",
    "iudx:Boolean"
]

def extract_examples(jsonld_file):
    with open(jsonld_file) as f:
        data = json.load(f)

    sample = data.get("dataSample", {})
    descriptor = data.get("dataDescriptor", {})

    examples = []

    for key, val in sample.items():
        desc = descriptor.get(key, {})
        correct_type = desc.get("dataSchema", None)

        if correct_type and correct_type in ALLOWED_TYPES:
            prompt = f"""Field: "{key}"
Value: {json.dumps(val)}
Predict the most suitable IUDX dataSchema type from:
- iudx:Text
- iudx:Number
- iudx:Integer
- iudx:DateTime
- iudx:Point
- iudx:Boolean"""

            examples.append({
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": correct_type}
                ]
            })

    return examples

def main():
    all_data = []

    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".jsonld"):
            path = os.path.join(INPUT_DIR, filename)
            examples = extract_examples(path)
            all_data.extend(examples)

    with open(OUTPUT_FILE, "w") as f:
        for item in all_data:
            f.write(json.dumps(item) + "\n")

    print(f"[✓] Wrote {len(all_data)} training examples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
# This script generates training data for fine-tuning a model based on JSON-LD files.
# It extracts examples from the specified input directory and writes them to a JSONL file.