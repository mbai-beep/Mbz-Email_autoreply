import os
import anthropic
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get API key from environment
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Initialize client with env key
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


def classify_intent(email_text):
    prompt = f"""
Classify this email into:
refund, return, exchange, other

Email:
{email_text}

Answer ONLY one word.
"""

    res = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )

    return res.content[0].text.strip().lower()