"""YouTube Data API v3 upload.

One-time OAuth: run scripts/setup_youtube_oauth.py to generate the token JSON.
After that, upload() runs headless — reads the refresh token and uploads.

Auth files expected:
  config/youtube_client_secret.json — OAuth 2.0 desktop credentials (download from Cloud Console)
  config/youtube_token.json         — refresh token (created by setup_youtube_oauth.py)
"""
import json
from pathlib import Path
from typing import Optional
from core.config import ROOT, YOUTUBE_CLIENT_SECRETS_JSON, YOUTUBE_TOKEN_JSON
from core.logger import get_logger

log = get_logger("youtube")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _load_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_path = ROOT / YOUTUBE_TOKEN_JSON
    if not token_path.exists():
        raise RuntimeError(
            f"YouTube token not found at {token_path}. "
            "Run: python scripts/setup_youtube_oauth.py"
        )
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            log.info("YouTube token refreshed")
        else:
            raise RuntimeError("YouTube credentials invalid — re-run setup_youtube_oauth.py")
    return creds


def upload(video_path: Path, title: str, description: str, tags: list[str],
           category_id: str = "22", privacy: str = "public",
           thumbnail_path: Optional[Path] = None) -> str:
    """Upload video to YouTube. Returns the video ID.

    category_id: 22 = People & Blogs, 24 = Entertainment, 27 = Education
    privacy: 'public' | 'unlisted' | 'private'
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        raise RuntimeError(
            f"google-api-python-client not installed: {e}\n"
            "Add to requirements.txt: google-api-python-client google-auth-oauthlib"
        )

    creds = _load_credentials()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    log.info(f"YouTube upload starting: {video_path.name} ({video_path.stat().st_size//1024//1024}MB)")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info(f"YouTube upload: {int(status.progress() * 100)}%")

    video_id = response["id"]
    video_url = f"https://youtu.be/{video_id}"
    log.info(f"YouTube upload complete: {video_url}")

    if thumbnail_path and thumbnail_path.exists():
        try:
            yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
            log.info(f"YouTube thumbnail set: {thumbnail_path.name}")
        except Exception as e:
            log.warning(f"YouTube thumbnail upload failed (non-fatal): {e}")

    return video_id
