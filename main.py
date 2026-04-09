import time
import json
from gmail_client import *
from classifier import classify_intent
from reply_generator import generate_reply
from templates import TEMPLATES
from config import ALLOWED_INTENTS
from logger import setup_logger
from auth import get_gmail_service
from gmail_client import add_label_to_email, get_or_create_label

from alert_manager import should_escalate, get_alert_emails

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


def main():
    logger.info("Email bot started")

    service = get_gmail_service()

    AUTO_LABEL = get_or_create_label(service, "AutoReplied")
    ESCALATED_LABEL = get_or_create_label(service, "Escalated")

    processed = load_processed()

    while True:
        try:
            for attempt in range(3):
                try:
                    messages = fetch_unread_emails(service)
                    break
                except Exception as e:
                    logger.warning(f"Fetch retry {attempt+1}: {e}")
                    time.sleep(2)
            else:
                logger.error("Failed to fetch emails after retries")
                time.sleep(30)
                continue

            logger.info(f"Fetched {len(messages)} messages")

            for msg in messages:
                msg_id = msg.get("id")

                if not msg_id or msg_id in processed:
                    continue

                try:
                    subject, body, thread_id, sender = get_email_content(service, msg_id)
                except Exception as e:
                    logger.error(f"Failed to read email {msg_id}: {e}")
                    continue

                # ✅ Avoid replying to yourself
                if "custcare@mbindia.net" in sender:
                    logger.info("Skipping self email")
                    continue

                logger.info(f"Processing email: {subject}")

                intent = classify_intent(body)
                logger.info(f"Detected intent: {intent}")

                # ✅ ESCALATION
                # ✅ ESCALATION (UPDATED - FINAL)
                if should_escalate(thread_id, intent):
                    logger.warning(f"Escalation triggered for thread {thread_id}")

                    # 🚨 Send internal alert
                    send_alert(
                        service,
                        f"Escalation: {intent}",
                        f"Repeated issue detected\n\nSubject: {subject}",
                        get_alert_emails()
                    )

                    # 🏷️ Add Escalated label
                    add_label_to_email(service, msg_id, ESCALATED_LABEL)

                    # 📩 Send acknowledgement to customer
                    try:
                        escalation_reply = TEMPLATES.get(
                            "escalation_ack",
                            "Hi,\n\nYour request has been escalated to our concerned team. "
                            "They will get back to you shortly.\n\nRegards"
                        )

                        send_reply(
                            service,
                            thread_id,
                            escalation_reply,
                            sender,
                            subject
                        )

                        logger.info("Escalation acknowledgement sent to customer")

                    except Exception as e:
                        logger.error(f"Failed to send escalation reply: {e}")

                    # ✅ Mark email as read
                    try:
                        mark_as_read(service, msg_id)
                    except Exception as e:
                        logger.error(f"Failed to mark as read: {e}")

                    # ✅ Save processed
                    processed.add(msg_id)
                    save_processed(processed)

                    # ❗ CRITICAL: stop further processing (no AI reply)
                    continue

                if intent not in ALLOWED_INTENTS:
                    logger.info("Skipped: not relevant")
                    mark_as_read(service, msg_id)
                    processed.add(msg_id)
                    continue

                try:
                    reply = generate_reply(intent, body)
                except Exception as e:
                    logger.error(f"AI failed: {e}")
                    reply = TEMPLATES.get(intent, "We will get back to you shortly.")

                try:
                    send_reply(service, thread_id, reply, sender, subject)
                    add_label_to_email(service, msg_id, AUTO_LABEL)
                    logger.info("Reply sent successfully")
                except Exception as e:
                    logger.error(f"Failed to send reply: {e}")

                try:
                    mark_as_read(service, msg_id)
                    logger.info("Marked email as read")
                except Exception as e:
                    logger.error(f"Failed to mark as read: {e}")

                processed.add(msg_id)
                save_processed(processed)

        except Exception as e:
            logger.error(f"Loop error: {e}")

        time.sleep(30)


if __name__ == "__main__":
    main()
    