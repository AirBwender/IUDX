import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load your basic input JSON
with open("inputtemple.geojson", "r") as f:
    basic_data = json.load(f)

# Prepare prompt
prompt = f"""
You are a metadata assistant converting GeoJSON into IUDX-compatible JSON-LD metadata.

Given this GeoJSON Feature:

{json.dumps(basic_data, indent=2)}

Your task is to generate **only the "dataDescriptor"** block, with the following structure:

- The outer object must have:
  - "@context": "https://voc.iudx.org.in/"
  - "type": ["iudx:DataDescriptor"]
  - "dataDescriptorLabel": A human-readable title like "Data Descriptor for Location of Temple (OSM 50K), Sonipat, Haryana"
  - "description": A sentence describing the structure of the dataset

- For each property in `properties`, use:
  "<property_name>": {{
    "type": ["ValueDescriptor"],
    "description": A short phrase describing the meaning of the property,
    "dataSchema": Choose from "iudx:Text", "iudx:Number", "iudx:Integer", etc.
  }}

- Include "geometry" as a separate key with:
  "geometry": {{
    "type": ["ValueDescriptor"],
    "description": "Geographical representation corresponding to this observation.",
    "dataSchema": "iudx:Point"
  }}

Use the exact property key names from the GeoJSON and do not wrap fields inside a list like `hasDescriptor`.

Return only the valid "dataDescriptor" JSON block.
"""

response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "system", "content": "You are a JSON-LD generator for IUDX metadata."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.2
)

raw_output = response.choices[0].message.content.strip()

# Simple extraction of first JSON object
start = raw_output.find("{")
end = raw_output.rfind("}") + 1

if start == -1 or end == -1:
    raise ValueError("No valid JSON object found in model output.")

clean_json_str = raw_output[start:end]
parsed_descriptor = json.loads(clean_json_str)

# Save
with open("myoutputtemple.jsonld", "w") as f:
    json.dump({"dataDescriptor": parsed_descriptor}, f, indent=2)

print("Cleaned descriptor saved to 'myoutputtemple.jsonld'")