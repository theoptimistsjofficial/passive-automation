#!/usr/bin/env python
"""One-time YouTube OAuth setup.

Prereq:
  1. Go to https://console.cloud.google.com/
  2. Create project (or reuse). Enable YouTube Data API v3.
  3. APIs & Services > OAuth consent screen > External (testing OK)
     Add your Google account as a test user
  4. Credentials > Create Credentials > OAuth client ID > Application type: Desktop app
  5. Download the JSON, save to: config/youtube_client_secret.json
  6. Run this script: python scripts/setup_youtube_oauth.py
     A browser opens; sign in with the Google account that owns @OptimistMantra
     Grant permissions. The script saves config/youtube_token.json for future headless uploads.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import YOUTUBE_CLIENT_SECRETS_JSON, YOUTUBE_TOKEN_JSON

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing package. Run: pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    secrets = ROOT / YOUTUBE_CLIENT_SECRETS_JSON
    if not secrets.exists():
        print(f"Missing client secrets at: {secrets}")
        print("Download from Google Cloud Console (see docstring at top of this file)")
        sys.exit(2)

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = ROOT / YOUTUBE_TOKEN_JSON
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    print(f"\n✅ YouTube token saved: {token_path}")
    print("Future uploads will run headless. Test with: python -c \"from services.youtube import _load_credentials; _load_credentials(); print('OK')\"")


if __name__ == "__main__":
    main()
