#!/usr/bin/env python3
"""
Setup script for Google OAuth authentication.
Run this to get your refresh token for Gmail and Calendar APIs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

# Scopes needed
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
]


def setup_oauth():
    """Run OAuth flow and get refresh token."""
    print("=" * 70)
    print("Google OAuth Setup for LeadFactory California")
    print("=" * 70)
    print()
    print("You'll need:")
    print("1. Google Cloud Project with Gmail and Calendar APIs enabled")
    print("2. OAuth 2.0 Client ID credentials (Desktop app)")
    print()
    print("Get these from: https://console.cloud.google.com/apis/credentials")
    print()

    client_id = input("Enter your Google Client ID: ").strip()
    client_secret = input("Enter your Google Client Secret: ").strip()

    if not client_id or not client_secret:
        print("\n✗ Client ID and Secret are required!")
        sys.exit(1)

    # Create flow
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"]
            }
        },
        scopes=SCOPES
    )

    print("\n📝 Opening browser for authentication...")
    print("Please sign in with your Google account and grant permissions.")
    print()

    try:
        creds = flow.run_local_server(port=0)

        print("\n✓ Authentication successful!")
        print()
        print("=" * 70)
        print("Add these to your .env file:")
        print("=" * 70)
        print()
        print(f"GOOGLE_CLIENT_ID={client_id}")
        print(f"GOOGLE_CLIENT_SECRET={client_secret}")
        print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
        print()
        print("=" * 70)

        # Ask if they want to auto-update .env
        update = input("\nWould you like to update .env automatically? (y/n): ").lower()

        if update == 'y':
            env_path = Path(__file__).parent.parent / '.env'

            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()

                # Update or add lines
                updated_lines = []
                keys_to_update = {
                    'GOOGLE_CLIENT_ID': client_id,
                    'GOOGLE_CLIENT_SECRET': client_secret,
                    'GOOGLE_REFRESH_TOKEN': creds.refresh_token
                }

                found_keys = set()
                for line in lines:
                    updated = False
                    for key, value in keys_to_update.items():
                        if line.startswith(f"{key}="):
                            updated_lines.append(f"{key}={value}\n")
                            found_keys.add(key)
                            updated = True
                            break
                    if not updated:
                        updated_lines.append(line)

                # Add missing keys
                for key, value in keys_to_update.items():
                    if key not in found_keys:
                        updated_lines.append(f"{key}={value}\n")

                with open(env_path, 'w') as f:
                    f.writelines(updated_lines)

                print(f"✓ Updated {env_path}")
            else:
                print(f"✗ .env file not found at {env_path}")
                print("Please create it manually using config/example.env as a template")

        print("\n✓ Setup complete!")
        print("You can now use Gmail and Google Calendar features.")

    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_oauth()
