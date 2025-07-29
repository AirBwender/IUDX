import os
import json
import uuid
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import argparse
import re

# Load environment variables
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def detect_resource_type(json_input, filename=None):
    """
    Heuristically detect the resource type based on input JSON or filename.
    Extend this function as new dataset types are added.
    """
    # Heuristic: check for keys or filename patterns
    if filename:
        fname = os.path.basename(filename).lower()
        if "geojson" in fname:
            return "GeoJSON"
        if "emergency" in fname or "ambulance" in fname:
            return "EmergencyVehicle"
        if "env" in fname or "aqm" in fname:
            return "EnvAQM"
    # Check keys in JSON
    if "geometry" in json_input or ("type" in json_input and json_input["type"] == "Feature"):
        return "GeoJSON"
    if "emergencyVehicleType" in json_input:
        return "EmergencyVehicle"
    if any(k in json_input for k in ["airQualityIndex", "pm10", "pm2p5", "co", "no2", "co2"]):
        return "EnvAQM"
    # Fallback
    return "GeoJSON"  # Default to GeoJSON if unsure

def build_prompt(json_input, resource_type, **kwargs):
    """
    Build the prompt string for the LLM based on resource type and input.
    """
    if resource_type == "GeoJSON":
        with open("prompt_template_geojson.txt", "r") as f:
            template = f.read()
        prompt = template.replace("{geojson_input}", json.dumps(json_input, indent=2))
    elif resource_type == "EmergencyVehicle":
        with open("prompt_template_emergency_vehicle.txt", "r") as f:
            template = f.read()
        city = kwargs.get("city", "")
        polygon = kwargs.get("polygon", [])
        url = f"[invalid url, do not cite]/{city.lower()}-emergency-vehicles-ambulance-live.json"
        prompt = template.replace("{city}", city).replace("{polygon}", json.dumps(polygon)).replace("{url}", url).replace("{json_input}", json.dumps(json_input, indent=2))
    elif resource_type == "EnvAQM":
        with open("prompt_template_env_aqm.txt", "r") as f:
            template = f.read()
        city = kwargs.get("city", "")
        polygon = kwargs.get("polygon", [])
        url = f"[invalid url, do not cite]/{city.lower()}-env-aqm-info.json"
        prompt = template.replace("{city}", city).replace("{polygon}", json.dumps(polygon)).replace("{url}", url).replace("{json_input}", json.dumps(json_input, indent=2))
    else:
        raise ValueError(f"Unknown resource_type: {resource_type}")
    return prompt

def generate_metadata(json_input, resource_type, prompt):
    """
    Generate IUDX-compliant JSON-LD metadata for the given input JSON and resource type.
    """
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
    # Extract and clean JSON block
    start = raw_output.find("{")
    end = raw_output.rfind("}") + 1
    if start == -1 or end == -1:
        raise ValueError("No valid JSON object found in model output.")
    clean_json_str = raw_output[start:end]
    parsed_metadata = json.loads(clean_json_str)
    # Add UUID as `id`
    parsed_metadata["id"] = str(uuid.uuid4())
    # Set itemCreatedAt to current datetime in IST
    parsed_metadata["itemCreatedAt"] = datetime.now().isoformat() + "+0530"
    # Ensure database-retrieved fields are blank
    parsed_metadata["provider"] = ""
    parsed_metadata["resourceServer"] = ""
    parsed_metadata["resourceGroup"] = ""
    return parsed_metadata

def main():
    parser = argparse.ArgumentParser(description="Generate IUDX-compliant JSON-LD metadata for a given input fileN.json, outputting output_fileN.jsonld.")
    parser.add_argument("input_file", help="Path to the input JSON file (fileN.json)")
    parser.add_argument("--city", help="City name (for EmergencyVehicle/EnvAQM)")
    parser.add_argument("--polygon", help="Polygon coordinates as JSON string (for EmergencyVehicle/EnvAQM)")
    args = parser.parse_args()

    input_file = args.input_file
    match = re.match(r"file(\d+)\.json", os.path.basename(input_file))
    if not match:
        raise ValueError("Input file must be named as fileN.json (e.g., file8.json)")
    file_num = match.group(1)
    output_file = f"output_file{file_num}.jsonld"
    prompt_file = f"prompt_file{file_num}.txt"

    with open(input_file, "r") as f:
        json_input = json.load(f)

    # Heuristically detect resource type
    resource_type = detect_resource_type(json_input, filename=input_file)

    # Parse polygon if provided
    polygon = None
    if args.polygon:
        try:
            polygon = json.loads(args.polygon)
        except Exception:
            raise ValueError("Invalid polygon JSON string.")
    # City
    city = args.city or ""

    # Build prompt
    prompt = build_prompt(json_input, resource_type, city=city, polygon=polygon)
    with open(prompt_file, "w") as pf:
        pf.write(prompt)

    # Generate metadata
    metadata = generate_metadata(json_input, resource_type, prompt)

    # Output in the required structure
    output_json = {
        "type": "urn:dx:cat:Success",
        "title": "Success",
        "totalHits": 1,
        "results": [metadata],
        "detail": "Success: Item generated Successfully"
    }
    with open(output_file, "w") as f:
        json.dump(output_json, f, indent=2)
    print(f"Output written to {output_file}\nPrompt saved to {prompt_file}")

if __name__ == "__main__":
    main()