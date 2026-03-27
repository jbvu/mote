# Feature Research

**Domain:** macOS meeting transcription tool (Swedish/Scandinavian language focus)
**Researched:** 2026-03-27
**Confidence:** HIGH (stack decisions verified; feature landscape drawn from competitor analysis and domain research)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Audio capture from virtual meetings | Core job-to-be-done — without this, nothing else matters | MEDIUM | BlackHole 2ch virtual audio device is the macOS-standard approach; requires user to configure Multi-Output Device in Audio MIDI Setup or equivalent |
| Start / stop recording controls | Every recorder has this; absence feels broken | LOW | CLI `record start` / `record stop`; must persist state across invocations (PID file or socket) |
| Transcription after recording stops | Batch transcription post-meeting is the expected flow for local tools | MEDIUM | faster-whisper processes WAV file; progress reporting via stdout/SSE |
| Output as plain text | Simplest consumable transcript format | LOW | Required for NotebookLM and copy-paste workflows |
| Output as Markdown | Developer-first format; pairs well with Drive/Notion | LOW | Heading + body structure, timestamps optional |
| Output as JSON | Machine-readable; downstream tooling, search indexing | LOW | Segment array with start/end/text fields; standard from Whisper |
| Model selection | Users need to trade accuracy vs. speed vs. disk space | LOW | tiny/base/small/medium/large; model flag on CLI or config key |
| Configuration file | Persistent settings without re-specifying flags each run | LOW | TOML at `~/.config/mote/config.toml`; sensible defaults |
| Real-time audio level monitor | Confirms audio is being captured before committing to a recording | LOW | RMS amplitude meter; essential for debugging BlackHole routing |
| Transcription progress feedback | Long recordings (60+ min) take minutes to process; silence = user frustration | LOW | Segment count or percentage via stdout / SSE stream |
| Temp file cleanup | Users don't expect WAV files accumulating; storage hygiene | LOW | Delete source WAV after successful transcription unless `--keep-audio` |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| KBLab Swedish-optimized models | 47% lower WER vs. OpenAI whisper-large-v3 on Swedish — the core reason this tool exists | MEDIUM | KB-Whisper tiny/base/small/medium/large available as CTranslate2 (faster-whisper compatible); must download from HuggingFace explicitly |
| Multi-engine transcription (local + cloud) | Fallback to cloud when local GPU is absent or user wants higher quality; cost-vs-privacy tradeoff | MEDIUM | Engine selector: `local` (faster-whisper + KB-Whisper), `openai` (Whisper API), `mistral` (Voxtral — note: Swedish support unconfirmed, treat as LOW confidence until verified) |
| Model management UI | Downloading a 1.5 GB model is opaque without progress; users abandon setup | MEDIUM | Web UI page: list installed models, disk usage, download with progress bar (SSE stream), delete |
| Google Drive auto-push | Removes the "where did I save that?" problem; feeds NotebookLM workflow without manual steps | MEDIUM | OAuth 2.0 flow on first use; token stored in config dir; upload to configurable folder; return Drive URL |
| Web dashboard | Visual alternative to CLI; lowers barrier for non-developer colleagues who may adopt the tool | HIGH | Flask + SSE; recording controls, live audio meter, job history, settings page; binds to 127.0.0.1 only |
| Chrome extension | One-click start/stop without switching windows; reduces friction during meetings where multitasking | HIGH | Manifest V3; communicates with local Flask server via `localhost` fetch; shows recording status in toolbar icon |
| Scandinavian language auto-detect | Norwegian/Danish/Finnish are close to Swedish; a single-language model makes multi-national meetings awkward | LOW | KB-Whisper is Swedish-only; multi-language requires OpenAI Whisper or Voxtral (pending language verification); this is a future differentiator |
| Structured transcript output (Subtitle/Strict modes) | KB-Whisper offers Subtitle and Strict checkpoint variants for different formatting styles | LOW | Pass `transcription_style` config option to faster-whisper; useful for subtitle generation |
| Transcript search history | Find what was said in a past meeting without re-opening files | MEDIUM | SQLite index of all transcripts; full-text search via web UI; deferred to v2 |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time live transcription (streaming during recording) | "I want to read along as it transcribes" | Doubles complexity: audio streaming pipeline + partial-result UI; conflicts with batch model loading; faster-whisper is optimized for complete audio segments, not live chunks. Creates false expectation of correctness mid-meeting | Batch-after-stop with fast turnaround (small/medium model on Apple Silicon processes 60 min in ~3–5 min). Show audio levels live instead |
| Speaker diarization (who said what) | Valuable for multi-participant meetings | pyannote.audio requires HuggingFace gated model access (manual token), adds 2–4x processing time, and has poor accuracy on Swedish. Adds a complex dependency with separate licensing | Out of scope for v1; revisit after core pipeline is stable. JSON output preserves segment timestamps for manual annotation |
| Multi-user / auth for web UI | "What if someone else on my network accesses it?" | Binds to 127.0.0.1; auth adds OAuth/session complexity for zero real threat. This is a personal tool | Document that UI is localhost-only; users needing multi-user access should use a different product |
| Auto-start recording when meeting detected | "Start automatically when I join a Zoom call" | Requires process monitoring or OS-level hooks; fragile across app versions; raises consent/privacy concerns | Provide a keyboard shortcut via Chrome extension or CLI alias for fast manual start |
| Auto-download models on first run | "It should just work" | Large model files (75 MB – 3 GB) downloaded without consent create bad UX (silent hang, unexpected bandwidth). Breaks air-gapped setups | Explicit `mote models download <name>` command with size shown beforehand; web UI model page with download button |
| Video recording / screen capture | "Record the screen too" | Increases file sizes 50–100x; irrelevant for transcription; opens legal complexity around recording other participants' cameras | Audio-only; transcript is the artifact, not the video |
| Cloud-hosted SaaS version | "Make it accessible from anywhere" | Fundamentally changes the security model (audio leaves the machine); requires auth, storage, billing, compliance — a different product entirely | Keep it local; Google Drive integration provides remote access to transcripts |
| Notification/bot joining the meeting | "Have a bot join so I don't have to configure audio" | Bots appear in participant lists, requiring host consent; introduces a cloud dependency; defeats the privacy advantage | BlackHole captures system audio invisibly, no meeting participant is added |

---

## Feature Dependencies

```
[BlackHole audio capture]
    └──required by──> [Recording (start/stop)]
                          └──required by──> [WAV file on disk]
                                                └──required by──> [Transcription engine]
                                                                       └──required by──> [Output files (MD/TXT/JSON)]
                                                                                              └──enhanced by──> [Google Drive push]

[KB-Whisper model downloaded]
    └──required by──> [Local transcription engine]

[Flask web server]
    └──required by──> [Web dashboard]
    └──required by──> [Chrome extension API]
    └──required by──> [SSE progress stream]

[SSE progress stream]
    └──enhances──> [Web dashboard live status]
    └──enhances──> [Model download progress UI]

[OAuth token (Google)]
    └──required by──> [Google Drive push]

[Model management (download/delete/list)]
    └──required by──> [Local transcription engine]  (model must exist before transcription)
    └──enhanced by──> [Web UI model management page]

[Chrome extension]
    └──requires──> [Flask web server running]
    └──conflicts──> [Transcription running] (extension should disable start button while transcribing)
```

### Dependency Notes

- **BlackHole required before recording:** Users must install `blackhole-2ch` via Homebrew and configure system audio routing before the tool is functional. This is the #1 setup friction point; must be documented clearly.
- **Model must exist before local transcription:** `mote transcribe` must check model presence and give a clear error pointing to `mote models download`. Silent failure here will confuse users.
- **Flask server required for Chrome extension:** The extension communicates with `http://localhost:PORT` — the server must already be running. Extension should detect server-down state and show an error rather than silently failing.
- **Google OAuth token required before Drive push:** The OAuth flow must complete once (browser-based) before Drive integration works. Token should be persisted between sessions in config dir.
- **SSE requires Flask threaded mode:** Default Flask dev server is single-threaded; SSE will block. Flask must run with `threaded=True` (default in Flask 2+) or via a production-grade server like Waitress.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] BlackHole system audio capture — core pipeline; nothing works without it
- [ ] CLI start/stop recording — minimal control surface
- [ ] Local transcription via faster-whisper + KB-Whisper models — the core differentiator
- [ ] OpenAI Whisper API as cloud fallback engine — for machines without GPU or when KB-Whisper not downloaded
- [ ] Output as Markdown and plain text — primary consumption formats
- [ ] TOML configuration — sensible defaults, no required flags
- [ ] Model management CLI (download/list/delete) — required before local engine is usable
- [ ] Real-time audio level monitoring — confirms routing before meeting starts
- [ ] Transcription progress reporting (CLI) — user feedback during processing
- [ ] Google Drive push — completes the workflow from capture to NotebookLM

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Web dashboard (Flask + SSE) — when CLI proves friction for regular use
- [ ] Chrome extension — when dashboard proves useful and one-click start is wanted
- [ ] Web UI model management with download progress — when web dashboard exists
- [ ] Mistral Voxtral engine — after verifying Swedish WER vs. KB-Whisper; add if competitive
- [ ] JSON output format — when downstream tooling (search, analysis) becomes a need

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Norwegian, Danish, Finnish language support — requires multi-language model strategy; KB-Whisper is Swedish-only
- [ ] Speaker diarization — high complexity, poor Swedish accuracy; defer until pyannote improves
- [ ] In-person recording via microphone — different audio routing path; deferred per PROJECT.md
- [ ] Transcript search history (SQLite FTS) — only valuable once transcript archive grows
- [ ] Subtitle/Strict transcription style variants — niche need; low-effort addition but low priority

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| BlackHole audio capture | HIGH | MEDIUM | P1 |
| CLI start/stop recording | HIGH | LOW | P1 |
| Local transcription (KB-Whisper) | HIGH | MEDIUM | P1 |
| Output formats (MD/TXT) | HIGH | LOW | P1 |
| TOML configuration | HIGH | LOW | P1 |
| Model management CLI | HIGH | LOW | P1 |
| Audio level monitoring | HIGH | LOW | P1 |
| Google Drive push | HIGH | MEDIUM | P1 |
| OpenAI Whisper API fallback | MEDIUM | LOW | P1 |
| Progress reporting | MEDIUM | LOW | P1 |
| Output format JSON | MEDIUM | LOW | P2 |
| Web dashboard | MEDIUM | HIGH | P2 |
| Chrome extension | MEDIUM | HIGH | P2 |
| Mistral Voxtral engine | MEDIUM | LOW | P2 |
| Web UI model management | MEDIUM | MEDIUM | P2 |
| Norwegian/Danish/Finnish | LOW | HIGH | P3 |
| Speaker diarization | LOW | HIGH | P3 |
| In-person microphone capture | LOW | MEDIUM | P3 |
| Transcript search history | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when core is stable
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Otter.ai / Fireflies | Jamie (bot-free, local) | trnscrb (local macOS) | Möte (this project) |
|---------|----------------------|-------------------------|-----------------------|---------------------|
| Swedish language | Poor (English-primary) | 28+ languages (auto-detect) | OpenAI Whisper (generic) | KB-Whisper: 47% lower WER for Swedish |
| Audio capture | Meeting bot joins call | System audio (BlackHole-like) | System audio via BlackHole | BlackHole 2ch |
| Privacy | Cloud upload, GDPR risk | Local-first, GDPR compliant | Local, no cloud | Local + explicit cloud opt-in |
| Output formats | PDF, DOCX, TXT, MP3 | Markdown, PDF | TXT | Markdown, TXT, JSON |
| CLI interface | None | None | None | Full Click CLI |
| Web dashboard | Full SaaS UI | Desktop app | Menu bar only | Localhost Flask dashboard |
| Chrome extension | No | No | No | Yes (remote control) |
| Google Drive | Integration (paid) | Export only | None | Direct API push |
| Model selection | None (cloud only) | Hidden | Whisper sizes | KB-Whisper + OpenAI + Mistral |
| Offline use | No | Yes | Yes | Yes (local engine) |
| Open source / self-hosted | No | No | No | Yes (GitHub, pip install) |
| Cost | $10–20/month | $15–25/month | Free | Free (local) / API costs only |

---

## Swedish Language Notes

This section covers the unique considerations for Swedish/Scandinavian language support.

**KB-Whisper model suite (HIGH confidence):**
- Trained on 50,000 hours of Swedish speech (TV subtitles, parliamentary recordings, dialect archives)
- Available sizes: tiny, base, small, medium, large-v3
- CTranslate2 format available — directly compatible with faster-whisper
- Average 47% WER reduction vs. OpenAI whisper-large-v3 on Swedish
- KB-Whisper-small outperforms OpenAI whisper-large (6x larger) on Swedish
- Two style variants: Subtitle (for captions) and Strict (for verbatim)
- Free download from HuggingFace; no license restrictions for personal use

**OpenAI Whisper API (MEDIUM confidence for Swedish):**
- OpenAI Whisper supports Swedish but is not Swedish-optimized
- Baseline for comparison; useful as cloud fallback when local model not available
- Cost: ~$0.006/minute; a 60-minute meeting costs ~$0.36

**Mistral Voxtral (LOW confidence for Swedish):**
- Official supported language list: 13 languages (English, Chinese, Hindi, Spanish, Arabic, French, Portuguese, Russian, German, Japanese, Korean, Italian, Dutch)
- Swedish is NOT in the confirmed list
- Claims 100+ language support in general model, but Swedish accuracy unverified
- Must benchmark against KB-Whisper before using Voxtral as Swedish engine
- Include as engine option but document the uncertainty

**Norwegian, Danish, Finnish:**
- KB-Whisper is Swedish-only; these require OpenAI Whisper or a different model
- OpenAI Whisper supports all four; generic model, not fine-tuned for Scandinavian dialects
- Deferred to v2 — solve Swedish first, then expand

---

## Sources

- [KB-Whisper announcement (KBLab, March 2025)](https://kb-labb.github.io/posts/2025-03-07-welcome-KB-Whisper/)
- [KB-Whisper HuggingFace models](https://huggingface.co/KBLab)
- [easytranscriber (KBLab, February 2026)](https://kb-labb.github.io/posts/2026-02-26-easytranscriber/)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [Voxtral Transcribe 2 announcement (Mistral AI)](https://mistral.ai/news/voxtral-transcribe-2)
- [Voxtral original announcement (Mistral AI)](https://mistral.ai/news/voxtral)
- [Otter.ai vs Fireflies feature comparison (Avoma, 2025)](https://www.avoma.com/blog/otter-vs-fireflies)
- [Jamie bot-free transcription review](https://www.meetjamie.ai/blog/jamie-review)
- [trnscrb local macOS transcription tool](https://www.toolify.ai/tool/trnscrb)
- [Privacy risks with cloud transcription (DEV Community, 2025)](https://dev.to/sujiths/are-ai-meeting-assistants-safe-privacy-risks-with-cloud-transcription-4a23)
- [On-device vs cloud STT tradeoffs (Talkio AI)](https://voicecontrol.chat/blog/posts/on-device-speech-to-text-vs-cloud-apis-tradeoffs-for-privacy-and-performance)
- [Chrome extension recording with Manifest V3 (Recall.ai)](https://www.recall.ai/blog/how-to-build-a-chrome-recording-extension)
- [Transcript output formats: TXT, SRT, VTT, JSON (BrassTranscripts)](https://brasstranscripts.com/blog/choosing-the-right-transcript-format-txt-srt-vtt-json)
- [Whisper model sizes and disk requirements (OpenWhispr)](https://openwhispr.com/blog/whisper-model-sizes-explained)
- [Flask SSE no-dependency implementation (Max Halford)](https://maxhalford.github.io/blog/flask-sse-no-deps/)
- [10 Best Meeting Transcription Software 2026 (Jamie)](https://www.meetjamie.ai/blog/meeting-transcription-software)
- [Best local meeting recorders (no cloud) 2026](https://blog.buildbetter.ai/best-local-meeting-recorders-no-cloud-2026/)

---
*Feature research for: macOS Swedish meeting transcription tool (Möte)*
*Researched: 2026-03-27*
