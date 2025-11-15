"""
Email tools using Gmail API.
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from config.settings import settings
from services.google_auth import get_gmail_service


def send_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email via Gmail API.

    Args:
        to_email: Recipient email
        subject: Email subject
        body_html: HTML body
        body_text: Plain text body (optional, will be derived from HTML if not provided)
        thread_id: Gmail thread ID for replies

    Returns:
        Dict with message ID and status
    """
    if settings.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "message_id": f"dry_run_{datetime.now().timestamp()}",
            "to": to_email,
            "subject": subject
        }

    try:
        service = get_gmail_service()

        # Create message
        message = MIMEMultipart('alternative')
        message['To'] = to_email
        message['From'] = f"{settings.gmail_sender_name} <{settings.gmail_sender_email}>"
        message['Subject'] = subject

        # Add text part
        if body_text:
            part1 = MIMEText(body_text, 'plain')
            message.attach(part1)

        # Add HTML part
        part2 = MIMEText(body_html, 'html')
        message.attach(part2)

        # Encode
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        message_body = {'raw': raw_message}
        if thread_id:
            message_body['threadId'] = thread_id

        # Send
        sent_message = service.users().messages().send(
            userId='me',
            body=message_body
        ).execute()

        return {
            "success": True,
            "message_id": sent_message['id'],
            "thread_id": sent_message.get('threadId'),
            "to": to_email
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "to": to_email
        }


def list_incoming_emails(
    since_hours: int = 24,
    query: Optional[str] = None,
    max_results: int = 100
) -> List[Dict[str, Any]]:
    """
    List incoming emails.

    Args:
        since_hours: Get emails from the last N hours
        query: Gmail search query (e.g., "from:someone@example.com")
        max_results: Max emails to return

    Returns:
        List of email dicts
    """
    if settings.dry_run:
        return []

    try:
        service = get_gmail_service()

        # Build query
        since_timestamp = int((datetime.now() - timedelta(hours=since_hours)).timestamp())
        full_query = f"after:{since_timestamp}"
        if query:
            full_query += f" {query}"

        # Get message IDs
        results = service.users().messages().list(
            userId='me',
            q=full_query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        emails = []
        for msg in messages:
            # Get full message
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in message['payload']['headers']}

            # Get body
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode()
                            break
            else:
                data = message['payload']['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode()

            emails.append({
                "id": msg['id'],
                "thread_id": message['threadId'],
                "from": headers.get('From', ''),
                "to": headers.get('To', ''),
                "subject": headers.get('Subject', ''),
                "body": body,
                "date": headers.get('Date', ''),
                "snippet": message.get('snippet', '')
            })

        return emails

    except Exception as e:
        print(f"Error listing emails: {e}")
        return []


def get_email_thread(thread_id: str) -> List[Dict[str, Any]]:
    """Get all messages in a thread."""
    if settings.dry_run:
        return []

    try:
        service = get_gmail_service()

        thread = service.users().threads().get(
            userId='me',
            id=thread_id
        ).execute()

        messages = []
        for msg in thread['messages']:
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}

            # Get body (simplified)
            body = msg.get('snippet', '')

            messages.append({
                "id": msg['id'],
                "from": headers.get('From', ''),
                "subject": headers.get('Subject', ''),
                "body": body,
                "date": headers.get('Date', '')
            })

        return messages

    except Exception as e:
        print(f"Error getting thread: {e}")
        return []
