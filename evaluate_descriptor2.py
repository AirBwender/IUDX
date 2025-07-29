import json
from typing import List, Dict, Tuple
import joblib
from pydantic import BaseModel, ValidationError, field_validator
import pandas as pd

class FieldDescriptor(BaseModel):
    type: List[str]
    description: str
    dataSchema: str

    @field_validator("dataSchema")
    def validate_data_schema(cls, v):
        if not v.startswith("iudx:"):
            raise ValueError("dataSchema must start with 'iudx:'")
        return v


model_path = "iudx_random_forest.pkl"
vectorizer, clf = joblib.load(model_path)

def infer_type(key: str, value) -> str:
    try:
        X = pd.DataFrame([[key, str(value)]], columns=["field_name", "sample_value"])
        X_transformed = vectorizer.transform(X)
        return clf.predict(X_transformed)[0]
    except Exception as e:
        print(f"[WARN] Type inference failed: {e}")
        return "iudx:Text"





def flatten_geojson_feature(geojson: Dict) -> Dict:
    #one dictionary with all properties and geometry over here for simplicity.
    merged = {}
    merged.update(geojson.get("properties", {}))
    merged["geometry"] = geojson.get("geometry", {})
    if "filename" in geojson:
        merged["filename"] = geojson["filename"]
    return merged


NON_CRITICAL_FIELDS = {"filename"}  # everything else is treated as critical

def evaluate_descriptor(template_path: str, sample_input: Dict) -> Tuple[str, Dict]:
    with open(template_path) as f:
        full_metadata = json.load(f)
        descriptor = full_metadata.get("dataDescriptor", {})

    errors = []
    fixed_descriptor = descriptor.copy()

    for key, value in sample_input.items():
        expected_type = infer_type(key, value)

        if key not in descriptor:
            fixed_descriptor[key] = {
                "type": ["ValueDescriptor"],
                "description": "autofixed",
                "dataSchema": expected_type
            }
            if key in NON_CRITICAL_FIELDS:
                errors.append((key, f"non-critical: missing field, added with inferred type {expected_type}"))
            else:
                errors.append((key, f"CRITICAL: missing field, expected {expected_type}"))
        else:
            field = descriptor[key]
            try:
                fd = FieldDescriptor(**field)
                numeric_types = {"iudx:Number", "iudx:Integer"}
                if fd.dataSchema != expected_type:
                # Allow iudx:Integer wherever iudx:Number is inferred, and vice versa
                    if {fd.dataSchema, expected_type}.issubset(numeric_types):
                        continue  

                    if key in NON_CRITICAL_FIELDS:
                        fixed_descriptor[key]["dataSchema"] = expected_type
                        errors.append((key, f"non-critical: type mismatch, fixed to {expected_type}"))
                    else:
                        errors.append((key, f"CRITICAL: type mismatch ({fd.dataSchema} ≠ {expected_type})"))
            except ValidationError:
                if key in NON_CRITICAL_FIELDS:
                    fixed_descriptor[key] = {
                        "type": ["ValueDescriptor"],
                        "description": "autofixed",
                        "dataSchema": expected_type
                    }
                    errors.append((key, f"non-critical: invalid descriptor, autofixed to {expected_type}"))
                else:
                    errors.append((key, f"CRITICAL: invalid descriptor for {key}"))

    if "filename" in sample_input:
        name = sample_input["filename"]
        fixed_descriptor["dataDescriptorLabel"] = f"Data Descriptor for {name}"
        fixed_descriptor["description"] = f"Describes the data structure of the {name} dataset."

    has_critical_error = any("CRITICAL" in msg for _, msg in errors)
    status = "REJECTED" if has_critical_error else "ACCEPTED"

    # Print Validation Summary
    print("Validation Summary:")
    for field, msg in errors:
        print(f"  - {field}: {msg}")
    
    
    print("Status:", status)

    return status, fixed_descriptor



if __name__ == "__main__":
    with open("inputtemple.geojson") as geo:
        geojson = json.load(geo)

    flat_sample = flatten_geojson_feature(geojson)

    with open("myoutputtemple22.jsonld") as f:
        full_metadata = json.load(f)

    #evaluation
    output_status, fixed_descriptor = evaluate_descriptor("myoutputtemple22.jsonld", flat_sample)

    #updating the metadata with the fixed descriptor
    full_metadata["dataDescriptor"] = fixed_descriptor

    #writing the corrected full metadata
    with open("outputtemple2.jsonld", "w") as f:
        json.dump(full_metadata, f, indent=2)

#rdfs catalogue iudx data modelling.
#prompt in text file, full jsonld output.
#provide examples in the prompt.
#no if else in the validator.

#no filename in jsonld output.
# read and understand different data types.
#prompt for all sorts of data types, timeseries, etc.