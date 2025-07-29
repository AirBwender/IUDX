import os
import json
import re
from pydantic import BaseModel, Field, ValidationError
from typing import Literal, Union
from groq import Groq
from dotenv import load_dotenv
import re

load_dotenv()

from typing import Union, List

class GeoCoordinates(BaseModel):
    type: Literal["GeoCoordinates"] = Field(..., alias="@type") 
    latitude: float
    longitude: float

class Location(BaseModel):
    type: Literal["Place"] = Field(..., alias="@type")
    name: Union[str, None] = None
    geo: Union[GeoCoordinates, None] = None

class JsonLdEntity(BaseModel):
    context: Union[str, dict] = Field(..., alias="@context")
    id: str = Field(..., alias="@id")
    type: Union[str, List[str]] = Field(..., alias="@type")
    name: str
    location: Union[Location, GeoCoordinates]  




def extract_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip("`\n ")
    match = re.search(r"(\[.*\])", text, re.DOTALL)
    return match.group(1) if match else text

with open("Museums 2021.geojson", "r") as f:
    geojson = json.load(f)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

prompt = f"""
Convert the following GeoJSON into JSON-LD format using schema.org vocabulary.

GeoJSON:
{json.dumps(geojson, indent=2)}

Make sure the output has:
- @context
- @id
- @type
- name
- location with Place and GeoCoordinates types

Respond with only a valid JSON list of entities.
"""

chat_completion = client.chat.completions.create(
    model="llama3-70b-8192",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that converts GeoJSON to JSON-LD"},
        {"role": "user", "content": prompt},
    ],
    temperature=0.2,
)

raw = chat_completion.choices[0].message.content
try:
    cleaned = extract_json(raw)
    jsonld_output = json.loads(cleaned)
except json.JSONDecodeError:
    print("LLM output is not valid JSON.")
    print(raw)
    exit()

with open("output.jsonld", "w") as f:
    json.dump(jsonld_output, f, indent=2)


print("Validating jsonld entities:\n")
valid_count = 0
for i, entity in enumerate(jsonld_output):
    try:
        validated = JsonLdEntity(**entity)
        print(f"Valid entity {i+1}: {validated.id}")
        valid_count += 1
    except ValidationError as e:
        print(f"Entity {i+1} failed:\n{e}\n")

print(f"\n {valid_count}/{len(jsonld_output)} entities validated.")
