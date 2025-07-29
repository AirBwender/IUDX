from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

jsonld_data = """
{
  "@context": "http://schema.org",
  "@type": "Product",
  "name": "GroqCard AI Accelerator",
  "brand": "Groq",
  "description": "High-performance AI accelerator for data centers",
  "offers": {
    "@type": "Offer",
    "price": "499.99",
    "priceCurrency": "USD",
    "availability": "http://schema.org/InStock"
  }
}
"""

messages = [
    {
        "role": "system",
        "content": "You are a tool that summarizes JSON-LD product metadata into a single sentence description for product listings."
    },
    {
        "role": "user",
        "content": f"Here is the JSON-LD:\n{jsonld_data}\n\nWrite a short description for it."
    }
]

chat_completion = client.chat.completions.create(
    messages=messages,
    model="gemma2-9b-it",
    temperature=0
)

print(chat_completion.choices[0].message.content)
