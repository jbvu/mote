# Mote

Swedish meeting transcription for macOS. Captures system audio from virtual meetings (Teams, Zoom, etc.) via BlackHole, transcribes using local KB-Whisper models or OpenAI Whisper API, and saves transcripts as Markdown and plain text files.

## Why?

No existing transcription tool handles Swedish natively. Mote uses [KBLab's KB-Whisper](https://huggingface.co/KBLab/kb-whisper-large) models, trained on 50,000 hours of Swedish audio, achieving 47% lower word error rate than whisper-large-v3 on Swedish.

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
mote record                                     # Record + transcribe with defaults
mote record --name standup                      # Name the output files
mote record --engine openai                     # Use OpenAI API instead of local model
mote record --language en                       # Transcribe as English
mote record --no-transcribe                     # Save WAV only, skip transcription
mote record --engine openai --language en --name meeting   # Combine flags
```

Supported languages: `sv` (Swedish, default), `no` (Norwegian), `da` (Danish), `fi` (Finnish), `en` (English).

### Transcripts

```bash
mote list                                       # Show last 20 transcripts
mote list --all                                 # Show all transcripts
```

Transcripts are saved to `~/Documents/mote/` as both Markdown (with metadata header) and plain text. Filenames follow the pattern `2026-03-28_1430_standup.md`.

### Models

```bash
mote models list                                # Show available models and download status
mote models download tiny                       # Download a model (tiny/base/small/medium/large)
mote models download medium --force             # Re-download even if present
mote models delete tiny                         # Delete a downloaded model
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
```

Config is stored at `~/.mote/config.toml` (created automatically on first run).

### Status

```bash
mote status                                     # Check if a recording is active
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

## Development

```bash
git clone https://github.com/jbvu/mote.git
cd mote
make setup    # Creates venv and installs dependencies
make test     # Run test suite
make lint     # Run ruff linter
```

## License

MIT
