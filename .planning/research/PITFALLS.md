# Pitfalls Research

**Domain:** macOS meeting transcription tool (Swedish/Scandinavian audio, BlackHole capture, faster-whisper local inference) — v2.0 Integration & Polish additions
**Researched:** 2026-03-28 (v2.0 update; v1 pitfalls preserved below)
**Confidence:** HIGH — all major claims verified against official documentation and/or primary issue trackers

---

## Critical Pitfalls

### Pitfall 1: BlackHole Multi-Output Device Drift Causes Distortion Over Long Recordings

**What goes wrong:**
When capturing system audio via a BlackHole Multi-Output device (the standard setup to hear audio while also capturing it), progressive audio distortion begins after 20–30 minutes. The audio fades and eventually becomes inaudible on Apple Silicon Macs. This is a known bug in BlackHole itself on M1/M2 hardware and is not fixable in application code.

**Why it happens:**
The Multi-Output device configuration has clock drift issues on Apple Silicon. BlackHole 2ch must be the primary/clock device in any Aggregate or Multi-Output configuration. When it is not (e.g., AirPods or external headphones are set as clock source), sample rate mismatches cause progressive buffer corruption. Even with drift correction enabled, the bug surfaces on M1/M2 hardware.

**How to avoid:**
- Document for users that BlackHole 2ch must be set as the primary/clock device in Audio MIDI Setup
- In setup docs, show the exact Aggregate Device configuration (BlackHole 2ch as clock source, built-in output second with drift correction enabled)
- Consider adding a startup check that detects whether the recording device is named "BlackHole 2ch" and warns if not
- For capture-only use cases (no simultaneous playback needed), skip the Multi-Output device entirely and set BlackHole 2ch as the system output directly — this avoids the drift problem altogether

**Warning signs:**
- Audio from recordings sounds fine in the first 10 minutes but garbled later
- Users report "fading" audio or increasing static over the course of a meeting
- Distortion reproducible on Apple Silicon but not on Intel Macs

**Phase to address:** Audio capture foundation phase (the very first recording milestone). Setup documentation and device detection must ship before real use.

---

### Pitfall 2: BlackHole Audio Routing Restore Failure on Interrupted Recording

**What goes wrong:**
The v2.0 auto-switch feature will set the macOS system output to BlackHole before recording and restore the original device after. If the Python process is killed (SIGKILL, force-quit, power loss, crash) the restore never runs and the user's system output is stuck on BlackHole — no sound from speakers, headphones, etc. The user has no feedback about why audio has stopped working.

**Why it happens:**
Audio device restore requires `SwitchAudioSource` (or equivalent) to run in a finally/cleanup block. SIGKILL does not allow any Python cleanup code to execute. Even SIGTERM and SIGINT can be missed if signal handlers are not explicitly registered.

**How to avoid:**
- Read the current system output device name before switching: `SwitchAudioSource -c` (current device) and store it in a recovery file at `~/.mote/audio_restore.json`
- On every `mote record` startup, check for a recovery file. If it exists, offer to restore the audio device before starting a new recording
- Register explicit SIGINT and SIGTERM handlers that call the restore before exit; the `try/finally` in `record_session()` already exists — extend it with the restore call
- Document the manual recovery command in the error output: `SwitchAudioSource -s "Built-in Output"` (or whatever was saved)
- SIGKILL cannot be caught — the recovery file approach is the only protection for force-quit scenarios

**Warning signs:**
- User reports "no sound" after a recording session that was interrupted unexpectedly
- `~/.mote/audio_restore.json` exists at the start of a new recording session (indicates a previous unclean exit)

**Phase to address:** Auto-switch BlackHole routing phase. Recovery file must be written before the switch executes, not after.

---

### Pitfall 3: SwitchAudioSource Is a Brew Dependency — Not Guaranteed to Exist

**What goes wrong:**
Auto-switching audio routing depends on `SwitchAudioSource` (from `switchaudio-osx` Homebrew formula). This is not a Python package — it cannot be installed via pyproject.toml. If the user has not installed it, the auto-switch silently fails or raises `FileNotFoundError` from subprocess, and the recording starts capturing silence.

**Why it happens:**
`subprocess.run(["SwitchAudioSource", ...])` raises `FileNotFoundError` when the binary is not on PATH. This is not caught unless explicitly handled.

**How to avoid:**
- At startup, check for SwitchAudioSource with `shutil.which("SwitchAudioSource")` — if absent, warn the user and skip auto-switching (fall through to manual routing instructions), do not abort
- Treat auto-switching as a best-effort convenience feature, not a hard requirement
- Add SwitchAudioSource to the project README as an optional dependency with install instructions: `brew install switchaudio-osx`
- Never let a missing optional binary cause the main recording flow to fail

**Warning signs:**
- `FileNotFoundError: [Errno 2] No such file or directory: 'SwitchAudioSource'` in tracebacks
- Recording starts but captures silence, no error shown

**Phase to address:** Auto-switch BlackHole routing phase.

---

### Pitfall 4: Google OAuth — Refresh Token Not Issued Without `access_type=offline` and `prompt=consent`

**What goes wrong:**
The first OAuth authorization flow completes, credentials are saved to `~/.mote/google_token.json`, but on subsequent runs the access token has expired (tokens expire after 1 hour), the refresh token is missing from the saved credentials, and the upload either fails silently or triggers a new browser flow.

**Why it happens:**
Google only issues a refresh token on the first authorization with `access_type='offline'`. On subsequent authorizations where the user has already granted consent, Google does not return a new refresh token — so `credentials.refresh_token` is `None` in the stored file. Without a refresh token, `google-auth` cannot renew the access token automatically.

**How to avoid:**
- Always pass `access_type='offline'` and `prompt='consent'` to `InstalledAppFlow.from_client_secrets_file(...).run_local_server()` — `prompt='consent'` forces Google to reissue the refresh token on every authorization, including repeat flows
- After loading `token.json`, check `credentials.refresh_token is None` — if so, delete the file and re-run auth rather than failing mid-upload
- Check `credentials.valid` and call `credentials.refresh(Request())` before every Drive API call
- Store `google_token.json` at `~/.mote/google_token.json` with `chmod 600`

**Warning signs:**
- Drive uploads work on the first run but fail or open a browser on subsequent runs
- `google.auth.exceptions.RefreshError: Token has been expired or revoked`
- `credentials.refresh_token` is `None` after loading from file

**Phase to address:** Google Drive integration phase.

---

### Pitfall 5: Google OAuth — "Unverified App" Warning Blocks First-Time Authorization

**What goes wrong:**
When a user runs `mote auth google` for the first time, Google shows a full-page warning: "Google hasn't verified this app." Non-technical users are confused and may abandon setup. The warning cannot be bypassed by code — it requires the user to click "Advanced" then "Go to [app] (unsafe)".

**Why it happens:**
Any OAuth app requesting Drive scopes that has not been verified by Google shows this warning. Verification requires a privacy policy URL, domain verification, and Google review — impractical for a personal CLI tool. The warning is mandatory for unverified apps requesting sensitive scopes.

**How to avoid:**
- Use `drive.file` scope (not `drive` full access) — `drive.file` is less sensitive and the warning is still shown but the scope restriction reduces concern
- Document the warning in setup instructions with a screenshot and explicit steps: "Click Advanced > Go to Mote (unsafe)"
- Explain clearly in docs that the credentials are the user's own Google Cloud project — there is no third party involved
- Consider requesting only `drive.file` scope (access only to files the app creates), which is the minimum needed to upload transcripts

**Warning signs:**
- User reports OAuth flow stopped at a warning screen
- User says "it says the app is unsafe"

**Phase to address:** Google Drive integration phase — documentation must accompany the auth command.

---

### Pitfall 6: Google OAuth — The OOB (Out-of-Band) Copy-Paste Flow Is Deprecated

**What goes wrong:**
Older tutorials and blog posts show an OAuth flow where a code appears in the browser and the user pastes it into the terminal. This "OOB" flow was deprecated by Google in October 2022 and no longer works for new apps. Implementing it will result in an error.

**Why it happens:**
Many Python examples still show `flow.run_console()` which uses the OOB flow. The current required approach for installed applications is the loopback redirect: start a local HTTP server on a random port, set the redirect URI to `http://127.0.0.1:<port>`, and capture the authorization code from the redirect.

**How to avoid:**
- Use `flow.run_local_server(port=0)` — `port=0` lets the OS assign a free port; the loopback redirect URI is constructed automatically by `google-auth-oauthlib`
- Do not use `flow.run_console()` — it will fail with `redirect_uri_mismatch` or a deprecation error
- Register `http://localhost` and `http://127.0.0.1` as allowed redirect URIs in the Google Cloud Console OAuth credentials configuration

**Warning signs:**
- `redirect_uri_mismatch` error during OAuth flow
- Authorization page shows error instead of consent screen

**Phase to address:** Google Drive integration phase.

---

### Pitfall 7: notebooklm-py Uses Undocumented APIs That Break Without Warning

**What goes wrong:**
Google periodically updates internal RPC method IDs, endpoint paths, or response formats in NotebookLM. When this happens, `notebooklm-py` raises `RPCError` or returns `None` silently. Upload appears to succeed (no exception) but the source never appears in the notebook. The library is at v0.3.4 — young and API surface is volatile.

**Why it happens:**
`notebooklm-py` reverse-engineers Google's internal `batchexecute` endpoint. Google does not publish this interface or maintain backward compatibility. The library maintainer must discover and update changed method IDs reactively.

**How to avoid:**
- Treat NotebookLM upload as a best-effort destination, not a guaranteed delivery channel — always upload to Google Drive first, then attempt NotebookLM
- Wrap all `notebooklm-py` calls in `try/except` and surface failures as warnings, not errors — a failed NotebookLM upload should not cause the entire `mote record` command to fail
- Check the library's GitHub for open issues before shipping the NotebookLM phase
- Do not make the NotebookLM upload blocking — run it asynchronously or as a background task after the Drive upload completes
- Pin the `notebooklm-py` version in `pyproject.toml` and test against the pinned version; upgrade only intentionally

**Warning signs:**
- `RPCError` in traceback from notebooklm-py
- Upload function returns without error but no source appears in NotebookLM
- `if debug: "method ID has changed"` messages in library output

**Phase to address:** NotebookLM integration phase — must be built with graceful degradation from the start.

---

### Pitfall 8: notebooklm-py Session Cookies Expire Every 1–2 Weeks

**What goes wrong:**
`notebooklm-py` authenticates by storing Google session cookies (SID, SSID, SAPISID, etc.) in `~/.notebooklm/storage_state.json` via a Playwright browser session. These cookies expire every 1–2 weeks. When they expire, every upload call fails with HTTP 401/403. Unlike OAuth2, there is no refresh token mechanism — the user must re-run `mote auth notebooklm` (which opens a browser) every 1–2 weeks.

**Why it happens:**
The library mimics a browser session. Google's session cookies are not designed for programmatic reuse and have short lifetimes. There is no programmatic way to refresh them without a browser.

**How to avoid:**
- Display a clear error message when authentication fails: "NotebookLM session expired. Run `mote auth notebooklm` to re-authenticate."
- Detect the 401/403 error proactively by calling a lightweight auth-check call before attempting upload — fail fast with a helpful message rather than failing mid-upload
- Document in user setup that NotebookLM authentication requires periodic re-login (every 1–2 weeks)
- Persist the `storage_state.json` at `~/.mote/notebooklm_state.json` (not the library's default location) so it is alongside other mote credentials and included in the same backup/security guidance

**Warning signs:**
- NotebookLM uploads worked last week but now fail with authentication errors
- HTTP 401 or 403 from notebooklm-py calls
- User reports "it was working before"

**Phase to address:** NotebookLM integration phase.

---

### Pitfall 9: Config Validation Breaks Existing Users When New Keys Are Added

**What goes wrong:**
Adding startup config validation for new v2.0 config keys (e.g., `[destinations]`, `[google]` sections) causes the tool to exit with "invalid config" for existing users who have v1 config files without those sections — even if the new keys are optional with sensible defaults.

**Why it happens:**
Config validation commonly checks "is this key present and valid?" A v1 config file legitimately lacks v2 sections. If validation treats absent v2 keys as errors rather than applying defaults, every existing user's tool breaks on upgrade.

**How to avoid:**
- Distinguish between validation types:
  - **Fatal**: value is present but wrong type/invalid (e.g., `engine = "badvalue"`, `language = 123`)
  - **Non-fatal default**: key is absent → silently apply default, do not warn
- Add new config sections (`[destinations]`, `[google]`, `[audio]`) to `_write_default_config()` so new installs include them — but existing installs without them must work via fallback defaults in `load_config()`
- Never add a new required config key that breaks existing v1 configs without an explicit migration path
- Test validation with a v1-format config file (no new sections) and verify the tool still starts

**Warning signs:**
- Validation error on startup after upgrading to v2.0
- Error message references a key that the user never set
- Error only appears for existing users, not fresh installs

**Phase to address:** Config validation phase — must be designed with backward compatibility as the primary constraint.

---

### Pitfall 10: Silence Detection Threshold False Positives on Low-Level Meeting Audio

**What goes wrong:**
Silence detection warns "no audio signal detected" during a legitimate meeting because the threshold is set too high. The user wastes time rechecking audio routing when the routing is correct — just quiet. Conversely, a threshold set too low misses genuine BlackHole misconfiguration (the original purpose of the feature).

**Why it happens:**
Audio from video conferencing apps (Teams, Zoom) can legitimately be very quiet when no one is speaking. The energy-based silence detection floor varies by platform, meeting software, and user volume settings. A fixed threshold in dBFS will be wrong for some users.

**How to avoid:**
- Use a conservative threshold (e.g., -50 dBFS over a 5-second window) rather than a tight threshold — the goal is detecting complete silence (routing failure), not quiet audio
- Only warn after a sustained silence period (e.g., 10 seconds of RMS below threshold), not on momentary gaps
- Frame the warning clearly: "No audio detected — check that system output is set to BlackHole" rather than a generic "silence detected"
- Allow the threshold to be configured in `[audio]` config section for power users
- The existing `rms_db()` function already computes per-block dB values — implement silence detection as a sliding window over the same blocks already being processed, not a separate audio path

**Warning signs:**
- Users report false "silence" warnings during active meetings
- Warning triggers during normal speech pauses

**Phase to address:** Audio improvements phase (silence detection).

---

### Pitfall 11: `mote transcribe <file>` Must Handle Non-16kHz WAV Files

**What goes wrong:**
`mote transcribe <file>` is designed for "existing WAV files" — but users may point it at any WAV file (44.1kHz stereo, 48kHz, etc.). faster-whisper accepts arbitrary sample rates internally (it resamples), but the existing `write_wav()` function is hardcoded to 16kHz mono output. If the input WAV is passed directly to faster-whisper at the wrong sample rate without declaring the actual rate, transcription output will be garbled or empty.

**Why it happens:**
faster-whisper's `transcribe()` method accepts a file path and reads the WAV header — it does handle non-16kHz inputs correctly as of v1.x. The pitfall is not in faster-whisper itself but in validation: code that assumes the input is 16kHz mono and processes it accordingly (e.g., computing duration from file size) will produce incorrect results.

**How to avoid:**
- Read the WAV header with Python's `wave` module before transcribing: verify sample rate, channels, and bit depth; display them to the user
- Pass the file path directly to `faster_whisper.WhisperModel.transcribe()` — do not pre-process or resample; let faster-whisper handle it
- Do not estimate duration from file size for user-provided files (formula only applies to 16kHz mono 16-bit)
- Reject clearly unsupported formats (e.g., MP3, M4A, video files) with a helpful error message before attempting transcription

**Warning signs:**
- Empty or nonsense transcription output from a file that plays correctly in VLC
- Duration estimate shown to user is wrong
- `wave.Error: file does not start with RIFF id` for non-WAV inputs

**Phase to address:** `mote transcribe` command phase.

---

### Pitfall 12: faster-whisper WhisperModel Is Not Safe to Call Concurrently from Multiple Threads

**What goes wrong:**
If Flask request threads or background threads call `model.transcribe()` on a single shared `WhisperModel` instance concurrently, results become non-deterministic and may crash or produce garbled output. CTranslate2 models are designed for sequential use from one caller at a time.

**Why it happens:**
CTranslate2's internal inference state is not protected by a lock within the model object. The library's own documentation recommends multiple model instances (via `num_workers` or separate instantiation) for parallelism rather than shared access.

**How to avoid:**
- Hold the `WhisperModel` as a singleton loaded once at startup
- Protect all calls to `model.transcribe()` with a `threading.Lock()`
- Since Möte is a single-user tool doing one transcription at a time, this is straightforward: one lock, one model, one transcription job
- Never pass the model object to Flask route handlers directly — route handlers should enqueue a transcription job and return immediately

**Warning signs:**
- Intermittent transcription failures only when web UI and CLI are used simultaneously
- Python crashes with a segfault inside CTranslate2 native code

**Phase to address:** Transcription engine phase. The lock must wrap model.transcribe() from day one.

---

### Pitfall 13: KBLab Models Require Exact faster-whisper + tokenizers Version Compatibility

**What goes wrong:**
Loading `KBLab/kb-whisper-large` (or any kb-whisper variant) with an older version of faster-whisper raises:
```
Exception: data did not match any variant of untagged enum ModelWrapper at line 264903 column 3
```
The error occurs in `tokenizers.Tokenizer.from_file()` during model initialization, not during transcription.

**Why it happens:**
The KBLab models use a tokenizer format that requires a newer version of the `tokenizers` library than older faster-whisper releases pin. faster-whisper 0.10.x with tokenizers 0.15.x is known to fail. The issue is not with the model files themselves.

**How to avoid:**
- Pin faster-whisper to a version known to work with KBLab models (verify against the HuggingFace discussion board for kb-whisper-large before locking versions)
- In `pyproject.toml`, set `faster-whisper>=1.0.0` and `tokenizers>=0.19.0` (verify exact versions at implementation time)
- Add a model load smoke-test to the test suite: load each supported model and transcribe 1 second of silence — fail fast rather than fail at transcription time
- Document that stale `~/.cache/huggingface/hub` directories for old model versions can also cause this — instruct users to clear cache if they upgrade model versions

**Warning signs:**
- Model loads fine in dev environment but fails on a fresh install
- `Exception: data did not match any variant of untagged enum ModelWrapper` in traceback
- Error occurs at startup/model-load time, not during transcription

**Phase to address:** Transcription engine phase. Dependency pinning must be validated before model management UI is built.

---

### Pitfall 14: Flask Dev Server Blocks All Requests Once an SSE Connection Is Open

**What goes wrong:**
Flask's built-in development server is single-threaded by default. Once a browser opens the SSE `/events` endpoint (an infinite streaming response), the server cannot serve any other HTTP request — buttons in the web UI stop working, API calls time out, and the page appears frozen.

**Why it happens:**
The SSE stream is an infinite generator that never completes. A single-threaded server holds the one available worker thread open for the duration of the SSE connection, starving all other routes.

**How to avoid:**
- Always launch Flask with `app.run(threaded=True)` — this is the minimum fix for the dev server
- For the final deployed form (even as a local tool), use a proper WSGI server: `waitress` is the recommended choice for a single-user local tool (pure Python, no Gunicorn dependency, works on macOS without gevent)
- Structure SSE to use a `queue.Queue` per client: audio level monitor thread pushes events onto the queue, SSE generator pops from it — thread-safe by design
- Wrap the SSE generator with Flask's `stream_with_context()` to ensure request context is preserved across yields

**Warning signs:**
- Web UI completely stops responding after the status page loads
- All API calls hang indefinitely after SSE connection is established
- Works fine when SSE tab is closed, breaks when opened

**Phase to address:** Web UI phase. threaded=True and waitress must be used from the first SSE implementation.

---

### Pitfall 15: sounddevice Callback Thread Must Never Block

**What goes wrong:**
Placing any blocking operation (file I/O, network calls, `print()`, lock acquisition, queue.get() with a timeout) inside the `sounddevice` InputStream callback causes audio buffer overflow. Overflowed input data is silently discarded, creating gaps in the recorded audio that are not recoverable.

**Why it happens:**
The PortAudio callback runs on a real-time audio thread with a hard deadline. Any operation that blocks longer than the buffer duration (typically 10–20ms) causes an overflow. The callback does not raise an exception — it silently drops frames and sets a status flag.

**How to avoid:**
- The callback should do exactly one thing: `q.put_nowait(indata.copy())` where `q` is a `queue.Queue`
- A separate consumer thread drains the queue and writes to the WAV file
- Pass `dtype='int16'` and `channels=1` to avoid format conversion inside the callback
- Monitor the `status` parameter passed to the callback: if `status.input_overflow`, log a warning (but do not log from inside the callback itself — use a flag checked by the consumer thread)
- Never call `print()`, `logging.*`, or `time.sleep()` inside the callback

**Warning signs:**
- Occasional silent gaps or clicks in recorded audio
- `status.input_overflow` flag is set in callback status checks
- Problem worsens under system load (other apps running)

**Phase to address:** Audio capture foundation phase. The queue-based pattern must be the initial design, not a refactor.

---

### Pitfall 16: Chrome Native Messaging — stdout Corruption Breaks the Protocol

**What goes wrong:**
Any output written to stdout from the native messaging host process — including Python's default print(), logging to stdout, or exception tracebacks — corrupts the binary message stream. Chrome receives malformed length-prefixed data and the extension silently stops receiving messages.

**Why it happens:**
Chrome native messaging reads raw bytes from the host's stdout. The protocol is: 4 bytes (little-endian uint32) encoding the JSON payload length, followed by exactly that many UTF-8 bytes of JSON. Any extraneous byte on stdout (even a newline from print()) causes Chrome to mis-parse the length prefix and misalign all subsequent reads.

**How to avoid:**
- Redirect all logging to stderr at process start: `logging.basicConfig(stream=sys.stderr)`
- Never call `print()` anywhere in the native messaging host module
- Wrap stdout in binary mode: `sys.stdout = sys.stdout.buffer` (or always write directly to `sys.stdout.buffer`)
- Use Python's `struct.pack('<I', len(msg))` for the length prefix — the `<` specifier ensures little-endian regardless of host platform
- Write a dedicated `send_message(data: dict)` function and use it exclusively; no direct stdout writes elsewhere

**Warning signs:**
- Extension receives no messages after the host starts
- Chrome extension console shows "Disconnected from native messaging host"
- Host process exits immediately with code 0 (stdout was closed by Chrome after parsing failure)

**Phase to address:** Chrome extension phase. The message framing must be the first thing implemented and unit tested before any feature logic.

---

### Pitfall 17: Chrome Native Messaging — Manifest Registration Path Must Be Absolute and Extension ID Must Be Exact

**What goes wrong:**
The native messaging host manifest (JSON file in `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/`) must have an absolute path to the host executable in its `"path"` field. Relative paths silently fail. Additionally, `"allowed_origins"` must list the exact extension ID — wildcards are not permitted. Any mismatch means Chrome refuses to launch the host with no useful error.

**Why it happens:**
macOS Chrome resolves the manifest path relative to nothing — it must be absolute. Extension IDs change between unpacked (development) and published (CWS) extension builds. Developers often hardcode the development ID and forget to update it for production.

**How to avoid:**
- Generate the manifest file at install time (post-install script) using the actual absolute path of the installed executable
- Document clearly that the extension ID in `allowed_origins` must match the Chrome extension's ID, and that this ID differs between dev and production
- Provide a `mote install-extension` CLI command that writes the manifest to the correct location with the correct path and prompts the user to paste their extension ID
- Do not bundle a pre-filled manifest in the repository

**Warning signs:**
- Native messaging host never launches (no process appears in Activity Monitor)
- Chrome extension background logs "Error when communicating with the native messaging host" on connect
- No error shown for path problems — just silent failure

**Phase to address:** Chrome extension phase.

---

### Pitfall 18: WAV File Size for Long Meetings Grows to Hundreds of Megabytes

**What goes wrong:**
At 16kHz mono 16-bit, audio accumulates at ~1.9 MB/min. A 1-hour meeting produces a ~110 MB WAV file. This is held entirely in the temp directory during recording and transcription. On machines with limited disk space (common on MacBook Air configurations), recordings can fail mid-session or transcription can fail to read the file.

**Why it happens:**
WAV is uncompressed PCM. The format is correct for Whisper (which expects PCM), but the lack of compression means disk usage grows linearly with meeting duration.

**How to avoid:**
- Check available disk space at recording start and warn if less than 500 MB free (enough for ~4 hours)
- Write audio to a named temp file using `tempfile.NamedTemporaryFile(delete=False, suffix='.wav')` rather than buffering in memory — never accumulate numpy arrays in a list across an entire meeting
- Delete the WAV file immediately after faster-whisper returns its result (do not defer cleanup)
- Document storage requirements (1.9 MB/min, ~110 MB/hour) in setup docs

**Warning signs:**
- Recording fails or freezes after ~30–40 minutes
- `OSError: [Errno 28] No space left on device` during recording
- Python MemoryError if accidentally buffering audio in a list instead of writing incrementally

**Phase to address:** Audio capture foundation phase (incremental write pattern) and temp file cleanup (transcription phase).

---

### Pitfall 19: Signal Handling — SIGINT Cleanup Skips atexit Handlers if Not Explicitly Wired

**What goes wrong:**
Registering cleanup functions with `atexit.register()` does not guarantee they run when the user presses Ctrl+C in the CLI. If a sounddevice stream is open, the WAV file is partially written, or a Flask server is running in a thread, Ctrl+C may leave the process in a broken state with orphaned temp files and an incomplete WAV.

**Why it happens:**
Python converts SIGINT to `KeyboardInterrupt` and propagates it, which may or may not trigger atexit handlers depending on where the exception is caught. More critically, SIGTERM (sent by process managers or `kill`) does not trigger atexit at all by default.

**How to avoid:**
- Register an explicit SIGINT handler that stops the recording stream, flushes the WAV file, and calls `sys.exit(0)` — which does trigger atexit
- Register a SIGTERM handler with the same logic
- Use `try/finally` blocks around the main recording loop to ensure the sounddevice stream is always stopped and the WAV file is always closed
- Use `tempfile.NamedTemporaryFile(delete=False)` and track the path; clean it up in the finally block and in atexit

**Warning signs:**
- Stale `.wav` files accumulating in `/tmp/` after interrupted recordings
- sounddevice stream left open (heard as continuous audio capture from the OS side)
- Flask server thread not shut down on Ctrl+C (port remains bound)

**Phase to address:** CLI phase (signal handling must be part of the initial recording loop design).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Load WhisperModel inside Flask route handler | Simpler startup | Model reloads on every transcription — 5–10 second penalty per request | Never |
| Use Flask dev server without threaded=True | Fast to start | SSE blocks all other requests from first connection | Never |
| Buffer all audio in a list before writing WAV | Simpler recording loop | Memory exhaustion on long meetings (~110 MB/hour in RAM) | Never |
| Hardcode extension ID in native messaging manifest | Skip setup complexity | Extension stops working when published to CWS | MVP only if dev/personal use |
| Skip token.json persistence, re-authorize every run | No file management needed | User must open browser for every Drive upload | Never |
| Write debug logs to stdout in native messaging host | Easy debugging | Corrupts Chrome message stream immediately | Never |
| Run sounddevice blocking mode instead of callback | Simpler threading | Cannot stop recording cleanly on signal; blocks main thread | Prototyping only |
| Make NotebookLM upload blocking (fail on error) | Simpler error handling | A transient API change fails the entire record workflow | Never — always best-effort |
| Skip audio device restore recovery file | Simpler code | User stuck on BlackHole output after any crash | Never |
| Validate all config keys as required | Simplest validation logic | Breaks all existing v1 users on upgrade | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| BlackHole via sounddevice | Query devices by index (index changes across reboots) | Query by name: find device where `name` contains `"BlackHole 2ch"` |
| faster-whisper KBLab models | Pass `model_size_or_path="kb-whisper-large"` (not a HuggingFace repo path) | Pass the full HuggingFace repo ID: `"KBLab/kb-whisper-large"` |
| faster-whisper language detection | Rely on auto-detect for Swedish | Always pass `language="sv"` explicitly — auto-detect on the first 30 seconds can misidentify Swedish as Norwegian, Danish, or English |
| Google Drive API | Assume OAuth token is valid on re-run | Always call `credentials.refresh(Request())` before every API call; check `credentials.valid` |
| Google Drive OAuth | Call `flow.run_console()` (OOB flow) | Call `flow.run_local_server(port=0)` — OOB is deprecated and no longer works |
| Google Drive OAuth | Request full `drive` scope | Request `drive.file` scope only — upload transcripts created by Mote, least-privilege |
| notebooklm-py | Treat upload failure as fatal error | Wrap in try/except; surface as warning; Drive upload is the primary destination |
| notebooklm-py | Skip version pinning | Pin to tested version in pyproject.toml; undocumented API changes break without warning |
| SwitchAudioSource | Assume binary is always present | Use `shutil.which()` to check; degrade gracefully if absent |
| Config validation | Treat absent v2 keys as errors | Treat absent keys as "use default"; only error on present-but-invalid values |
| Chrome native messaging | Use `json.dumps()` + `print()` to send messages | Use `sys.stdout.buffer.write(struct.pack('<I', len(msg)) + msg.encode())` |
| Flask SSE | Yield events from a direct generator reading shared state | Use `queue.Queue` per client; SSE generator blocks on `q.get(timeout=1)` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading WhisperModel on each transcription call | 5–15 second delay before transcription starts; high memory churn | Load model once at application start; hold as singleton | Every transcription |
| Using `float32` compute_type on Apple Silicon CPU | Transcription uses only 1 CPU core; 3–5x slower than int8 | Use `compute_type="int8"` on CPU; this is the fastest option on Apple Silicon without GPU | Always on Apple Silicon |
| Writing audio to a growing in-memory list | RAM grows ~1.9 MB/min; Python GC pressure increases | Write directly to WAV file in callback consumer thread | Recordings over ~15 minutes |
| Blocking on notebooklm-py upload in recording loop | Recording flow hangs if NotebookLM API is slow or down | Run NotebookLM upload after Drive upload in a separate step or background task | Any time NotebookLM is slow |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing `credentials.json` (OAuth client secret) in the project repo | Exposes OAuth client secret; anyone can impersonate the app | Add `credentials.json` to `.gitignore`; document that users must create their own Google Cloud project |
| Storing `google_token.json` in the project repo | Exposes valid refresh token; attacker gains full Drive access | Add `google_token.json` to `.gitignore`; store in `~/.mote/` with `chmod 600` |
| Storing `notebooklm_state.json` in the project repo | Exposes Google session cookies; attacker gains NotebookLM account access | Add to `.gitignore`; store in `~/.mote/` with `chmod 600` |
| Flask web UI binding to `0.0.0.0` | Anyone on the local network can control recordings and read transcripts | Always bind to `127.0.0.1` only; this is already a stated constraint but must be enforced in code, not just docs |
| TOML config file with API keys world-readable | API keys (OpenAI, Mistral) readable by other local users or processes | Set config file permissions to `600` on creation; warn if permissions are too open at startup |
| Requesting `drive` (full) scope for OAuth | App can read, modify, and delete all files in the user's Drive | Request `drive.file` scope — Mote only needs to create transcript files |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent recording start when BlackHole is not the system output | User records an entire meeting, gets a silent transcript | Validate device at recording start; refuse to record with a clear error message and setup instructions |
| No disk space check before recording | Recording fails mid-meeting with an OS error | Check available disk space at recording start; warn if < 500 MB free |
| "Unverified app" OAuth warning with no documentation | User abandons setup; reports the tool as broken | Pre-emptive docs with screenshot of the warning and exact steps to proceed |
| NotebookLM auth expires every 1–2 weeks with no clear message | User thinks the feature is broken; no indication of what to do | Clear error: "NotebookLM session expired. Run `mote auth notebooklm`" |
| Audio stuck on BlackHole after crash | User has no system audio; unclear what happened | Recovery file + clear message on next startup: "Previous recording left audio routing on BlackHole — restoring" |
| Config validation error on startup for v1 users upgrading | Tool is broken immediately after upgrade | Backward-compatible validation: absent keys use defaults, never error |
| Ambiguous "silence detected" warning during normal pauses | User interrupts or reconfigures during valid meeting | Only warn after 10+ continuous seconds of silence; phrase as routing check, not generic silence |
| No path shown after transcript is written | User cannot find the transcript | Always print absolute path of every output file |

---

## "Looks Done But Isn't" Checklist

- [ ] **Google Drive auth:** Token refresh works on second run (not just first) — test by deleting `google_token.json` access token field and running again without re-authorizing
- [ ] **Google Drive auth:** `access_type='offline'` and `prompt='consent'` are both set — verify by inspecting the authorization URL logged during `mote auth google`
- [ ] **Google Drive scope:** App requests `drive.file` not `drive` — verify in Google Cloud Console OAuth consent screen configuration
- [ ] **NotebookLM failure is non-fatal:** Drive upload succeeds even if NotebookLM raises `RPCError` — test by mocking a notebooklm failure
- [ ] **NotebookLM session expiry error is clear:** Running upload with expired cookies shows "run `mote auth notebooklm`" not a Python stack trace
- [ ] **Audio routing restore:** Running `mote record` and pressing Ctrl+C restores the original system output device — verify with `SwitchAudioSource -c` before and after
- [ ] **Audio routing recovery file:** Sending SIGKILL to a recording process leaves `~/.mote/audio_restore.json`; next `mote record` startup detects and restores
- [ ] **SwitchAudioSource absent:** Removing SwitchAudioSource from PATH does not break `mote record` — it warns and continues with manual routing instructions
- [ ] **Config validation backward compat:** Running v2 code against a v1 config file (no `[destinations]` section) starts without error
- [ ] **Config validation catches bad values:** Setting `engine = "invalid"` in config.toml produces a clear error at startup, not mid-transcription
- [ ] **Silence detection threshold:** Recording a quiet-but-active meeting does not trigger the silence warning (test at -45 dBFS sustained)
- [ ] **mote transcribe with non-16kHz file:** Passing a 44.1kHz stereo WAV produces a transcript (not an error or garbage)
- [ ] **Orphaned WAV handling:** Re-running `mote record` after a crash that left a WAV file detects and offers retry
- [ ] **Audio capture:** Recording produces non-empty WAV file AND the audio is actually meeting audio (not silence, not mic noise) — verify by checking waveform, not just file size
- [ ] **Transcription:** Model loads without error AND produces Swedish text output (not English) — test with a known Swedish audio sample
- [ ] **Signal handling:** Ctrl+C during recording stops the stream cleanly, no orphaned processes — check with `ps aux` after interrupt
- [ ] **Temp file cleanup:** WAV file is deleted after successful transcription AND after failed transcription AND after Ctrl+C — test all three cases

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Audio stuck on BlackHole after crash | LOW | Run `SwitchAudioSource -s "Built-in Output"` (or check `~/.mote/audio_restore.json` for the saved device name) |
| notebooklm-py API breakage | LOW | Pin to previous working version; continue using Drive upload; wait for library update |
| NotebookLM session expired | LOW | Run `mote auth notebooklm`; re-authenticate in browser |
| Google OAuth refresh token missing from token.json | LOW | Delete `~/.mote/google_token.json`; run `mote auth google` to re-authorize |
| Config validation breaks on upgrade | LOW | Add missing sections to config.toml manually, or delete and recreate (will lose custom settings) |
| BlackHole drift distortion on M1/M2 | LOW | Change to capture-only mode (set BlackHole 2ch as system output, use earphones directly) |
| KBLab tokenizer version mismatch | LOW | `rm -rf ~/.cache/huggingface/hub/models--KBLab*` then upgrade faster-whisper and re-download |
| Chrome extension ID mismatch in manifest | LOW | Re-run `mote install-extension` with correct ID; reload extension in Chrome |
| Orphaned WAV temp files | LOW | `rm ~/.mote/recordings/mote_*.wav` |
| Flask port still bound after crash | LOW | `lsof -i :PORT | grep LISTEN` then `kill -9 PID` |
| WhisperModel loaded multiple times, OOM | MEDIUM | Restart application; ensure model is a module-level singleton not per-request |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| BlackHole drift distortion on M1/M2 | Audio capture foundation | Record a 30-minute test session; check audio for distortion |
| Audio routing restore failure on crash | Auto-switch routing phase | SIGKILL recording process; verify audio_restore.json written; verify next startup restores device |
| SwitchAudioSource not installed | Auto-switch routing phase | Remove binary from PATH; verify mote record still starts with helpful warning |
| Google OAuth refresh token missing | Google Drive integration phase | Delete token.json; run upload; verify no browser window opened on second run |
| Google OAuth unverified app warning | Google Drive integration phase | Document in setup guide with screenshot before shipping |
| Google OAuth OOB flow deprecated | Google Drive integration phase | Verify `run_local_server(port=0)` is used; never `run_console()` |
| notebooklm-py API instability | NotebookLM integration phase | Mock RPCError; verify Drive upload still completes |
| notebooklm-py session expiry | NotebookLM integration phase | Use expired cookies; verify clear error message |
| Config validation backward compat | Config validation phase | Test v1 config file against v2 validation code; must start clean |
| Silence detection false positives | Audio improvements phase | Test at low-but-active audio levels; verify no false warning |
| mote transcribe non-16kHz files | mote transcribe phase | Pass 44.1kHz WAV; verify output |
| WhisperModel concurrency / thread safety | Transcription engine | Run transcription while Flask web UI is open; verify no crashes |
| KBLab tokenizer version mismatch | Transcription engine | Fresh `pip install` in empty venv; verify model loads without error |
| Flask SSE blocks all requests | Web UI | Connect to SSE endpoint; verify recording control buttons still respond |
| sounddevice callback must not block | Audio capture foundation | Record 5 minutes; inspect WAV for gaps or overflow warnings |
| Chrome native messaging stdout corruption | Chrome extension | Verify JSON messages received by extension with no debug print() calls present |
| Chrome native messaging absolute path | Chrome extension | Uninstall and reinstall; verify extension connects without manual manifest editing |
| WAV file size and disk space | Audio capture foundation | Estimate size at recording start; verify 1-hour recording produces ~110 MB file |
| Signal handling and temp file cleanup | CLI phase | Press Ctrl+C during recording; verify no orphaned files in recordings dir |

---

## Sources

**v2.0 Integration & Polish (2026-03-28):**
- [notebooklm-py GitHub — teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) — stability warning, unofficial API, MIT license
- [notebooklm-py Troubleshooting docs](https://github.com/teng-lin/notebooklm-py/blob/main/docs/troubleshooting.md) — RPC method ID changes, session expiry, rate limiting
- [notebooklm-py PyPI 0.1.4](https://pypi.org/project/notebooklm-py/0.1.4/) — package metadata, Python 3.10+ requirement
- [Google OAuth 2.0 — Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Google OAuth 2.0 for Installed Applications](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html)
- [Google OAuth Loopback Migration Guide](https://developers.google.com/identity/protocols/oauth2/resources/loopback-migration) — OOB deprecation confirmed
- [Google Drive API scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth) — drive.file vs full drive scope
- [Google OAuth Troubleshoot authentication](https://developers.google.com/workspace/drive/labels/troubleshoot-authentication-authorization)
- [Google Cloud — Unverified apps](https://support.google.com/cloud/answer/7454865) — verification requirements for sensitive scopes
- [Google Cloud — When is verification not needed](https://support.google.com/cloud/answer/13464323) — personal project exceptions
- [google-api-python-client Issue #807 — OAuth2 token not refreshing](https://github.com/googleapis/google-api-python-client/issues/807)
- [github.com/deweller/switchaudio-osx](https://github.com/deweller/switchaudio-osx) — SwitchAudioSource CLI tool
- [switchaudio-osx Homebrew formula](https://formulae.brew.sh/formula/switchaudio-osx)
- [switchaudio-osx Issue #34 — -t system flag behavior](https://github.com/deweller/switchaudio-osx/issues/34)
- [python-sounddevice Issue #394 — sounddevice reset hangs](https://github.com/spatialaudio/python-sounddevice/issues/394)
- [Simon Willison TIL — Google OAuth for a CLI application](https://til.simonwillison.net/googlecloud/google-oauth-cli-application) — OOB deprecation, loopback flow

**v1.0 Foundation (2026-03-27):**
- [BlackHole GitHub — Multi-Output and Aggregate Devices wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Aggregate-Device)
- [BlackHole GitHub — Issue #274: Recorded sound distorts after 20-30 minutes](https://github.com/ExistentialAudio/BlackHole/issues/274)
- [KBLab/kb-whisper-large HuggingFace — Discussion #15: Error when using this model from faster-whisper](https://huggingface.co/KBLab/kb-whisper-large/discussions/15)
- [faster-whisper GitHub — Discussion #406: Concurrent requests](https://github.com/SYSTRAN/faster-whisper/discussions/406)
- [faster-whisper GitHub — Issue #1207: Inconsistent Transcription Results with Async](https://github.com/SYSTRAN/faster-whisper/issues/1207)
- [Chrome for Developers — Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Max Halford — Server-sent events in Flask without extra dependencies](https://maxhalford.github.io/blog/flask-sse-no-deps/)
- [python-sounddevice — Issue #187: Proper threading and thread-safety](https://github.com/spatialaudio/python-sounddevice/issues/187)
- [python-sounddevice — Issue #155: Explanation of Over/Underflow errors](https://github.com/spatialaudio/python-sounddevice/issues/155)

---
*Pitfalls research for: macOS Swedish meeting transcription tool (Möte) — v2.0 Integration & Polish*
*Researched: 2026-03-28*
