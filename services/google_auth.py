"""
Google OAuth authentication for Gmail and Calendar APIs.
"""

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import Optional

from config.settings import settings


def get_google_credentials() -> Optional[Credentials]:
    """
    Get Google API credentials from settings.

    Returns:
        Credentials object or None if not configured
    """
    if not settings.has_google_auth():
        return None

    creds = Credentials(
        token=None,  # Will be refreshed
        refresh_token=settings.google_refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar',
        ]
    )

    # Refresh the token
    if not creds.valid:
        creds.refresh(Request())

    return creds


def get_gmail_service():
    """Get Gmail API service."""
    creds = get_google_credentials()
    if not creds:
        raise ValueError("Google authentication not configured")

    return build('gmail', 'v1', credentials=creds)


def get_calendar_service():
    """Get Calendar API service."""
    creds = get_google_credentials()
    if not creds:
        raise ValueError("Google authentication not configured")

    return build('calendar', 'v3', credentials=creds)
