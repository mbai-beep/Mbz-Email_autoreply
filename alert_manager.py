import json
import os
from datetime import datetime, timedelta

ALERT_FILE = "alert_tracker.json"

ESCALATION_INTENTS = ["return", "refund", "exchange"]

LEVEL_1_EMAIL = "himanshi@mbindia.net"
LEVEL_2_EMAIL = "shuja@mbindia.net"


def load_tracker():
    if not os.path.exists(ALERT_FILE):
        return {}
    with open(ALERT_FILE, "r") as f:
        return json.load(f)


def save_tracker(data):
    with open(ALERT_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ✅ Detect order details (basic logic - can improve later)
def contains_order_details(text):
    import re
    return bool(re.search(r"\b\d{5,}\b", text))


# ✅ Call this when customer sends reply
def update_thread_on_reply(thread_id, body, intent):
    data = load_tracker()

    if thread_id not in data:
        data[thread_id] = {
            "intent": intent,
            "order_details_received": False,
            "order_details_time": None,
            "agent_replied": False,
            "escalation_level": 0
        }

    # Detect order details
    if contains_order_details(body):
        data[thread_id]["order_details_received"] = True
        data[thread_id]["order_details_time"] = str(datetime.now())

    save_tracker(data)


# ✅ Mark when agent replies (optional but useful)
def mark_agent_replied(thread_id):
    data = load_tracker()
    if thread_id in data:
        data[thread_id]["agent_replied"] = True
        save_tracker(data)


# ✅ Core escalation checker
def check_escalations():
    data = load_tracker()
    alerts = []

    now = datetime.now()

    for thread_id, info in data.items():

        if not info.get("order_details_received"):
            continue

        if info.get("agent_replied"):
            continue

        order_time_str = info.get("order_details_time")
        if not order_time_str:
            continue

        order_time = datetime.fromisoformat(order_time_str)
        time_passed = now - order_time

        # 🚨 Level 1: after 24h
        if time_passed >= timedelta(hours=24) and info["escalation_level"] == 0:
            alerts.append({
                "thread_id": thread_id,
                "level": 1,
                "email": LEVEL_1_EMAIL
            })
            info["escalation_level"] = 1

        # 🚨 Level 2: after 48h
        elif time_passed >= timedelta(hours=48) and info["escalation_level"] == 1:
            alerts.append({
                "thread_id": thread_id,
                "level": 2,
                "email": LEVEL_2_EMAIL
            })
            info["escalation_level"] = 2

    save_tracker(data)
    return alerts