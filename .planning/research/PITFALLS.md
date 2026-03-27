# Pitfalls Research

**Domain:** macOS meeting transcription tool (Swedish/Scandinavian audio, BlackHole capture, faster-whisper local inference)
**Researched:** 2026-03-27
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

### Pitfall 2: BlackHole Requires Manual macOS System Output Routing — No API to Automate This

**What goes wrong:**
For BlackHole to capture system audio (Teams, Zoom calls), the macOS system output must be set to BlackHole 2ch (or a Multi-Output device including it). There is no macOS API accessible from Python to programmatically change the system output device. If users forget to switch, the recording captures silence.

**Why it happens:**
macOS restricts programmatic audio routing changes to privileged system APIs not available to unprivileged user-space applications. sounddevice and CoreAudio bindings cannot change the system default output device.

**How to avoid:**
- Emit a prominent warning at recording start if the detected input device is not "BlackHole 2ch"
- Use `sounddevice.query_devices()` to enumerate devices and detect BlackHole by name
- Write clear setup documentation with screenshots of Audio MIDI Setup
- Optionally: use `switchaudio-osx` (a CLI tool, `brew install switchaudio-osx`) to emit a shell command that changes the system output — but document this requires user permission and is a best-effort helper
- Never silently start a recording that will capture silence

**Warning signs:**
- Recorded WAV file contains silence or ambient room noise only
- `sounddevice.query_devices()` does not list any device named "BlackHole 2ch"

**Phase to address:** Audio capture foundation phase. Device validation must be built into the recording start flow.

---

### Pitfall 3: faster-whisper WhisperModel Is Not Safe to Call Concurrently from Multiple Threads

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

### Pitfall 4: KBLab Models Require Exact faster-whisper + tokenizers Version Compatibility

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

### Pitfall 5: Flask Dev Server Blocks All Requests Once an SSE Connection Is Open

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

### Pitfall 6: sounddevice Callback Thread Must Never Block

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

### Pitfall 7: Chrome Native Messaging — stdout Corruption Breaks the Protocol

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

### Pitfall 8: Chrome Native Messaging — Manifest Registration Path Must Be Absolute and Extension ID Must Be Exact

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

### Pitfall 9: Google Drive OAuth — Refresh Token Not Issued Without `access_type=offline` and `prompt=consent`

**What goes wrong:**
The first OAuth authorization flow completes, credentials are saved to `token.json`, but on subsequent runs the token has expired (access tokens expire after 1 hour), the refresh token is missing from the saved credentials, and the user is prompted for authorization again — or the upload fails silently.

**Why it happens:**
Google only issues a refresh token on the first authorization if `access_type='offline'` is specified. On subsequent flows, Google reuses the existing authorization and does not return a new refresh token — so `credentials.refresh_token` is `None` in `token.json`. Without a refresh token, the `google-auth` library cannot renew the expired access token automatically.

**How to avoid:**
- Always pass `access_type='offline'` and `prompt='consent'` to `InstalledAppFlow.from_client_secrets_file(...).run_local_server()` — `prompt='consent'` forces Google to reissue the refresh token even if the user previously authorized
- Check `credentials.valid` and call `credentials.refresh(Request())` before any Drive API call
- Store `token.json` in the user config directory (`~/.config/mote/`) with permissions 600
- If `credentials.refresh_token is None` after loading `token.json`, delete the file and re-run the authorization flow

**Warning signs:**
- Drive uploads work in dev (first run) but fail in production (subsequent runs)
- `google.auth.exceptions.RefreshError: Token has been expired or revoked`
- `credentials.refresh_token` is `None` after loading from file

**Phase to address:** Google Drive integration phase.

---

### Pitfall 10: WAV File Size for Long Meetings Grows to Hundreds of Megabytes

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

### Pitfall 11: Signal Handling — SIGINT Cleanup Skips atexit Handlers if Not Explicitly Wired

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

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| BlackHole via sounddevice | Query devices by index (index changes across reboots) | Query by name: find device where `name` contains `"BlackHole 2ch"` |
| faster-whisper KBLab models | Pass `model_size_or_path="kb-whisper-large"` (not a HuggingFace repo path) | Pass the full HuggingFace repo ID: `"KBLab/kb-whisper-large"` |
| faster-whisper language detection | Rely on auto-detect for Swedish | Always pass `language="sv"` explicitly — auto-detect on the first 30 seconds can misidentify Swedish as Norwegian, Danish, or English |
| Google Drive API | Assume OAuth token is valid on re-run | Always call `credentials.refresh(Request())` before every API call; check `credentials.valid` |
| Chrome native messaging | Use `json.dumps()` + `print()` to send messages | Use `sys.stdout.buffer.write(struct.pack('<I', len(msg)) + msg.encode())` |
| Flask SSE | Yield events from a direct generator reading shared state | Use `queue.Queue` per client; SSE generator blocks on `q.get(timeout=1)` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading WhisperModel on each transcription call | 5–15 second delay before transcription starts; high memory churn | Load model once at application start; hold as singleton | Every transcription |
| Using `float32` compute_type on Apple Silicon CPU | Transcription uses only 1 CPU core; 3–5x slower than int8 | Use `compute_type="int8"` on CPU; this is the fastest option on Apple Silicon without GPU | Always on Apple Silicon |
| Writing audio to a growing in-memory list | RAM grows ~1.9 MB/min; Python GC pressure increases | Write directly to WAV file in callback consumer thread | Recordings over ~15 minutes |
| Transcribing the entire WAV file at once for very long meetings | Whisper segments max at 30s internally anyway; no benefit to huge batch | File-based transcription is fine; do not chunk manually unless future streaming is needed | Not a trap for batch mode |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing `credentials.json` (OAuth client secret) in the project repo | Exposes OAuth client secret; anyone can impersonate the app | Add `credentials.json` to `.gitignore`; document that users must create their own Google Cloud project |
| Storing `token.json` in the project repo | Exposes valid refresh token; attacker gains full Drive access | Add `token.json` to `.gitignore`; store in `~/.config/mote/` with `chmod 600` |
| Flask web UI binding to `0.0.0.0` | Anyone on the local network can control recordings and read transcripts | Always bind to `127.0.0.1` only; this is already a stated constraint but must be enforced in code, not just docs |
| TOML config file with API keys world-readable | API keys (OpenAI, Mistral) readable by other local users or processes | Set config file permissions to `600` on creation; warn if permissions are too open at startup |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent recording start when BlackHole is not the system output | User records an entire meeting, gets a silent transcript | Validate device at recording start; refuse to record with a clear error message and setup instructions |
| No disk space check before recording | Recording fails mid-meeting with an OS error | Check available disk space at recording start; warn if < 500 MB free |
| Ambiguous "downloading model" progress — no size shown | User does not know if it's a 200 MB or 2 GB download | Show model size in MB before download begins; show progress bar during download |
| Model name "kb-whisper-large" not explaining what it is | User does not know which model to choose | Show WER improvement vs. OpenAI Whisper alongside model name in model management UI |
| Transcript written to current working directory silently | User cannot find transcript file | Always print the absolute path of the output file after transcription completes |

---

## "Looks Done But Isn't" Checklist

- [ ] **Audio capture:** Recording produces non-empty WAV file AND the audio is actually meeting audio (not silence, not mic noise) — verify by checking waveform, not just file size
- [ ] **Transcription:** Model loads without error AND produces Swedish text output (not English) — test with a known Swedish audio sample
- [ ] **SSE:** Status events arrive in browser AND other API routes still respond while SSE is connected — test both simultaneously
- [ ] **Native messaging:** Extension receives message from host AND host receives message from extension — test bidirectional; receive-only often works while send is broken
- [ ] **OAuth flow:** Token refresh works on second run (not just first) — test by deleting access token from token.json and running again without re-authorizing
- [ ] **Temp file cleanup:** WAV file is deleted after successful transcription AND after failed transcription AND after Ctrl+C — test all three cases
- [ ] **Signal handling:** Ctrl+C during recording stops the stream cleanly, no orphaned processes — check with `ps aux` after interrupt
- [ ] **Model management:** Download progress shown AND download can be interrupted AND partial download does not corrupt the model directory

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| BlackHole drift distortion on M1/M2 | LOW | Change to capture-only mode (set BlackHole 2ch as system output, use earphones directly) |
| KBLab tokenizer version mismatch | LOW | `rm -rf ~/.cache/huggingface/hub/models--KBLab*` then upgrade faster-whisper and re-download |
| Chrome extension ID mismatch in manifest | LOW | Re-run `mote install-extension` with correct ID; reload extension in Chrome |
| OAuth refresh token missing from token.json | LOW | Delete `~/.config/mote/token.json`; run `mote auth` to re-authorize |
| Orphaned WAV temp files | LOW | `rm /tmp/mote_*.wav` |
| Flask port still bound after crash | LOW | `lsof -i :PORT | grep LISTEN` then `kill -9 PID` |
| WhisperModel loaded multiple times, OOM | MEDIUM | Restart application; ensure model is a module-level singleton not per-request |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| BlackHole drift distortion on M1/M2 | Audio capture foundation | Record a 30-minute test session; check audio for distortion |
| BlackHole requires manual output routing | Audio capture foundation | Attempt to start recording with wrong output device; verify clear error message |
| WhisperModel concurrency / thread safety | Transcription engine | Run transcription while Flask web UI is open; verify no crashes |
| KBLab tokenizer version mismatch | Transcription engine | Fresh `pip install` in empty venv; verify model loads without error |
| Flask SSE blocks all requests | Web UI | Connect to SSE endpoint; verify recording control buttons still respond |
| sounddevice callback must not block | Audio capture foundation | Record 5 minutes; inspect WAV for gaps or overflow warnings |
| Chrome native messaging stdout corruption | Chrome extension | Verify JSON messages received by extension with no debug print() calls present |
| Chrome native messaging absolute path | Chrome extension | Uninstall and reinstall; verify extension connects without manual manifest editing |
| Google Drive OAuth refresh token missing | Google Drive integration | Delete token.json; run upload; verify no browser window opened on second run |
| WAV file size and disk space | Audio capture foundation | Estimate size at recording start; verify 1-hour recording produces ~110 MB file |
| Signal handling and temp file cleanup | CLI phase | Press Ctrl+C during recording; verify no orphaned files in /tmp |

---

## Sources

- [BlackHole GitHub — Multi-Output and Aggregate Devices wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Aggregate-Device)
- [BlackHole GitHub — Issue #274: Recorded sound distorts after 20-30 minutes](https://github.com/ExistentialAudio/BlackHole/issues/274)
- [BlackHole DeepWiki — Multi-Output and Aggregate Devices](https://deepwiki.com/ExistentialAudio/BlackHole/3.2-multi-output-and-aggregate-devices)
- [KBLab/kb-whisper-large HuggingFace — Discussion #15: Error when using this model from faster-whisper](https://huggingface.co/KBLab/kb-whisper-large/discussions/15)
- [KBLab Blog — Welcome KB-Whisper (2025-03-07)](https://kb-labb.github.io/posts/2025-03-07-welcome-KB-Whisper/)
- [faster-whisper GitHub — Discussion #406: Concurrent requests](https://github.com/SYSTRAN/faster-whisper/discussions/406)
- [faster-whisper GitHub — Issue #1207: Inconsistent Transcription Results with Async](https://github.com/SYSTRAN/faster-whisper/issues/1207)
- [Chrome for Developers — Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)
- [Max Halford — Server-sent events in Flask without extra dependencies](https://maxhalford.github.io/blog/flask-sse-no-deps/)
- [Flask-SSE Documentation](https://flask-sse.readthedocs.io/en/latest/quickstart.html)
- [python-sounddevice — Issue #187: Proper threading and thread-safety](https://github.com/spatialaudio/python-sounddevice/issues/187)
- [python-sounddevice — Issue #155: Explanation of Over/Underflow errors](https://github.com/spatialaudio/python-sounddevice/issues/155)
- [Google OAuth 2.0 — Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Python docs — atexit module](https://docs.python.org/3/library/atexit.html)
- [Python docs — tempfile module](https://docs.python.org/3/library/tempfile.html)
- [slinkp.com — Recording System Audio Output on a Macbook (2025)](https://slinkp.com/record-system-audio-macos-2025.html)

---
*Pitfalls research for: macOS Swedish meeting transcription tool (Möte)*
*Researched: 2026-03-27*
