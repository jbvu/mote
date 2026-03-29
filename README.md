# Mote

Swedish meeting transcription for macOS. Captures system audio from virtual meetings (Teams, Zoom, Google Meet) via BlackHole, transcribes using local KB-Whisper models or OpenAI Whisper API, and delivers transcripts to local files, Google Drive, or NotebookLM.

## Why?

No existing transcription tool handles Swedish natively. Mote uses [KBLab's KB-Whisper](https://huggingface.co/KBLab/kb-whisper-large) models, trained on 50,000 hours of Swedish audio, achieving 47% lower word error rate than whisper-large-v3 on Swedish.

## Features

- **Local Swedish transcription** via KBLab KB-Whisper (5 model sizes, CPU int8 quantized)
- **Cloud fallback** via OpenAI Whisper API with automatic file chunking
- **Live recording feedback** with audio level meter, elapsed time, and silence detection
- **Automatic audio routing** — switches output to BlackHole on record, restores on stop
- **Multi-destination output** — local Markdown/text/JSON, Google Drive, NotebookLM
- **Failure resilience** — WAV files kept on error, retry prompt, orphan detection on next run
- **Config validation** — catches misconfiguration before recording starts

## Prerequisites

- **macOS** (relies on Core Audio and BlackHole)
- **Python 3.11+**
- **BlackHole 2ch** (virtual audio device)

### Install BlackHole

```bash
brew install blackhole-2ch
```

Then set up audio routing so Mote can capture system audio:

1. Open **Audio MIDI Setup** (search in Spotlight)
2. Click **+** in the bottom left, select **Create Multi-Output Device**
3. Check both your speakers/headphones AND **BlackHole 2ch**
4. In **System Settings > Sound > Output**, select the Multi-Output Device

This lets you hear audio normally while Mote captures it through BlackHole.

### Optional: Automatic Audio Switching

Install [SwitchAudioSource](https://github.com/deweller/switchaudio-osx) for automatic BlackHole routing:

```bash
brew install switchaudio-osx
```

With this installed, `mote record` automatically switches audio output to BlackHole when recording starts and restores your original device when recording stops. Without it, Mote works normally but you must configure audio routing manually.

## Install

```bash
pip install git+https://github.com/jbvu/mote.git
```

Verify it works:

```bash
mote --version
```

## Quick Start

```bash
# Download a transcription model (one-time, ~1.4 GB)
mote models download medium

# Record a meeting — press Ctrl+C to stop
mote record --name standup

# View your transcripts
mote list
```

After pressing Ctrl+C, Mote automatically transcribes the audio and saves the result to `~/Documents/mote/`.

## Commands

### Recording

```bash
mote record                           # Record + transcribe with defaults
mote record --name standup            # Name the output files
mote record --engine openai           # Use OpenAI API instead of local model
mote record --language en             # Transcribe as English
mote record --no-transcribe           # Save WAV only, skip transcription
mote record --output-format json      # Also produce JSON output
mote record --destination drive       # Upload to Google Drive after transcription
mote record --destination notebooklm  # Upload to NotebookLM after transcription
```

Supported languages: `sv` (Swedish, default), `no` (Norwegian), `da` (Danish), `fi` (Finnish), `en` (English).

During recording, Mote shows a live display with elapsed time and audio level. If silence is detected for more than 30 seconds, a warning appears — this usually means audio routing needs attention.

### Transcribe Existing Files

```bash
mote transcribe recording.wav                      # Transcribe an existing WAV file
mote transcribe recording.wav --engine openai      # Use OpenAI engine
mote transcribe recording.wav --destination drive  # Upload result to Drive
```

Same engine, language, name, output-format, and destination flags as `mote record`.

### Transcripts

```bash
mote list                             # Show last 20 transcripts
mote list --all                       # Show all transcripts
```

Transcripts are saved to `~/Documents/mote/` as Markdown (with metadata header) and plain text. Filenames follow the pattern `2026-03-28_1430_standup.md`.

### Models

```bash
mote models list                      # Show available models and download status
mote models download tiny             # Download a model (tiny/base/small/medium/large)
mote models download medium --force   # Re-download even if present
mote models delete tiny               # Delete a downloaded model
```

| Model | Size | Notes |
|-------|------|-------|
| tiny | ~77 MB | Fastest, lowest quality |
| base | ~143 MB | |
| small | ~466 MB | |
| medium | ~1.4 GB | Good balance of speed and quality |
| large | ~2.9 GB | Best quality, slowest |

All models run locally on CPU with int8 quantization. No GPU required.

### Configuration

```bash
mote config show                                # Print current config
mote config set transcription.engine openai     # Default to OpenAI engine
mote config set transcription.language en       # Default language
mote config set transcription.model kb-whisper-tiny   # Default model
mote config set api_keys.openai sk-...          # Set OpenAI API key
mote config path                                # Print config file location
mote config validate                            # Check config for errors
```

Config is stored at `~/.mote/config.toml` (created automatically on first run, permissions 600).

### Destinations

Mote can deliver transcripts to multiple destinations. Configure active destinations in config or override per-run:

```bash
# Set destinations in config
mote config set destinations.active '["local", "drive"]'

# Override for a single run
mote record --destination drive --destination notebooklm
```

| Destination | Setup | Notes |
|-------------|-------|-------|
| `local` | Default, always active | Writes to `~/Documents/mote/` |
| `drive` | `mote auth google` | Uploads to Google Drive folder |
| `notebooklm` | `mote auth notebooklm` | Experimental, sessions expire weekly |

Destination failures are always warnings — local files are written first, and a failed upload never marks the transcription as failed.

### Authentication

```bash
mote auth google                      # Authenticate with Google Drive (OAuth2 browser flow)
mote auth notebooklm                  # Authenticate with NotebookLM (experimental, Playwright)
```

### Uploading

```bash
mote upload transcript.md             # Upload a transcript to Google Drive
mote upload --last                    # Upload the most recent transcript
```

### Utilities

```bash
mote status                           # Check if a recording is active
mote audio restore                    # Restore audio output if stuck on BlackHole after a crash
mote cleanup                          # Delete expired WAV recordings
```

## OpenAI Whisper API

To use the cloud engine instead of local models:

1. Get an API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Set it in Mote:
   ```bash
   mote config set api_keys.openai sk-your-key
   ```
   Or via environment variable:
   ```bash
   export OPENAI_API_KEY=sk-your-key
   ```
3. Record with the OpenAI engine:
   ```bash
   mote record --engine openai
   ```

Cost is approximately $0.006 per minute of audio. Files over 25 MB are automatically split into chunks.

## Google Drive Integration

Upload transcripts automatically after each recording:

1. Authenticate once:
   ```bash
   mote auth google
   ```
2. Add `drive` to your active destinations:
   ```bash
   mote config set destinations.active '["local", "drive"]'
   ```
3. Record as normal — transcripts are uploaded automatically:
   ```bash
   mote record --name standup
   ```

You can also upload individual files with `mote upload transcript.md` or `mote upload --last`.

## NotebookLM Integration (Experimental)

Upload transcripts to Google NotebookLM as sources for AI analysis:

1. Install the optional dependency:
   ```bash
   pip install 'mote[notebooklm]'
   playwright install chromium
   ```
2. Authenticate (opens a browser window):
   ```bash
   mote auth notebooklm
   ```
3. Add `notebooklm` to destinations:
   ```bash
   mote record --destination notebooklm
   ```

NotebookLM sessions expire approximately weekly — re-run `mote auth notebooklm` when prompted. This uses the unofficial [notebooklm-py](https://github.com/nicholasgasior/notebooklm-py) library and may break if the NotebookLM API changes.

## Failure Recovery

Mote is designed to never lose your recordings:

- **Transcription failure**: WAV file is kept, and you're prompted to retry. Answer yes to re-transcribe without re-recording.
- **Orphaned recordings**: If Mote crashes during transcription, the next `mote record` detects leftover WAV files and suggests `mote transcribe <file>`.
- **Upload failure**: Local files are always written first. Drive or NotebookLM failures produce a warning but never affect the transcription result.
- **Audio routing stuck**: If your Mac's audio output is stuck on BlackHole after a crash, run `mote audio restore`.

## Development

```bash
git clone https://github.com/jbvu/mote.git
cd mote
make setup    # Creates venv and installs dependencies
make test     # Run test suite (303 tests)
make lint     # Run ruff linter
```

## Architecture

```
src/mote/
  cli.py           # Click CLI — all commands and _run_transcription orchestrator
  config.py         # TOML config with validation, env var loading, dotted-key set
  audio.py          # BlackHole detection, recording, silence tracking, audio switching
  transcribe.py     # Local KB-Whisper and OpenAI Whisper engines
  models.py         # Model download/list/delete via huggingface_hub
  output.py         # Markdown/text/JSON transcript writing, filename generation
  drive.py          # Google Drive OAuth2 + upload via google-api-python-client
  notebooklm.py     # NotebookLM session management + upload via notebooklm-py
```

## License

MIT
