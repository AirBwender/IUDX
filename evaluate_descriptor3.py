import json
from typing import List, Dict, Tuple
from pydantic import BaseModel, ValidationError, field_validator


class FieldDescriptor(BaseModel):
    type: List[str]
    description: str
    dataSchema: str

    @field_validator("dataSchema")
    def validate_data_schema(cls, v):
        if not v.startswith("iudx:"):
            raise ValueError("dataSchema must start with 'iudx:'")
        return v


def infer_type(value):
    if isinstance(value, int):
        return "iudx:Integer"
    elif isinstance(value, float):
        return "iudx:Number"
    elif isinstance(value, dict) and value.get("type") == "Point":
        return "iudx:Point"
    elif isinstance(value, str):
        # Reject numeric-only strings
        try:
            int(value)
            return "iudx:Integer"
        except ValueError:
            try:
                float(value)
                return "iudx:Number"
            except ValueError:
                pass
        # Accept only if there are letters in the string.
        if any(c.isalpha() for c in value):
            return "iudx:Text"
    # fallback
    return None


def flatten_geojson_feature(geojson: Dict) -> Dict:
    merged = {}
    merged.update(geojson.get("properties", {}))
    merged["geometry"] = geojson.get("geometry", {})
    if "filename" in geojson:
        merged["filename"] = geojson["filename"]
    return merged


def evaluate_descriptor(template_path: str, sample_input: Dict) -> Tuple[str, Dict]:
    with open(template_path) as f:
        descriptor = json.load(f)

    errors = []
    fixed_descriptor = descriptor.copy()
    fixed_descriptor.setdefault("properties", {})

    for key, value in sample_input.items():
        expected_type = infer_type(value)

        if key not in descriptor.get("properties", {}):
            # Field missing, add it
            fixed_descriptor["properties"][key] = {
                "type": ["ValueDescriptor"],
                "description": "autofixed",
                "dataSchema": expected_type
            }
            errors.append((key, f"missing field, added with inferred type {expected_type}"))

        else:
            field = descriptor["properties"][key]
            try:
                fd = FieldDescriptor(**field)
                # Fix only if type is wrong
                if fd.dataSchema != expected_type:
                    fixed_descriptor["properties"][key]["dataSchema"] = expected_type
                    errors.append((key, f"type mismatch, fixed to {expected_type}"))
            except ValidationError:
                # Keep existing description if it's meaningful
                desc = field.get("description", "").lower()
                if "autofixed" in desc or not any(c.isalpha() for c in desc):
                    description = "autofixed"
                else:
                    description = field.get("description", "autofixed")

                fixed_descriptor["properties"][key] = {
                    "type": ["ValueDescriptor"],
                    "description": description,
                    "dataSchema": expected_type
                }
                errors.append((key, f"invalid descriptor, fixed to {expected_type}"))

    if "filename" in sample_input:
        name = sample_input["filename"]
        fixed_descriptor["dataDescriptorLabel"] = f"Data Descriptor for {name}"
        fixed_descriptor["description"] = f"Describes the data structure of the {name} dataset."

    status = "REJECTED" if errors else "ACCEPTED"
    return status, fixed_descriptor


if __name__ == "__main__":
    with open("inputtemple.geojson") as geo:
        geojson = json.load(geo)

    flat_sample = flatten_geojson_feature(geojson)
    output_status, fixed_data = evaluate_descriptor("outputtemple.jsonld", flat_sample)

    with open("outputtemple2.jsonld", "w") as f:
        json.dump(fixed_data, f, indent=2)

    print("Status:", output_status)

#prmpt to text