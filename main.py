import time
import json
from gmail_client import *
from classifier import classify_intent, detect_simple_intent
from reply_generator import generate_reply
from templates import TEMPLATES
from config import ALLOWED_INTENTS
from logger import setup_logger
from auth import get_gmail_service
from gmail_client import add_label_to_email, get_or_create_label
from gmail_client import is_agent
from alert_manager import mark_agent_replied

from alert_manager import (
    update_thread_on_reply,
    check_escalations
)

logger = setup_logger()

PROCESSED_FILE = "processed.json"


def load_processed():
    try:
        with open(PROCESSED_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f)


# ✅ NEW: BUILD THREAD CONTEXT (FIXES WRONG INTENT)
def build_thread_context(service, thread_id):
    try:
        messages = get_thread_messages(service, thread_id)

        conversation = ""
        for msg in messages[-3:]:  # last 3 emails only
            payload = msg.get("payload", {})
            body = extract_body(payload)

            if body:
                conversation += f"\n---\n{body}"

        return conversation.strip()

    except Exception as e:
        logger.error(f"Thread context error: {e}")
        return ""


def main():
    logger.info("Email bot started")

    service = get_gmail_service()

    AUTO_LABEL = get_or_create_label(service, "AutoReplied")
    ESCALATED_L1 = get_or_create_label(service, "Escalated_L1")
    ESCALATED_L2 = get_or_create_label(service, "Escalated_L2")

    processed = load_processed()

    while True:
        try:
            messages = fetch_unread_emails(service)
            logger.info(f"Fetched {len(messages)} messages")

            for msg in messages:
                msg_id = msg.get("id")

                if not msg_id or msg_id in processed:
                    continue

                subject, body, thread_id, sender, message_id = get_email_content(service, msg_id)

                # ✅ 1. AGENT REPLY HANDLING
                if is_agent(sender):
                    logger.info(f"Agent replied on thread {thread_id}")

                    mark_agent_replied(thread_id)
                    mark_as_read(service, msg_id)

                    processed.add(msg_id)
                    save_processed(processed)
                    continue

                logger.info(f"Processing: {subject}")

                # ✅ 2. BUILD CONTEXT (CRITICAL FIX)
                context = build_thread_context(service, thread_id)
                text_for_classification = context if context else body

                # ✅ 3. RULE-BASED INTENT FIRST (FAST)
                simple_intent = detect_simple_intent(body)

                # ✅ DO NOT skip if order ID present
                if simple_intent == "gratitude" and not has_order_id(body):
                    logger.info("Detected gratitude → skipping reply")

                    mark_as_read(service, msg_id)
                    processed.add(msg_id)
                    continue


                # ✅ 4. LLM CLASSIFICATION
                intent = classify_intent(text_for_classification)

                logger.info(f"Detected intent: {intent}")

                # ✅ ALWAYS update thread (important)
                update_thread_on_reply(thread_id, body, intent)

                # ✅ 5. SAFETY: SKIP GRATITUDE AGAIN (DOUBLE GUARD)
                if intent == "gratitude":
                    logger.info("LLM detected gratitude → skipping reply")

                    mark_as_read(service, msg_id)
                    processed.add(msg_id)
                    continue

                # 🔹 Step 1: Auto Reply
                if intent in ALLOWED_INTENTS:
                    try:
                        reply = generate_reply(intent, body)
                    except Exception as e:
                        logger.error(f"Reply generation failed: {e}")
                        reply = TEMPLATES.get(intent, "We will get back to you shortly.")

                    send_reply(service, thread_id, reply, sender, subject, message_id)
                    add_label_to_email(service, msg_id, AUTO_LABEL)

                # mark read + processed
                mark_as_read(service, msg_id)
                processed.add(msg_id)

            save_processed(processed)

            # 🚨 Step 2: Escalation checker
            alerts = check_escalations()

            for alert in alerts:
                thread_id = alert["thread_id"]
                level = alert["level"]
                email = alert["email"]

                logger.warning(f"Escalation L{level} for {thread_id}")

                send_alert(
                    service,
                    f"Escalation Level {level}",
                    f"Thread {thread_id} pending for {level * 24} hours.",
                    [email]
                )

                if level == 1:
                    label_id = ESCALATED_L1
                else:
                    label_id = ESCALATED_L2

                # (Optional) add thread labeling logic here later

        except Exception as e:
            logger.error(f"Loop error: {e}")

        time.sleep(30)


if __name__ == "__main__":
    main()