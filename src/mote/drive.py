"""Google Drive API wrapper for Mote transcript uploads."""

import json
from pathlib import Path

# Module-level constants (no Google imports needed here)
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CLIENT_CONFIG = {
    "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "YOUR_CLIENT_SECRET",
        "redirect_uris": ["http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}
MIME_TYPES = {
    "md": "text/markdown",
    "txt": "text/plain",
    "json": "application/json",
}


def get_token_path(config_dir: Path) -> Path:
    """Return path to Google OAuth token file (D-02)."""
    return config_dir / "google_token.json"


def get_credentials(token_path: Path):
    """Load credentials from token file, refreshing if expired.

    Returns Credentials if valid, None if missing or unrefreshable.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not token_path.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Preserve cached folder_id when rewriting token
            folder_id = _load_folder_id(token_path)
            _save_token(token_path, creds, folder_id=folder_id)
        else:
            return None

    return creds if creds.valid else None


def run_auth_flow(token_path: Path):
    """Run browser OAuth2 consent flow and store token (D-03).

    Returns Credentials.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    _save_token(token_path, creds)
    return creds


def build_service(creds):
    """Build and return Google Drive v3 service."""
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, folder_name: str) -> str:
    """Return folder ID for named Drive folder, creating it if absent.

    With drive.file scope, only finds folders the app itself created.
    """
    q = (
        f"name='{folder_name}' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false"
    )
    results = (
        service.files()
        .list(q=q, spaces="drive", fields="files(id,name)")
        .execute()
    )
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    # Create the folder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_file(service, local_path: Path, folder_id: str) -> str:
    """Upload local_path to Drive folder. Returns Drive file ID."""
    from googleapiclient.http import MediaFileUpload

    ext = local_path.suffix.lstrip(".")
    mime = MIME_TYPES.get(ext, "text/plain")
    metadata = {"name": local_path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(local_path), mimetype=mime)
    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id")
        .execute()
    )
    return file["id"]


def _save_token(token_path: Path, creds, folder_id: str | None = None) -> None:
    """Write credentials JSON to token_path with 600 permissions.

    Optionally embeds drive_folder_id alongside OAuth credentials.
    """
    data = json.loads(creds.to_json())
    if folder_id:
        data["drive_folder_id"] = folder_id
    token_path.write_text(json.dumps(data))
    token_path.chmod(0o600)


def _load_folder_id(token_path: Path) -> str | None:
    """Read cached Drive folder ID from token file. Returns None if missing."""
    if not token_path.exists():
        return None
    data = json.loads(token_path.read_text())
    return data.get("drive_folder_id")


def upload_transcripts(
    config_dir: Path, files: list[Path], folder_name: str
) -> None:
    """Upload all transcript files to Google Drive.

    Orchestrates: load creds → build service → get/create folder → upload each file.
    Raises RuntimeError if not authenticated (caller should warn, per D-09).
    """
    token_path = get_token_path(config_dir)
    creds = get_credentials(token_path)
    if creds is None:
        raise RuntimeError(
            "Not authenticated with Google Drive. Run: mote auth google"
        )

    service = build_service(creds)

    # Use cached folder_id if available; otherwise look up / create
    folder_id = _load_folder_id(token_path)
    if not folder_id:
        folder_id = get_or_create_folder(service, folder_name)
        _save_token(token_path, creds, folder_id=folder_id)

    for f in files:
        upload_file(service, f, folder_id)
