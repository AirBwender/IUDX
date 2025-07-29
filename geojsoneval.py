# geojson eval:
# sample geojson dataset, values/outputs jsonld. structure a prompt perfect description dataschema no data should be lost like coordinates and stuff.

from dotenv import load_dotenv
import os 
from groq import Groq
load_dotenv() 

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)