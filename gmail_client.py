import base64
import re
from email.mime.text import MIMEText
from googleapiclient.errors import HttpError


def fetch_unread_emails(service):
    try:
        results = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=10
        ).execute()
        return results.get("messages", [])
    except HttpError as e:
        print("Gmail API error:", e)
        return []


def get_email_content(service, msg_id):
    msg = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full"
    ).execute()

    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    subject = next(
        (h["value"] for h in headers if h["name"] == "Subject"),
        "(No Subject)"
    )

    sender = next(
        (h["value"] for h in headers if h["name"] == "From"),
        ""
    )

    # ✅ Extract pure email
    match = re.search(r'<(.+?)>', sender)
    if match:
        sender = match.group(1)

    body = ""

    try:
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        break
        else:
            data = payload.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    except Exception as e:
        print("Error decoding email:", e)

    return subject, body, msg.get("threadId"), sender


def send_reply(service, thread_id, reply_text, to_email, subject):
    try:
        import re

        # ❌ Remove unwanted "Subject:" line from body
        reply_text = re.sub(r"Subject:.*\n", "", reply_text, flags=re.IGNORECASE)

        message = MIMEText(reply_text.strip())

        message["to"] = to_email
        message["subject"] = f"Re: {subject}"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={
                "raw": raw,
                "threadId": thread_id
            }
        ).execute()

    except HttpError as e:
        print("Send error:", e)


# ✅ ALERT EMAIL
def send_alert(service, subject, body, to_emails):
    try:
        message = MIMEText(body)
        message["to"] = ", ".join(to_emails)
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

    except HttpError as e:
        print("Alert send error:", e)


def mark_as_read(service, msg_id):
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception as e:
        print(f"Failed to mark as read: {e}")


def get_or_create_label(service, label_name):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    label_body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }

    label = service.users().labels().create(
        userId="me",
        body=label_body
    ).execute()

    return label["id"]


def add_label_to_email(service, msg_id, label_id):
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": [label_id]}
        ).execute()
    except Exception as e:
        print(f"Failed to add label: {e}")