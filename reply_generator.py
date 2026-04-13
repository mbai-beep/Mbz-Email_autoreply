import anthropic
from dotenv import load_dotenv
import os
import re
from config import STRICT_REFUND_POLICY

# ✅ Load env
load_dotenv()

# ✅ Get API key
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# ✅ Init client
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


# ✅ Detect order ID
def has_order_id(text):
    return bool(re.search(r"\b\d{5,}\b", text))


# ✅ Detect gratitude (FAST PATH — NO LLM)
def is_gratitude(text):
    text = text.lower()
    keywords = [
        "thanks", "thank you", "thx", "appreciate",
        "got it", "noted", "ok", "okay", "received"
    ]
    return any(word in text for word in keywords)


# ✅ MAIN REPLY FUNCTION
def generate_reply(intent, email_text):

    # 🔥 1. HANDLE GRATITUDE (CRITICAL FIX)
    if intent == "gratitude" and not has_order_id(email_text):
        return """You're very welcome! 😊

We're glad we could assist you. If you need anything else, feel free to reach out anytime.

Have a great day ahead!"""

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

    # ✅ Order ID logic
    if not has_order_id(email_text):
        order_instruction = "Customer has NOT provided order ID → politely ask for it."
    else:
        order_instruction = "Customer HAS provided order ID → do NOT ask again."

    # ✅ Intent-specific guidance (NEW 🔥)
    intent_instruction = ""

    if intent == "refund":
        intent_instruction = "User is asking about refund status or request."

    elif intent == "return":
        intent_instruction = "User wants to return a product."

    elif intent == "exchange":
        intent_instruction = "User wants to exchange a product."

    elif intent == "complaint":
        intent_instruction = "User is unhappy → show empathy and reassurance."

    elif intent == "inquiry":
        intent_instruction = "User is asking a general question."

    else:
        intent_instruction = "General customer support response."

    # ✅ FINAL PROMPT
    prompt = f"""
You are a professional customer support agent.

{safety_rules}

Intent: {intent}
{intent_instruction}

{order_instruction}

Customer email:
{email_text}

Write a SHORT, clear and helpful reply.
"""

    try:
        res = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        return res.content[0].text.strip()

    except Exception as e:
        print(f"Claude API error: {e}")

        # ✅ Fallback response
        return "Thank you for reaching out. We will review your request and get back to you shortly."