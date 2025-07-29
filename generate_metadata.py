import os
import json
import uuid
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Load the prompt template
with open("prompt_template.txt", "r") as f:
    base_prompt = f.read()

# Load your input GeoJSON
with open("inputmosque1.geojson", "r") as f:
    geojson_input = json.load(f)

# Inject input GeoJSON into prompt
prompt = base_prompt.replace("{geojson_input}", json.dumps(geojson_input, indent=2))

# Send to LLM
response = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that outputs structured JSON-LD metadata following the IUDX schema."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.2
)

# Extract the generated JSON-LD text
response_text = response.choices[0].message.content.strip()

# Try parsing the result to validate
try:
    jsonld_output = json.loads(response_text)
except json.JSONDecodeError:
    print("LLM output is not valid JSON.")
    print(response_text)
    exit(1)

# Save to file
with open("myoutputmosque2.jsonld", "w") as f:
    json.dump(jsonld_output, f, indent=2)

print("JSON-LD metadata generated and saved to myoutputmosque2.jsonld")
