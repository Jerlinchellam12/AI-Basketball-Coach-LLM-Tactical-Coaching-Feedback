"""One-off script confirming Groq API access, using llama-3.1-8b-instant.

Groq dropped Gemma support entirely (see PROJECT.md LLM Strategy) - this is
kept only for the optional secondary-model stretch comparison, not the
primary Gemma pipeline (see test_gemma_connection.py for that).
"""
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Reply with exactly: Groq connection OK"}],
)

print(response.choices[0].message.content)
