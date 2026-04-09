import json
import os
from datetime import datetime

ALERT_FILE = "alert_tracker.json"
ESCALATION_INTENTS = ["return", "refund", "exchange"]
ALERT_EMAILS = ["himanshi@mbindia.net", "shuja@mbindia.net","mbai@mbindia.net"]

def load_tracker():
    if not os.path.exists(ALERT_FILE):
        return {}
    with open(ALERT_FILE, "r") as f:
        return json.load(f)


def save_tracker(data):
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f, indent=4)


def should_escalate(thread_id, intent):
    if not intent:
        return False

    if intent.lower() not in ESCALATION_INTENTS:
        return False

    data = load_tracker()

    if thread_id not in data:
        data[thread_id] = {
            "count": 1,
            "intent": intent,
            "alert_sent": False,
            "last_seen": str(datetime.now())
        }
    else:
        data[thread_id]["count"] += 1
        data[thread_id]["last_seen"] = str(datetime.now())

    # ✅ Trigger alert ONLY ONCE
    if data[thread_id]["count"] == 2 and not data[thread_id]["alert_sent"]:
        data[thread_id]["alert_sent"] = True
        save_tracker(data)
        return True

    save_tracker(data)
    return False


def get_alert_emails():
    return ALERT_EMAILS