import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


# ✅ RULE-BASED INTENT (FAST + RELIABLE)
def has_order_id(text):
    import re
    return bool(re.search(r"\b\d{5,}\b", text))


def detect_simple_intent(email_text):
    text = email_text.lower().strip()

    gratitude_keywords = [
        "thanks", "thank you", "thx", "appreciate",
        "got it", "noted", "ok", "okay", "received"
    ]

    # ✅ CRITICAL FIX: If order ID exists → NOT gratitude
    if has_order_id(text):
        return None

    # ✅ Only short messages should be treated as gratitude
    if len(text.split()) <= 5:
        for word in gratitude_keywords:
            if word in text:
                return "gratitude"

    return None


# ✅ LLM CLASSIFIER (IMPROVED)
def classify_intent(email_text):
    simple = detect_simple_intent(email_text)
    if simple:
        return simple

    prompt = f"""
Classify this email into ONE of these categories:

refund, return, exchange, complaint, inquiry, gratitude, other

Rules:
- If user is thanking → gratitude
- If user acknowledges → gratitude
- If asking question → inquiry
- If complaining → complaint
- If unclear → other

Email:
{email_text}

Answer ONLY one word.
"""

    try:
        res = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )

        return res.content[0].text.strip().lower()

    except Exception as e:
        print("Classifier error:", e)
        return "other"
    
