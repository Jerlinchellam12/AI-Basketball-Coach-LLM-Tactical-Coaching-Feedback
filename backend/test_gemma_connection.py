"""One-off script to confirm Google AI Studio access to Gemma works before building llm_feedback.py."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemma-4-31b-it"
API_KEY = os.environ["GOOGLE_API_KEY"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

response = requests.post(
    URL,
    headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
    json={"contents": [{"parts": [{"text": "Reply with exactly: Gemma connection OK"}]}]},
)

print(response.status_code)
print(response.text)
