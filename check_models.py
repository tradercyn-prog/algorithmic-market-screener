import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("--- AUTHORIZED MODELS FOR THIS API KEY ---")
    for m in client.models.list():
        print(m.name)
except Exception as e:
    print(f"Error connecting to API: {e}")