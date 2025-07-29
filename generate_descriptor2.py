import os
import json
import uuid
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load input GeoJSON
with open("inputtemple.geojson", "r") as f:
    basic_data = json.load(f)

# Load prompt template
with open("prompt_template.txt", "r") as f:
    template = f.read()

# Replace placeholder
prompt = template.replace("{geojson_input}", json.dumps(basic_data, indent=2))

# Query the model
response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "system", "content": "You are a JSON-LD generator for IUDX metadata."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.2
)

raw_output = response.choices[0].message.content.strip()

print("==== RAW LLM OUTPUT START ====")
print(repr(raw_output))
print("==== RAW LLM OUTPUT END ====")


# Extract and clean JSON block
start = raw_output.find("{")
end = raw_output.rfind("}") + 1
if start == -1 or end == -1:
    raise ValueError("No valid JSON object found in model output.")

clean_json_str = raw_output[start:end]
parsed_metadata = json.loads(clean_json_str)

# Add UUID as `id`
parsed_metadata["id"] = str(uuid.uuid4())

# Leave provider fields blank
parsed_metadata["provider"] = ""
parsed_metadata["resourceServer"] = ""
parsed_metadata["resourceGroup"] = ""

# Save output
with open("myoutputtemple2.jsonld", "w") as f:
    json.dump(parsed_metadata, f, indent=2)

print("Metadata with descriptor saved to 'myoutputtemple2.jsonld'")
