import anthropic
from dotenv import load_dotenv
import os
from config import CLAUDE_API_KEY, STRICT_REFUND_POLICY

# Load variables from .env file
load_dotenv()

# Get API key from environment
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

def generate_reply(intent, email_text):
    safety_rules = """
CRITICAL RULES:
- NEVER confirm a refund is approved
- NEVER say "your refund is processed"
- ALWAYS say "we will review" or "we will check"
- If order ID is missing → ask for it
- Be polite and professional
- Do NOT include Subject line
- Be concise and clear
- Be polite and helpful
- Ask only necessary information
- No long paragraphs
"""

    if STRICT_REFUND_POLICY and intent == "refund":
        safety_rules += "\n- Refunds must be verified before approval"

    prompt = f"""
You are a customer support agent.

{safety_rules}

Intent: {intent}

Customer email:
{body}

Write a SHORT and PROFESSIONAL reply (max 4–5 lines).
"""

    res = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}]
    )

    return res.content[0].text.strip()
