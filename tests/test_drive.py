"""Unit tests for mote.drive module."""

import json
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from mote.drive import (
    MIME_TYPES,
    SCOPES,
    CLIENT_CONFIG,
    get_token_path,
    get_credentials,
    run_auth_flow,
    build_service,
    get_or_create_folder,
    upload_file,
    upload_transcripts,
    _save_token,
    _load_folder_id,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_scopes_contains_drive_file():
    """SCOPES contains the drive.file scope."""
    assert "https://www.googleapis.com/auth/drive.file" in SCOPES


def test_client_config_has_installed_key():
    """CLIENT_CONFIG has 'installed' key with required fields."""
    assert "installed" in CLIENT_CONFIG
    installed = CLIENT_CONFIG["installed"]
    assert "client_id" in installed
    assert "client_secret" in installed
    assert "redirect_uris" in installed


def test_mime_types():
    """MIME_TYPES maps md, txt, json to correct MIME types."""
    assert MIME_TYPES["md"] == "text/markdown"
    assert MIME_TYPES["txt"] == "text/plain"
    assert MIME_TYPES["json"] == "application/json"


# ---------------------------------------------------------------------------
# get_token_path
# ---------------------------------------------------------------------------


def test_get_token_path(mote_home):
    """get_token_path returns config_dir / google_token.json."""
    result = get_token_path(mote_home)
    assert result == mote_home / "google_token.json"


# ---------------------------------------------------------------------------
# get_credentials
# ---------------------------------------------------------------------------


def test_get_credentials_no_file(mote_home):
    """get_credentials returns None when token file does not exist."""
    token_path = mote_home / "google_token.json"
    result = get_credentials(token_path)
    assert result is None


def test_get_credentials_loads_valid(mote_home):
    """get_credentials loads valid credentials from token file."""
    token_path = mote_home / "google_token.json"
    token_path.write_text(json.dumps({"token": "valid_token"}))
    token_path.chmod(0o600)

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False

    with patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    ):
        result = get_credentials(token_path)

    assert result is mock_creds


def test_get_credentials_refreshes_expired(mote_home):
    """get_credentials refreshes expired credentials and rewrites token file with 600 perms."""
    token_path = mote_home / "google_token.json"
    # Write a minimal token file so it "exists" with a folder_id
    token_path.write_text(
        json.dumps({"token": "expired_token", "drive_folder_id": "folder123"})
    )
    token_path.chmod(0o600)

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "some-refresh-token"
    mock_creds.to_json.return_value = json.dumps({"token": "new_token"})

    def make_valid(request):
        mock_creds.valid = True

    mock_creds.refresh.side_effect = make_valid

    with patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    ):
        with patch("google.auth.transport.requests.Request"):
            result = get_credentials(token_path)

    assert result is mock_creds
    # Token file should have been rewritten
    assert token_path.exists()
    mode = stat.S_IMODE(token_path.stat().st_mode)
    assert mode == 0o600


def test_get_credentials_returns_none_when_invalid(mote_home):
    """get_credentials returns None when credentials are invalid and cannot refresh."""
    token_path = mote_home / "google_token.json"
    token_path.write_text(json.dumps({"token": "bad_token"}))
    token_path.chmod(0o600)

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = False
    mock_creds.refresh_token = None

    with patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    ):
        result = get_credentials(token_path)

    assert result is None


# ---------------------------------------------------------------------------
# run_auth_flow
# ---------------------------------------------------------------------------


def test_run_auth_flow_saves_token_with_600_perms(mote_home):
    """run_auth_flow calls InstalledAppFlow and writes token with 600 permissions."""
    token_path = mote_home / "google_token.json"

    mock_creds = MagicMock()
    mock_creds.to_json.return_value = json.dumps({"token": "new_access_token"})

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds

    with patch(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_config",
        return_value=mock_flow,
    ) as mock_from_config:
        result = run_auth_flow(token_path)

    # Verify from_client_config called with CLIENT_CONFIG and SCOPES
    mock_from_config.assert_called_once_with(CLIENT_CONFIG, scopes=SCOPES)
    # Verify run_local_server called with correct params
    mock_flow.run_local_server.assert_called_once_with(
        port=0, access_type="offline", prompt="consent"
    )
    # Token file written
    assert token_path.exists()
    mode = stat.S_IMODE(token_path.stat().st_mode)
    assert mode == 0o600
    assert result is mock_creds


# ---------------------------------------------------------------------------
# build_service
# ---------------------------------------------------------------------------


def test_build_service():
    """build_service calls googleapiclient.discovery.build with drive v3."""
    mock_creds = MagicMock()
    mock_service = MagicMock()

    with patch(
        "googleapiclient.discovery.build", return_value=mock_service
    ) as mock_build:
        result = build_service(mock_creds)

    mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds)
    assert result is mock_service


# ---------------------------------------------------------------------------
# get_or_create_folder
# ---------------------------------------------------------------------------


def test_get_or_create_folder_existing():
    """get_or_create_folder returns existing folder ID when search finds one."""
    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {
        "files": [{"id": "existing-folder-id", "name": "Mote Transcripts"}]
    }

    result = get_or_create_folder(mock_service, "Mote Transcripts")

    assert result == "existing-folder-id"
    # Should NOT call files().create()
    mock_service.files().create.assert_not_called()


def test_get_or_create_folder_creates_when_absent():
    """get_or_create_folder creates folder and returns new ID when search finds none."""
    mock_service = MagicMock()
    # Reset call history to avoid chain pollution
    mock_service.reset_mock()

    # Need to return distinct mocks for list vs create
    mock_list_execute = MagicMock(return_value={"files": []})
    mock_list_request = MagicMock()
    mock_list_request.execute = mock_list_execute

    mock_create_execute = MagicMock(return_value={"id": "new-folder-id"})
    mock_create_request = MagicMock()
    mock_create_request.execute = mock_create_execute

    mock_files = MagicMock()
    mock_files.list.return_value = mock_list_request
    mock_files.create.return_value = mock_create_request
    mock_service.files.return_value = mock_files

    result = get_or_create_folder(mock_service, "Mote Transcripts")

    assert result == "new-folder-id"
    mock_files.create.assert_called_once()


# ---------------------------------------------------------------------------
# upload_file
# ---------------------------------------------------------------------------


def test_upload_file_md(tmp_path):
    """upload_file calls files().create with correct metadata for .md file."""
    md_file = tmp_path / "transcript.md"
    md_file.write_text("# Meeting transcript")

    mock_service = MagicMock()
    mock_service.files().create().execute.return_value = {"id": "drive-file-id"}

    with patch("googleapiclient.http.MediaFileUpload") as mock_media:
        result = upload_file(mock_service, md_file, "folder-123")

    # Verify metadata passed to create
    create_call_kwargs = mock_service.files().create.call_args
    body = create_call_kwargs[1].get("body") or create_call_kwargs[0][0] if create_call_kwargs[0] else create_call_kwargs[1]["body"]
    assert body["name"] == "transcript.md"
    assert body["parents"] == ["folder-123"]

    # Verify MediaFileUpload called with md mime type
    mock_media.assert_called_once_with(str(md_file), mimetype="text/markdown")


def test_upload_file_txt(tmp_path):
    """upload_file uses text/plain MIME type for .txt file."""
    txt_file = tmp_path / "transcript.txt"
    txt_file.write_text("Meeting transcript")

    mock_service = MagicMock()
    mock_service.files().create().execute.return_value = {"id": "drive-file-id"}

    with patch("googleapiclient.http.MediaFileUpload") as mock_media:
        upload_file(mock_service, txt_file, "folder-123")

    mock_media.assert_called_once_with(str(txt_file), mimetype="text/plain")


def test_upload_file_json(tmp_path):
    """upload_file uses application/json MIME type for .json file."""
    json_file = tmp_path / "transcript.json"
    json_file.write_text('{"text": "Meeting transcript"}')

    mock_service = MagicMock()
    mock_service.files().create().execute.return_value = {"id": "drive-file-id"}

    with patch("googleapiclient.http.MediaFileUpload") as mock_media:
        upload_file(mock_service, json_file, "folder-123")

    mock_media.assert_called_once_with(str(json_file), mimetype="application/json")


def test_upload_file_returns_id(tmp_path):
    """upload_file returns Drive file ID."""
    f = tmp_path / "t.md"
    f.write_text("content")

    mock_service = MagicMock()
    mock_service.files().create().execute.return_value = {"id": "returned-file-id"}

    with patch("googleapiclient.http.MediaFileUpload"):
        result = upload_file(mock_service, f, "folder-123")

    assert result == "returned-file-id"


# ---------------------------------------------------------------------------
# _save_token / _load_folder_id
# ---------------------------------------------------------------------------


def test_save_token_writes_json_with_600_perms(mote_home):
    """_save_token writes JSON and sets 600 permissions."""
    token_path = mote_home / "google_token.json"
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = json.dumps({"token": "access_token"})

    _save_token(token_path, mock_creds)

    assert token_path.exists()
    mode = stat.S_IMODE(token_path.stat().st_mode)
    assert mode == 0o600
    data = json.loads(token_path.read_text())
    assert "token" in data


def test_save_token_includes_folder_id(mote_home):
    """_save_token includes drive_folder_id when provided."""
    token_path = mote_home / "google_token.json"
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = json.dumps({"token": "access_token"})

    _save_token(token_path, mock_creds, folder_id="my-folder-id")

    data = json.loads(token_path.read_text())
    assert data["drive_folder_id"] == "my-folder-id"


def test_load_folder_id_returns_none_when_no_file(mote_home):
    """_load_folder_id returns None when token file does not exist."""
    token_path = mote_home / "google_token.json"
    result = _load_folder_id(token_path)
    assert result is None


def test_load_folder_id_returns_none_when_field_missing(mote_home):
    """_load_folder_id returns None when drive_folder_id not in token."""
    token_path = mote_home / "google_token.json"
    token_path.write_text(json.dumps({"token": "some_token"}))

    result = _load_folder_id(token_path)
    assert result is None


def test_load_folder_id_reads_value(mote_home):
    """_load_folder_id returns drive_folder_id from token file."""
    token_path = mote_home / "google_token.json"
    token_path.write_text(
        json.dumps({"token": "some_token", "drive_folder_id": "cached-id"})
    )

    result = _load_folder_id(token_path)
    assert result == "cached-id"


# ---------------------------------------------------------------------------
# upload_transcripts
# ---------------------------------------------------------------------------


def test_upload_transcripts_raises_when_not_authenticated(mote_home, tmp_path):
    """upload_transcripts raises RuntimeError when not authenticated (no token)."""
    files = [tmp_path / "t.md"]

    with pytest.raises(RuntimeError, match="Not authenticated"):
        upload_transcripts(mote_home, files, "Mote Transcripts")


def test_upload_transcripts_orchestrates_full_flow(mote_home, tmp_path):
    """upload_transcripts loads creds, builds service, gets/creates folder, uploads."""
    token_path = mote_home / "google_token.json"
    token_path.write_text(json.dumps({"token": "valid_token"}))
    token_path.chmod(0o600)

    # Create test files
    f1 = tmp_path / "transcript.md"
    f1.write_text("content")
    f2 = tmp_path / "transcript.txt"
    f2.write_text("content")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = json.dumps({"token": "valid_token"})

    mock_service = MagicMock()
    mock_service.files().list().execute.return_value = {
        "files": [{"id": "existing-folder-id"}]
    }
    mock_service.files().create().execute.return_value = {"id": "uploaded-file-id"}

    with (
        patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ),
        patch("googleapiclient.discovery.build", return_value=mock_service),
        patch("googleapiclient.http.MediaFileUpload"),
    ):
        upload_transcripts(mote_home, [f1, f2], "Mote Transcripts")


def test_upload_transcripts_caches_folder_id(mote_home, tmp_path):
    """upload_transcripts caches folder_id in token file after first folder lookup."""
    token_path = mote_home / "google_token.json"
    # No cached folder_id initially
    token_path.write_text(json.dumps({"token": "valid_token"}))
    token_path.chmod(0o600)

    f1 = tmp_path / "transcript.md"
    f1.write_text("content")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = json.dumps({"token": "valid_token"})

    # Set up separate mock objects to control list vs create responses
    mock_list_execute = MagicMock(return_value={"files": []})
    mock_list_request = MagicMock()
    mock_list_request.execute = mock_list_execute

    mock_create_folder_execute = MagicMock(return_value={"id": "new-folder-id"})
    mock_create_folder_request = MagicMock()
    mock_create_folder_request.execute = mock_create_folder_execute

    mock_create_file_execute = MagicMock(return_value={"id": "uploaded-file-id"})
    mock_create_file_request = MagicMock()
    mock_create_file_request.execute = mock_create_file_execute

    mock_files = MagicMock()
    mock_files.list.return_value = mock_list_request
    # First create = folder creation, subsequent = file upload
    mock_files.create.side_effect = [
        mock_create_folder_request,
        mock_create_file_request,
    ]

    mock_service = MagicMock()
    mock_service.files.return_value = mock_files

    with (
        patch(
            "google.oauth2.credentials.Credentials.from_authorized_user_file",
            return_value=mock_creds,
        ),
        patch("googleapiclient.discovery.build", return_value=mock_service),
        patch("googleapiclient.http.MediaFileUpload"),
    ):
        upload_transcripts(mote_home, [f1], "Mote Transcripts")

    # folder_id should now be cached in token file
    saved_data = json.loads(token_path.read_text())
    assert saved_data.get("drive_folder_id") == "new-folder-id"
