import json
import re
from typing import Literal
from pydantic import BaseModel, ValidationError, validator

allowed_schemas = ["iudx:Text", "iudx:Number", "iudx:Point"]

class FieldDescriptor(BaseModel):
    type: list[Literal["ValueDescriptor"]] = ["ValueDescriptor"]
    description: str
    dataSchema: str

    @validator("dataSchema")
    def check_data_schema(cls, value):
        if value not in allowed_schemas:
            raise ValueError(f"invalid dataSchema: {value}")
        return value

def infer_data_schema(key: str, value):
    if isinstance(value, str) and re.fullmatch(r"\d+", value):
        return "iudx:Number"
    if isinstance(value, list) and len(value) == 2 and all(isinstance(x, float) for x in value):
        return "iudx:Point"
    return "iudx:Text"

def is_description_apt(key: str, description: str) -> bool:
    return key.lower().replace(".", "") in description.lower() or key.lower() in description.lower()

def evaluate_descriptor(descriptor_path: str, json_sample: dict):
    with open(descriptor_path) as f:
        descriptor = json.load(f)

    result = {}

    for key, value in descriptor.items():
        if key in ["@context", "type", "dataDescriptorLabel", "description"]:
            continue

        field = descriptor[key]
        field_result = {"status": "Accepted", "reason": None}

        try:
            FieldDescriptor(**field)
        except ValidationError as e:
            field_result["status"] = "Rejected"
            field_result["reason"] = str(e)
            result[key] = field_result
            continue

        sample_value = json_sample.get("properties", {}).get(key)
        if sample_value:
            inferred = infer_data_schema(key, sample_value)
            if inferred != field["dataSchema"]:
                field_result["status"] = "Rejected"
                field_result["reason"] = f"expected {inferred} but got {field['dataSchema']}"
                field["dataSchema"] = inferred
                field_result["autocorrected"] = True

        if not is_description_apt(key, field["description"]):
            field_result["status"] = "Rejected"
            field_result["reason"] = "description does not match key semantics"

        result[key] = field_result

    return result, descriptor

if __name__ == "__main__":
    with open("basicjsonsnippet.json") as f:
        sample = json.load(f)

    output, fixed_descriptor = evaluate_descriptor("generated_descriptor.json", sample)

    print("validation result:")
    for k, v in output.items():
        print(f"{k}: {v}")

    with open("corrected_descriptor.json", "w") as f:
        json.dump(fixed_descriptor, f, indent=2)
