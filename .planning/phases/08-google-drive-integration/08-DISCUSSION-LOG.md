# Phase 8: Google Drive Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 08-google-drive-integration
**Areas discussed:** OAuth2 credentials, Destination config, Upload behavior, Auth command UX

---

## OAuth2 Credentials

### How should users get Google OAuth credentials?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship client_id in code | Embed installed app client_id in package. Standard for open-source CLI tools. | ✓ |
| User creates own project | README instructs users to create Google Cloud project. More friction. | |
| Config file with bundled default | Ship credentials.json, let users override. | |

**User's choice:** Ship client_id in code
**Notes:** None

### Where should the OAuth refresh token be stored?

| Option | Description | Selected |
|--------|-------------|----------|
| ~/.mote/google_token.json | Next to config.toml, permissions 600. Consistent with existing layout. | ✓ |
| System keychain | macOS Keychain via keyring library. Overkill for personal tool. | |
| XDG data dir | ~/.local/share/mote/. Separates credentials from config. | |

**User's choice:** ~/.mote/google_token.json
**Notes:** None

---

## Destination Config

### Config section structure

| Option | Description | Selected |
|--------|-------------|----------|
| Simple list | [destinations] active = ["local"]. --destination flag overrides per-run. | ✓ |
| Per-destination sections | [destinations.drive] enabled = true. Each destination has own toggle. | |
| Flag-only, no config | No config section, --destination flag each time. | |

**User's choice:** Simple list
**Notes:** None

### Local files when --destination drive used

| Option | Description | Selected |
|--------|-------------|----------|
| Always write local | Local files always written. Drive is additive. | ✓ |
| Destination replaces local | Only upload to Drive, skip local. | |

**User's choice:** Always write local
**Notes:** Matches roadmap decision

---

## Upload Behavior

### Which format(s) to upload to Drive

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown only | Upload just .md file. Keeps Drive folder clean. | |
| All configured formats | Upload whatever formats user has configured. | ✓ |
| User picks in config | Separate config key for Drive formats. | |

**User's choice:** All configured formats
**Notes:** None

### Drive folder selection

| Option | Description | Selected |
|--------|-------------|----------|
| Named folder, auto-create | folder_name = "Mote Transcripts". Creates on first upload. | ✓ |
| Folder ID in config | User copies folder ID from Drive URL. | |
| Drive root | Upload to My Drive root. | |

**User's choice:** Named folder, auto-create
**Notes:** None

---

## Auth Command UX

### Behavior when auth already exists

| Option | Description | Selected |
|--------|-------------|----------|
| Show status, offer re-auth | Display email/token status, confirm before re-auth. | ✓ |
| Always re-auth | Always trigger new browser consent. | |
| Separate status command | --status flag for checking. | |

**User's choice:** Show status, offer re-auth
**Notes:** None

### Upload failure verbosity

| Option | Description | Selected |
|--------|-------------|----------|
| One-line warning | Brief warning with retry hint. | ✓ |
| Detailed error + retry hint | Full error with mote upload retry command. | |
| Silent with log | No terminal output, log to file. | |

**User's choice:** One-line warning
**Notes:** Selected preview showing `mote upload` retry hint

### Manual upload command

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add mote upload | mote upload [file] for manual/retry uploads. | ✓ |
| No separate command | Drive upload only automatic. | |

**User's choice:** Yes, add mote upload
**Notes:** Emerged from the upload failure warning preview mentioning retry

---

## Claude's Discretion

- Drive API scope selection
- Folder ID caching mechanism
- File naming convention on Drive
- mote upload behavior without arguments

## Deferred Ideas

None
