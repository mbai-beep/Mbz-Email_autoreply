import anthropic
from dotenv import load_dotenv
import os
import re
from config import STRICT_REFUND_POLICY

# ✅ Load env
load_dotenv()

# ✅ Get API key
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# ✅ Init client (FIXED)
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


# ✅ Detect order ID (same logic as alert_manager)
def has_order_id(text):
    return bool(re.search(r"\b\d{5,}\b", text))


def generate_reply(intent, email_text):
    # ✅ Safety + tone rules
    safety_rules = """
CRITICAL RULES:
- NEVER confirm a refund is approved
- NEVER say "your refund is processed"
- ALWAYS say "we will review" or "we will check"
- Be polite, professional, and concise
- Do NOT include Subject line
- Keep response within 4-5 lines
- Ask only necessary information
"""

    # ✅ Refund strictness
    if STRICT_REFUND_POLICY and intent == "refund":
        safety_rules += "\n- Refunds must be verified before approval"

    # ✅ Smart behavior: ask order ID ONLY if missing
    order_instruction = ""
    if not has_order_id(email_text):
        order_instruction = "Customer has NOT provided order ID → ask for it."
    else:
        order_instruction = "Customer HAS provided order ID → do NOT ask again."

    prompt = f"""
You are a professional customer support agent.

{safety_rules}

Intent: {intent}

{order_instruction}

Customer email:
{email_text}

Write a SHORT, clear and helpful reply.
"""

    try:
        res = client.messages.create(
            model="claude-haiku-4-5-20251001",  # ✅ stable model name
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        return res.content[0].text.strip()

    except Exception as e:
        print(f"Claude API error: {e}")

        # ✅ Fallback response
        return "Thank you for reaching out. We will review your request and get back to you shortly."