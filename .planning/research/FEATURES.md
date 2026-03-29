# Feature Research

**Domain:** macOS meeting transcription tool (Swedish/Scandinavian language focus)
**Researched:** 2026-03-28 (updated for v2.0 Integration & Polish milestone)
**Confidence:** HIGH for core v1 features; MEDIUM for notebooklm-py (unofficial API); HIGH for OAuth2 and audio-switching patterns

---

## Context: What Is Already Built (v1 Complete)

These features are implemented and passing tests — they are not in scope for v2 but inform dependencies:

- CLI record/transcribe flow (`mote record`, auto-transcribes after stop)
- KB-Whisper local engine + OpenAI Whisper API engine
- Markdown and plain text output with YAML frontmatter headers
- Model management (`mote models list/download/delete`)
- TOML config at `~/.mote/config.toml`
- `mote list` for past transcripts
- Orphan WAV detection (detection exists; retry UX is incomplete)
- `mote status` (PID file check)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `mote transcribe <file>` command | Power users always want to re-transcribe old recordings or process external WAV files; absence requires workarounds | LOW | Reuses existing `transcribe_file()` + `write_transcript()`. Only needs a new CLI command that reads a WAV path. Config-driven engine/language/model. |
| Retry failed transcription | On failure the WAV is already kept — users expect a one-step retry, not manual subprocess commands | LOW | The WAV retention on failure is already coded. Add: interactive prompt "Retry? [Y/n]" in the failure handler. Re-run same transcription call. |
| Orphaned WAV transcription offer | Recording crashes leave WAVs behind; users want to salvage them, not hunt for file paths | LOW | `find_orphan_recordings()` already exists. On `mote record` startup, if orphans found, offer "Transcribe now? [Y/n]" per orphan. |
| Config validation on startup | Users misconfigure engine names, models, paths; silent failure mid-transcription is worse than early error | LOW | Validate: engine is "local" or "openai"; if local, model alias valid; if openai, API key not empty; output dir writable. Raise `ClickException` before recording starts. |
| JSON output format | Machine-readable format for downstream tooling, programmatic analysis, and NotebookLM source uploads | LOW | Add `json` to output format list. Schema: `{date, duration, words, engine, language, model, transcript}`. Mirrors existing MD frontmatter fields. |
| Google Drive upload on transcription complete | Completing the workflow loop: capture → transcribe → Drive → NotebookLM; without this the user still has to manually copy files | MEDIUM | `google-api-python-client` + `google-auth-oauthlib`. One-time OAuth2 consent via `mote auth google`. Token persisted at `~/.mote/google_token.json`. Upload via `files().create()` with `MediaFileUpload`. |
| Auth command (`mote auth google`) | Drive integration is useless without a discoverable one-time setup command | LOW | `InstalledAppFlow.from_client_secrets_file(...).run_local_server(port=0)`. Save credentials to `~/.mote/google_token.json`. Clear confirmation message. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Auto-switch BlackHole audio routing | Eliminates the #1 setup friction: manually switching System Audio Output to BlackHole before each meeting and back after | MEDIUM | Requires `brew install switchaudio-osx`. Use `subprocess.run(["SwitchAudioSource", "-t", "output", "-s", "BlackHole 2ch"])` before recording; restore original device after. Must handle: device not found, SwitchAudioSource not installed (graceful degradation). |
| Silence detection warning | Catches misconfigured audio routing before the entire meeting is recorded as silence | LOW | RMS check in the existing sounddevice callback. If `np.sqrt(np.mean(indata**2)) < threshold` for N consecutive seconds, print a warning. Threshold ~-50 dBFS. Does not stop recording — warns only. |
| NotebookLM upload (`mote auth notebooklm`) | Completes the Drive → NotebookLM workflow step programmatically; no manual "Add Source" in the NotebookLM web UI | HIGH | Uses `notebooklm-py` (unofficial API). Requires Playwright for browser auth (`pip install "notebooklm-py[browser]"`). Fragile — undocumented Google internal APIs. Treat as best-effort. Gate behind explicit flag or config opt-in. |
| Configurable destinations | Users want control over where transcripts land: local only, Drive only, both, or NotebookLM | LOW | Config `[destinations]` section with boolean flags: `google_drive = true`, `notebooklm = false`. Override via `--destination drive,notebooklm` flag on `mote record`. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time live transcription (streaming during recording) | "I want to read along as it transcribes" | faster-whisper is optimized for complete audio segments; streaming adds pipeline complexity; partial results mislead users mid-meeting | Batch-after-stop with fast turnaround (medium model on Apple Silicon processes 60 min in ~3–5 min). Show audio levels live instead. |
| Speaker diarization | Valuable for multi-participant meetings | pyannote.audio requires HuggingFace gated model access, adds 2–4x processing time, poor accuracy on Swedish | Out of scope for v2. JSON output with timestamps allows manual annotation. |
| Auto-start on meeting detection | "Start automatically when I join a Zoom call" | Requires process monitoring, OS-level hooks, fragile across app versions, privacy consent concerns | Chrome extension one-click start; CLI alias `alias mr='mote record'` |
| Auto-download models | "It should just work" | Multi-GB files downloaded without consent; breaks air-gapped setups; silent hang = bad UX | Explicit `mote models download <name>` with size shown first |
| Aggressive auto-routing (always-on BlackHole) | "Just always route to BlackHole" | Audio stops reaching speakers; user hears nothing during meetings; requires Multi-Output Device setup (manual step in Audio MIDI Setup) | Only switch output at `mote record` start, restore immediately on stop |
| notebooklm-py as primary integration | "Automate NotebookLM completely" | Uses undocumented internal Google APIs — no stability guarantee; Playwright browser dep adds 100+ MB; auth breaks when Google changes cookie structure | Google Drive push is the stable primary path; NotebookLM then picks up files from Drive. notebooklm-py is an optional enhancement. |

---

## Feature Behavior Patterns (v2 Research)

### OAuth2 Installed-App Flow for Google Drive

**Pattern (HIGH confidence — official docs):**
1. Developer creates OAuth2 credentials in Google Cloud Console, downloads `client_secret.json`
2. Ship `client_secret.json` inside the package (or prompt user to provide path)
3. On `mote auth google`: call `InstalledAppFlow.from_client_secrets_file(secrets_path, scopes=["https://www.googleapis.com/auth/drive.file"]).run_local_server(port=0)`
4. `run_local_server(port=0)` opens default browser, catches the redirect on a random local port, returns `credentials`
5. Serialize credentials to `~/.mote/google_token.json` via `credentials.to_json()`
6. On subsequent runs: load from token file; if expired, `credentials.refresh(Request())` handles it automatically
7. Upload: `service.files().create(body={"name": filename, "parents": [folder_id]}, media_body=MediaFileUpload(path, resumable=False)).execute()`

**Scope note:** `drive.file` scope is least-privileged — only access files the app created. Sufficient for upload use case.

**Token refresh:** `google-auth` handles access token refresh automatically using the stored refresh token. No user re-authentication needed until refresh token expires (typically 7 days for test apps; indefinite for published apps).

**Credential distribution problem:** Bundling `client_secret.json` in a public GitHub repo exposes the OAuth client ID/secret. Standard approach for personal/open-source tools: document that users must create their own Google Cloud project and download their own `client_secret.json`. Store at `~/.mote/client_secret.json`.

### notebooklm-py Upload Workflow

**Pattern (MEDIUM confidence — unofficial, may break):**
1. `pip install "notebooklm-py[browser]"` installs Playwright dependency
2. `mote auth notebooklm` runs `notebooklm login` — opens browser to Google OAuth
3. Credentials cached in `~/.notebooklm/` (library-managed)
4. Upload: `notebooklm source add /path/to/transcript.md --notebook "Meeting Notes"` (CLI) or Python API call
5. Supports local files: MD, TXT, PDF, DOCX

**Stability risk:** Library uses undocumented internal Google APIs. Auth flow broke after a Google update in late 2024 and required a patch release. Treat as best-effort. Gate behind `--destination notebooklm` flag, not default behavior.

**Recommended pattern:** Make Google Drive the reliable primary path. NotebookLM can be connected to a Drive folder natively in the NotebookLM UI (Google Drive source type). This makes the Drive upload sufficient for the full workflow without notebooklm-py.

### `mote transcribe <file>` CLI Pattern

**Pattern (LOW complexity — reuses existing code):**
- New `@cli.command("transcribe")` with `@click.argument("file", type=click.Path(exists=True, path_type=Path))`
- Validate extension (`.wav` required; `faster-whisper` accepts WAV; OpenAI API accepts WAV/MP3/M4A)
- Call existing `get_wav_duration()` + `transcribe_file()` + `write_transcript()` — identical to the post-recording flow
- Engine/language/model/name resolved from config + CLI flags (same as `record` command)
- No WAV cleanup — the input file was provided by the user; do not delete it
- If `--destination` flag present, trigger Drive/NotebookLM upload same as `record` post-transcription

**Expected UX:** `mote transcribe meeting.wav --name "q1-planning"` — prints progress, writes outputs, prints summary line.

### Retry / Orphan Detection UX

**Current state:** WAV is kept on transcription failure with message "WAV kept at: {path}". Orphan detection runs on `mote record` startup and prints a warning list.

**v2 expected behavior:**

*Retry on failure:*
```
Transcription failed: [error]
WAV kept at: ~/.mote/recordings/2026-03-28_1400.wav
Retry? [Y/n]: Y
```
Re-run `transcribe_file()` with same parameters. On second failure, keep WAV, exit.

*Orphan offer on startup:*
```
Found 2 orphaned recording(s):
  2026-03-27_0900.wav (45.2 MB, ~24 min)
  2026-03-26_1430.wav (12.8 MB, ~7 min)
Transcribe them now? [Y/n/skip]:
  Y = transcribe all orphans (sequentially, same config)
  n = skip all, leave on disk
  skip = skip and add to ignore list
```

**Complexity:** LOW — the detection logic is done. Only the interactive prompt and transcription loop are new.

### Auto-Switch BlackHole Audio Routing

**Mechanism:** `switchaudio-osx` (`brew install switchaudio-osx`) provides `SwitchAudioSource` binary.

```
SwitchAudioSource -t output -c          # get current device name
SwitchAudioSource -t output -s "BlackHole 2ch"   # switch to BlackHole
SwitchAudioSource -t output -s "MacBook Pro Speakers"  # restore
```

**Python pattern:**
```python
import subprocess, shutil

def get_current_output() -> str | None:
    exe = shutil.which("SwitchAudioSource")
    if exe is None:
        return None
    result = subprocess.run([exe, "-t", "output", "-c"], capture_output=True, text=True)
    return result.stdout.strip() or None

def set_output(device_name: str) -> bool:
    exe = shutil.which("SwitchAudioSource")
    if exe is None:
        return False
    result = subprocess.run([exe, "-t", "output", "-s", device_name])
    return result.returncode == 0
```

**Graceful degradation:** If `SwitchAudioSource` is not installed, skip silently and print a one-time hint: "Install `brew install switchaudio-osx` to enable auto-routing." Do not fail.

**Config flag:** `auto_routing = true` in `[audio]` config section. Default: `false` until user opts in (avoids surprising speaker-output changes).

**Restore on Ctrl+C:** Must use try/finally to restore the original device even on KeyboardInterrupt. If restore fails (device disconnected), warn but do not error.

### RMS-Based Silence Detection

**Mechanism:** The existing `record_session()` uses a sounddevice InputStream callback that already receives `indata` (NumPy array). Add a rolling window RMS check in the callback.

```python
rms = float(np.sqrt(np.mean(indata ** 2)))
# Track if RMS stays below threshold for > N seconds
```

**Threshold:** `-50 dBFS` = `10 ** (-50/20)` ≈ `0.00316` in linear scale. This catches genuine silence (no audio from BlackHole) while tolerating low-level room noise.

**Warning behavior:**
- If silence persists for 30 seconds, print once: `"Warning: no audio detected — check BlackHole routing in System Settings > Sound > Output"`
- Print again every 60 seconds if still silent
- Do NOT stop recording — user may have a silent stretch legitimately

**Complexity:** LOW — the callback is already in place. Add a running counter and last-warned timestamp.

### Config Validation Pattern

**When:** At the start of `mote record` and `mote transcribe`, before any recording or file I/O.

**What to validate:**
| Config key | Rule | Error message |
|------------|------|---------------|
| `transcription.engine` | Must be "local" or "openai" | "Unknown engine '{value}'. Valid: local, openai" |
| `transcription.model` | If engine=local, model alias must be in MODELS dict | "Unknown model '{value}'. Run 'mote models list' to see valid names" |
| `transcription.model` | If engine=local, model must be downloaded | "Model '{name}' is not downloaded. Run 'mote models download {name}'" |
| `api_keys.openai` | If engine=openai, must be non-empty | "OpenAI API key not set. Run 'mote config set api_keys.openai YOUR_KEY'" |
| `output.dir` | Parent directory must be creatable | "Output directory '{path}' is not writable" |
| `transcription.language` | Must be in ["sv","no","da","fi","en"] | "Unknown language '{value}'. Valid: sv, no, da, fi, en" |

**Pattern:** Raise `click.ClickException` with a human-readable message. Exit before recording starts — never fail silently mid-recording.

### JSON Output Format

**Schema (mirrors existing MD frontmatter):**
```json
{
  "date": "2026-03-28T14:00:00.000000",
  "duration": 1440,
  "words": 5230,
  "engine": "local",
  "language": "sv",
  "model": "kb-whisper-medium",
  "transcript": "Full transcript text here..."
}
```

**Filename:** Same pattern as MD/TXT — `YYYY-MM-DD_HHMM[_name].json`

**Complexity:** LOW — `write_transcript()` already takes a `formats` list. Add `if "json" in formats:` branch using `json.dumps(...)` with `ensure_ascii=False` for Swedish characters.

**Config:** `format = ["markdown", "txt", "json"]` in `[output]` section. Default remains `["markdown", "txt"]` — JSON is opt-in.

---

## Feature Dependencies

```
[mote transcribe <file>]
    └──reuses──> [transcribe_file(), write_transcript()] (already built)
    └──enhanced by──> [Drive upload] (same post-transcription hook as record)

[Drive upload]
    └──requires──> [mote auth google] (OAuth token must exist)
    └──requires──> [google-api-python-client, google-auth-oauthlib] (new deps)

[mote auth google]
    └──requires──> [~/.mote/client_secret.json] (user must provide from GCP console)

[NotebookLM upload]
    └──requires──> [mote auth notebooklm] (Playwright browser login)
    └──requires──> [notebooklm-py[browser]] (new dep with Playwright)
    └──enhanced by──> [Drive upload] (recommended path: Drive → NotebookLM native source)

[Auto-routing]
    └──requires──> [switchaudio-osx] (brew dep, not pip-installable)
    └──enhanced by──> [silence detection] (if routing failed, silence detection catches it)

[Silence detection]
    └──depends on──> [sounddevice callback] (already in record_session())
    └──no new deps]

[Config validation]
    └──depends on──> [load_config()] (already built)
    └──depends on──> [MODELS dict, is_model_downloaded()] (already built)
    └──no new deps]

[JSON output]
    └──depends on──> [write_transcript()] (already built)
    └──no new deps]

[Retry / orphan UX]
    └──depends on──> [find_orphan_recordings()] (already built)
    └──depends on──> [transcribe_file()] (already built)
    └──no new deps]
```

### Dependency Notes

- **Drive upload requires user-created GCP credentials.** Cannot ship `client_secret.json` in a public repo. Users must create a Google Cloud project, enable Drive API, create an OAuth2 Desktop App credential, and download `client_secret.json` to `~/.mote/`. This is setup friction — document clearly in README.
- **notebooklm-py is a Playwright dependency.** Playwright downloads browser binaries (~100 MB). This must be a soft/optional dependency — do not add `notebooklm-py` to mandatory `dependencies` in pyproject.toml. Use an extras group: `[project.optional-dependencies] notebooklm = ["notebooklm-py[browser]"]`.
- **switchaudio-osx is a brew dep, not pip-installable.** Auto-routing must degrade gracefully when the binary is absent. Never make recording fail because SwitchAudioSource is missing.
- **Config validation runs before recording starts.** It must be fast (no network calls, no model loading). Purely in-memory checks against already-loaded config values.
- **JSON output has no new deps.** `json` is stdlib. Zero install friction.

---

## MVP Definition

### v2.0 Launch With

Minimum feature set for the v2.0 Integration & Polish milestone.

- [ ] `mote transcribe <file>` — core usability feature; reuses all existing logic; zero risk
- [ ] Retry failed transcription — low effort, closes a known UX gap
- [ ] Orphaned WAV offer on startup — low effort, pairs with existing detection
- [ ] Config validation on startup — prevents confusing mid-run failures
- [ ] JSON output format — zero new deps; enables downstream automation
- [ ] Google Drive upload + `mote auth google` — primary integration value
- [ ] Configurable destinations config section — needed for Drive + future NotebookLM
- [ ] Silence detection warning — low effort, high value for debugging routing issues
- [ ] Auto-switch BlackHole routing — biggest UX win; requires brew dep, must degrade gracefully

### Defer to v2.1 or v3

- [ ] NotebookLM upload via notebooklm-py — fragile unofficial API; Playwright dep; recommend Drive-as-intermediary pattern instead. Add only if user explicitly requests it.

### Future Consideration (v3+)

- [ ] Web dashboard (Flask + SSE) — substantial work; deferred per PROJECT.md
- [ ] Chrome extension — requires Flask server first
- [ ] Speaker diarization — poor Swedish accuracy; deferred
- [ ] Norwegian/Danish/Finnish KB-Whisper models — KB-Whisper is Swedish-only; needs different model strategy
- [ ] Transcript search history (SQLite FTS) — valuable only once archive grows large

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `mote transcribe <file>` | HIGH | LOW | P1 |
| Config validation | HIGH | LOW | P1 |
| Silence detection warning | HIGH | LOW | P1 |
| Retry / orphan UX | MEDIUM | LOW | P1 |
| JSON output format | MEDIUM | LOW | P1 |
| Google Drive upload | HIGH | MEDIUM | P1 |
| `mote auth google` | HIGH | LOW | P1 |
| Configurable destinations | MEDIUM | LOW | P1 |
| Auto-switch BlackHole routing | HIGH | MEDIUM | P2 |
| NotebookLM upload | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v2.0
- P2: Should have, fits v2.0 if time allows
- P3: Defer — fragility or complexity outweighs value for this milestone

---

## Competitor Feature Analysis

| Feature | Otter.ai / Fireflies | Jamie (bot-free, local) | Möte v1 (built) | Möte v2 (this milestone) |
|---------|----------------------|-------------------------|-----------------|--------------------------|
| Swedish language | Poor | 28+ languages (auto-detect) | KB-Whisper native | Same — no change |
| `transcribe <file>` | No | Yes | No | Yes |
| Retry failed job | No | Manual | Warning only | Interactive retry |
| Google Drive auto-push | Paid integration | Export only | No | Yes (OAuth2, API) |
| NotebookLM integration | No | No | No | Optional (notebooklm-py) |
| JSON output | No | No | No | Yes |
| Config validation | N/A | N/A | No | Yes (startup check) |
| Auto audio routing | No | No | No | Yes (SwitchAudioSource) |
| Silence detection | No | No | No | Yes (RMS warning) |

---

## Sources

- [OAuth 2.0 for Installed Applications — google-api-python-client](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html)
- [google-auth-oauthlib flow module reference](https://googleapis.dev/python/google-auth-oauthlib/latest/reference/google_auth_oauthlib.flow.html)
- [Drive API — Media Upload documentation](https://googleapis.github.io/google-api-python-client/docs/media.html)
- [notebooklm-py GitHub (teng-lin)](https://github.com/teng-lin/notebooklm-py)
- [notebooklm-py on PyPI](https://pypi.org/project/notebooklm-py/)
- [switchaudio-osx GitHub (deweller)](https://github.com/deweller/switchaudio-osx)
- [switchaudio-osx Homebrew formula](https://formulae.brew.sh/formula/switchaudio-osx)
- [Silence detection in sounddevice stream — GitHub issue #157](https://github.com/spatialaudio/python-sounddevice/issues/157)
- [Click advanced patterns — custom validation](https://click.palletsprojects.com/en/stable/advanced/)
- [JSON CLI output best practices (Kelly Brazil, 2021)](https://blog.kellybrazil.com/2021/12/03/tips-on-adding-json-output-to-your-cli-app/)
- [Transcript file formats: TXT/SRT/VTT/JSON guide (BrassTranscripts)](https://brasstranscripts.com/blog/transcription-file-formats-decision-guide-2026)
- [KB-Whisper announcement (KBLab, March 2025)](https://kb-labb.github.io/posts/2025-03-07-welcome-KB-Whisper/)
- [Google Drive file scope — drive.file least privilege](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)

---
*Feature research for: macOS Swedish meeting transcription tool (Möte) — v2.0 Integration & Polish*
*Researched: 2026-03-28*
