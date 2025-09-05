import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def generate_embedding(text: str) -> list[float]:
    resp = client.embeddings.create(
        model = "text-embedding-3-small", 
        input=text
    )
    return resp.data[0].embedding