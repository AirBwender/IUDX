import json
from typing import List, Dict, Tuple
from pydantic import BaseModel, ValidationError, field_validator
from groq import Groq
import os
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def infer_type_llm(key: str, value) -> str:
    prompt = f"""
You are an expert in semantic data modeling for everything.

Given a field name and a sample value, predict the most suitable IUDX dataSchema type.

Use only the following types:
- iudx:Text
- iudx:Number
- iudx:Integer
- iudx:Boolean
- iudx:Point

Respond with **only** the type like this: `iudx:Text` (no explanations).

Example 1:
Field: "Name", Value: "Temple of Kali"
Answer: iudx:Text

Example 2:
Field: "Latitude", Value: 28.6139
Answer: iudx:Number

Example 3:
Field: "geometry", Value: {{ "type": "Point", "coordinates": [76.4, 29.1] }}
Answer: iudx:Point

Respond ONLY with the type, like this: iudx:Text (no 'Answer:' or quotes).
Field: "{key}"
Value: {json.dumps(value)}
""".strip()

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        raw_output = response.choices[0].message.content.strip()
        type_str = raw_output.split()[0] if "iudx:" in raw_output else "iudx:Text"
        return type_str
    except Exception as e:
        print(f"[WARN] LLM type inference failed for `{key}`: {e}")
        return "iudx:Text"

class FieldDescriptor(BaseModel):
    type: List[str]
    description: str
    dataSchema: str

    @field_validator("dataSchema")
    def validate_data_schema(cls, v):
        if not v.startswith("iudx:"):
            raise ValueError("dataSchema must start with 'iudx:'")
        return v

def flatten_geojson_feature(geojson: Dict) -> Dict:
    merged = {}
    merged.update(geojson.get("properties", {}))
    merged["geometry"] = geojson.get("geometry", {})
    if "filename" in geojson:
        merged["filename"] = geojson["filename"]
    return merged

NON_CRITICAL_FIELDS = {"filename"}

def evaluate_descriptor(template_path: str, sample_input: Dict) -> Tuple[str, Dict]:
    with open(template_path) as f:
        full_metadata = json.load(f)
        descriptor = full_metadata.get("dataDescriptor", {})

    errors = []
    fixed_descriptor = descriptor.copy()

    for key, value in sample_input.items():
        expected_type = infer_type_llm(key, value)

        # Refine numeric type based on value
        if expected_type in {"iudx:Number", "iudx:Integer"}:
            if isinstance(value, (int, float)):
                expected_type = "iudx:Number" if isinstance(value, float) or (isinstance(value, str) and "." in str(value)) else "iudx:Integer"

        if key not in descriptor:
            fixed_descriptor[key] = {
                "type": ["ValueDescriptor"],
                "description": "autofixed",
                "dataSchema": expected_type
            }
            errors.append((key, f"{'non-critical' if key in NON_CRITICAL_FIELDS else 'CRITICAL'}: missing field, added with inferred type {expected_type}"))
        else:
            field = descriptor[key]
            try:
                fd = FieldDescriptor(**field)
                numeric_types = {"iudx:Number", "iudx:Integer"}
                if fd.dataSchema != expected_type:
                    # Allow iudx:Number as a valid type for integers (superset)
                    if expected_type == "iudx:Integer" and fd.dataSchema == "iudx:Number":
                        continue
                    # Flag mismatch if expected type is Number but descriptor is Integer
                    if expected_type == "iudx:Number" and fd.dataSchema == "iudx:Integer":
                        errors.append((key, f"{'non-critical' if key in NON_CRITICAL_FIELDS else 'CRITICAL'}: type mismatch (expected {expected_type}, found {fd.dataSchema})"))
                        fixed_descriptor[key]["dataSchema"] = expected_type
                    elif fd.dataSchema != expected_type and not {fd.dataSchema, expected_type}.issubset(numeric_types):
                        errors.append((key, f"{'non-critical' if key in NON_CRITICAL_FIELDS else 'CRITICAL'}: type mismatch ({fd.dataSchema} ≠ {expected_type})"))
                        fixed_descriptor[key]["dataSchema"] = expected_type
            except ValidationError:
                fixed_descriptor[key] = {
                    "type": ["ValueDescriptor"],
                    "description": "autofixed",
                    "dataSchema": expected_type
                }
                errors.append((key, f"{'non-critical' if key in NON_CRITICAL_FIELDS else 'CRITICAL'}: invalid descriptor, autofixed to {expected_type}"))

    if "filename" in sample_input:
        name = sample_input["filename"]
        fixed_descriptor["dataDescriptorLabel"] = f"Data Descriptor for {name}"
        fixed_descriptor["description"] = f"Describes the data structure of the {name} dataset."

    status = "REJECTED" if any("CRITICAL" in msg for _, msg in errors) else "ACCEPTED"

    print("Validation Summary:")
    for field, msg in errors:
        print(f"  - {field}: {msg}")
    print("Status:", status)

    return status, fixed_descriptor

if __name__ == "__main__":
    with open("input21.json") as geo:
        geojson = json.load(geo)

    flat_sample = flatten_geojson_feature(geojson)

    with open("myoutputtemple22.jsonld") as f:
        full_metadata = json.load(f)

    output_status, fixed_descriptor = evaluate_descriptor("output21.jsonld", flat_sample)
    full_metadata["dataDescriptor"] = fixed_descriptor

    with open("outputtemple2.jsonld", "w") as f:
        json.dump(full_metadata, f, indent=2)