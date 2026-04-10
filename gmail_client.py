import base64
import re
from email.mime.text import MIMEText
from googleapiclient.errors import HttpError


# ✅ FETCH UNREAD EMAILS
def fetch_unread_emails(service):
    try:
        results = service.users().messages().list(
            userId="me",
            q="is:unread to:custcare@mbindia.net",
            maxResults=10
        ).execute()
        return results.get("messages", [])
    except HttpError as e:
        print("Gmail API error:", e)
        return []


# ✅ GET EMAIL CONTENT
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

    body = extract_body(payload)

    return subject, body, msg.get("threadId"), sender


# ✅ BODY EXTRACTOR (Improved)
def extract_body(payload):
    body = ""

    try:
        if "parts" in payload:
            for part in payload["parts"]:
                mime = part.get("mimeType")

                if mime == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

                # fallback to HTML
                elif mime == "text/html":
                    data = part["body"].get("data")
                    if data and not body:
                        html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        body = clean_html(html)

        else:
            data = payload.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    except Exception as e:
        print("Error decoding email:", e)

    return body


# ✅ SIMPLE HTML CLEANER
def clean_html(html):
    clean = re.sub('<.*?>', '', html)
    return clean.strip()


# ✅ SEND REPLY
def send_reply(service, thread_id, reply_text, to_email, subject):
    try:
        # remove accidental subject duplication
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


# ✅ MARK EMAIL AS READ
def mark_as_read(service, msg_id):
    try:
        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception as e:
        print(f"Failed to mark as read: {e}")


# ✅ LABEL HELPERS
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


# 🆕 GET ALL MESSAGES IN THREAD
def get_thread_messages(service, thread_id):
    try:
        thread = service.users().threads().get(
            userId="me",
            id=thread_id
        ).execute()

        return thread.get("messages", [])
    except Exception as e:
        print(f"Failed to fetch thread: {e}")
        return []


# 🆕 GET LAST MESSAGE ID FROM THREAD
def get_last_message_id(service, thread_id):
    messages = get_thread_messages(service, thread_id)
    if messages:
        return messages[-1]["id"]
    return None


# 🆕 ADD LABEL TO LATEST MESSAGE IN THREAD
def add_label_to_thread(service, thread_id, label_id):
    try:
        last_msg_id = get_last_message_id(service, thread_id)
        if last_msg_id:
            add_label_to_email(service, last_msg_id, label_id)
    except Exception as e:
        print(f"Thread labeling failed: {e}")


# 🆕 DETECT IF AGENT REPLIED
def is_agent(sender):
    agents = [
        "custcare@mbindia.net",
        "himanshi@mbindia.net",
        "shuja@mbindia.net"
    ]
    return sender.lower() in agents