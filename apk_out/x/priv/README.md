# ROLEX AI

**A local-first, modular personal AI operating system for Android + PC.**

ROLEX AI is a complete personal assistant that runs on your own machine. It keeps
your data local, works offline, and only talks to external AI providers (OpenAI,
Gemini, Ollama, Hugging Face) when *you* allow it. It ships with a dark,
futuristic Rolex-themed GUI, a voice interface with wake-word support, a
scientific math engine, document intelligence, task/plan management, a knowledge
base, automation, plugins, and a full security layer.

> **Design principle:** *Local-first. Private by default. Nothing leaves your
> device unless you say so.*

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture](#architecture)
3. [Quick Start (PC)](#quick-start-pc)
4. [Configuration & API Keys](#configuration--api-keys)
5. [Using ROLEX AI](#using-rolex-ai)
6. [Voice & Wake Word](#voice--wake-word)
7. [The GUI](#the-gui)
8. [Building the Android APK](#building-the-android-apk)
9. [Security Model](#security-model)
10. [Testing](#testing)
11. [Project Layout](#project-layout)
12. [Troubleshooting](#troubleshooting)
13. [Roadmap](#roadmap)

---

## Feature Overview

ROLEX AI is organized into **26 departments**, each implemented as a focused,
independently testable module.

| # | Department | Module | What it does |
|---|-----------|--------|--------------|
| 1 | Core Intelligence | `app.py`, `brain.py` | End-to-end reasoning pipeline |
| 2 | Brain / Reasoning | `brain.py` | Normalize → context → reason → decompose |
| 3 | Command & Router | `router.py` | Intent detection (English / Tamil / Tanglish) |
| 4 | Database | `data/database.py` | Thread-safe SQLite (WAL), migrations, backup/restore |
| 5 | Engineering | `modules/math_engine.py` | Scientific, geometry, electrical, RPM |
| 6 | Document Intelligence | `modules/documents.py` | PDF/DOCX/XLSX/PPTX/CSV/JSON/TXT/MD |
| 7 | GUI | `gui/` | Kivy dark Rolex theme, 5 tabs |
| 8 | Voice | `modules/voice.py` | STT, TTS, wake word |
| 9 | Internet | `modules/web.py` | Web search + weather (Open-Meteo) |
| 10 | Tasks | `modules/tasks.py` | Task manager with states & priorities |
| 11 | Knowledge | `modules/knowledge.py` | Personal knowledge base |
| 12 | Local-First | `config.py`, `modules/sync.py` | Offline-first, local backup/restore |
| 13 | Mathematics | `modules/math_engine.py` | AST-safe evaluator (no `eval`) |
| 14 | Network | `modules/web.py` | Online detection, retries, timeouts |
| 15 | Device / OS | `modules/diagnostics.py` | System, storage, CPU, memory health |
| 16 | Memory | `modules/memory.py` | Long-term personal memory |
| 17 | QA | `tests/` | 85 unit + integration tests |
| 18 | Reliability | `modules/verification.py` | Hallucination & hedging detection |
| 19 | Security | `modules/security.py` | Encryption, roles, audit, secret scan |
| 20 | Tools | `router.py` | Deterministic tool dispatch |
| 21 | UX | `gui/theme.py` | Consistent Rolex visual language |
| 22 | Vision | `modules/vision.py` | OCR, image analysis, QR (optional) |
| 23 | Planning / Autonomy | `modules/planner.py`, `modules/automation.py` | Plans, schedules, routines |
| 24 | Extensions / Plugins | `modules/plugins.py` | 11 built-in plugin manifests |
| 25 | Multi-Device | `modules/sync.py` | Local + cloud sync hooks |
| 26 | Build / Deployment | `buildozer.spec`, `.github/` | APK build + CI/CD |

---

## What's New in v1.1 — Voice Fix + Full Capability Build

This release fixes the reported **voice input/output bug** and adds a large set
of new capabilities, all local-first and gracefully degrading when optional
dependencies are missing.

### 🎙 Voice (fixed)
- **Platform-aware voice facade** (`modules/voice.py`) that auto-selects the
  right backend: native Android TTS/STT via `pyjnius` (`modules/voice_android.py`)
  or desktop `pyttsx3` + `SpeechRecognition` (`modules/voice_desktop.py`).
- **Wake words:** "Hey Rolex" and "Hey Guru" (plus bare "rolex"/"guru").
- **Live amplitude** (`VoiceState.amplitude`, 0..1) exposed for UI animation.

### 🤖 Futuristic Autobots UI
- **Optimus Prime hero** (`gui/optimus.py`) rendered in the center of the app,
  with **eyes that glow in sync with the voice bass** — the eye bloom, aura
  rings and ground glow all react to the live voice amplitude.
- New **Optimus Core** screen and **Capabilities** dashboard.
- Expanded Autobots palette (autobot blue, energon violet, energy cyan).

### 🧠 Intelligence & Learning
- `modules/knowledge_graph.py` — SQLite knowledge graph with BFS path finding.
- `modules/self_learning.py` — daily learning cycle + fact mining.
- `modules/sandbox.py` — AST policy guard + subprocess sandbox.
- `modules/self_modify.py` — propose → test → apply → rollback self-modification.
- Smart provider selection in `modules/parallel_ai.py`.
- Short + long-term memory in `modules/memory.py`.

### 🧰 Capability Modules
| Module | Capability |
|--------|-----------|
| `modules/tool_manager.py` | Register/invoke tools with approval + audit |
| `modules/package_manager.py` | Controlled, dry-run package management |
| `modules/device.py` | Battery, storage, vibrate, torch, device info |
| `modules/smarthome.py` | Smart-home / IoT devices, scenes, drivers |
| `modules/messaging.py` | Messaging/social + mail with auto-reply rules |
| `modules/finance.py` | SIP, lumpsum, EMI, interest, share P&L, expenses, bills |
| `modules/health.py` | BMI, BMR, water intake, curated health topics, red-flag triage |
| `modules/biometrics.py` | Fingerprint / face auth (PBKDF2 secrets) |
| `modules/emergency.py` | Emergency stop (engage/release) |
| `modules/remote_lab.py` | Minimal stdlib WebSocket remote lab |
| `modules/coding.py` | Detect/explain/review code, templates |
| `modules/computer_knowledge.py` | Offline computer knowledge base |
| `modules/self_tests.py` | Automated self-test suite |
| `modules/recovery.py` | Snapshots, integrity checks, self-heal |
| `modules/vision.py` | Camera capture + OCR + document scan |

### 🗣 New voice/chat commands
```
SIP 5000 12 10            EMI 500000 8.5 20        compound 10000 8 5
my spending               bmi 70 1.75              device info / battery
turn on light             inbox                    send message to Sabari hi
explain code <code>       what is a cpu            backup now
run self test             knowledge graph stats    daily learning
available tools           list packages            remote lab status
capture photo             best ai for coding       emergency stop
```

---

## Architecture

```
                 ┌────────────────────────────────────────────┐
                 │                 ROLEX AI                    │
                 │            (app.py — facade)                │
                 └───────────────┬────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   ┌────▼─────┐           ┌──────▼──────┐          ┌──────▼──────┐
   │  Router  │           │    Brain    │          │   Voice     │
   │ (tools)  │           │ (reasoning) │          │ (STT/TTS)   │
   └────┬─────┘           └──────┬──────┘          └─────────────┘
        │                        │
        │              ┌─────────▼──────────┐
        │              │  Parallel AI +     │
        │              │  Verification      │
        │              └─────────┬──────────┘
        │                        │
        │              ┌─────────▼──────────┐
        │              │  Providers         │
        │              │  OpenAI / Gemini / │
        │              │  Ollama / HF /     │
        │              │  Local             │
        │              └────────────────────┘
        │
   ┌────▼──────────────────────────────────────────────────┐
   │  Memory · Tasks · Planner · Documents · Knowledge ·    │
   │  Web · Automation · Plugins · Sync · Vision · Security │
   └────────────────────────┬───────────────────────────────┘
                            │
                   ┌────────▼─────────┐
                   │  SQLite (WAL)    │
                   │  data/rolex.db   │
                   └──────────────────┘
```

**Key idea:** the router handles deterministic, local commands first (math,
memory, tasks, weather, etc.). Only when no local tool matches does the request
fall through to the brain, which may consult external AI providers — and only if
the policy engine allows it.

---

## Quick Start (PC)

### 1. Requirements

- **Python 3.10+** (3.11 recommended)
- No third-party packages are required for the core — it runs on the standard
  library alone. Optional packages unlock GUI, documents, voice, and vision.

### 2. Install

```bash
cd ROLEX_AI

# (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# core only (zero dependencies)
python main.py --status

# full experience (GUI + documents + voice)
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# edit .env and add your API keys (see next section)
```

### 4. Run

```bash
python main.py            # interactive CLI chat
python main.py --gui      # launch the Kivy GUI
python main.py --voice    # voice mode (needs SpeechRecognition + mic)
python main.py --status   # system status
python main.py --diag     # diagnostics report
python main.py --packages # optional dependency status
python main.py --ask "what is 15% of 240"
```

---

## Configuration & API Keys

All configuration lives in `.env` (never committed). Copy `.env.example` to
`.env` and fill in what you have. **Every key is optional** — ROLEX AI degrades
gracefully and keeps working locally without any of them.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI models (`gpt-4o-mini` by default) |
| `GEMINI_API_KEY` | Google Gemini (`gemini-1.5-flash`) |
| `OLLAMA_BASE_URL` | Local Ollama server (default `http://localhost:11434`) |
| `HUGGINGFACE_API_KEY` | Hugging Face Inference API |
| `ELEVENLABS_API_KEY` | High-quality TTS voices |
| `PICOVOICE_ACCESS_KEY` | Porcupine wake-word engine |
| `OPENWEATHER_API_KEY` | Weather (falls back to keyless Open-Meteo) |
| `ROLEX_ONLY_MODE` | `true` = block all external AI, local only |
| `ALLOW_EXTERNAL_AI` | `true` = allow external providers when keys exist |
| `REQUIRE_APPROVAL` | `true` = require approval for sensitive actions |
| `ROLEX_SECRET_KEY` | Long random string used for local encryption |

Check which providers are live at any time:

```bash
python main.py --status
```

---

## Using ROLEX AI

ROLEX AI understands **English, Tamil, and Tanglish**. Type natural commands:

| You say | What happens |
|---------|--------------|
| `remember my wifi password is hunter2` | Stored in personal memory |
| `what is my wifi password` | Recalled from memory |
| `calculate 2^10 + sqrt(144)` | Math engine (AST-safe) |
| `convert 5 km to miles` | Unit conversion |
| `ohms law voltage 2 amps 10` | Electrical calculation |
| `rpm 4 poles 50 hz` | Motor RPM |
| `add task buy groceries` | Task created |
| `list my tasks` | Task list |
| `plan a trip to Goa` | Multi-step plan |
| `index document notes.pdf` | Document intelligence |
| `search knowledge python decorators` | Knowledge base lookup |
| `weather in Chennai` | Live weather |
| `search the web for latest AI news` | Web search |
| `status` | System status |
| `help` | Command reference |

---

## Voice & Wake Word

ROLEX AI supports hands-free operation with the wake words **"Hey Rolex"** and
**"Hey Guru"** (plus bare `rolex` / `guru`).

- **Speech-to-text:** `SpeechRecognition` (Google / Sphinx backends)
- **Text-to-speech:** `pyttsx3` (offline) or ElevenLabs (online, higher quality)
- **Wake word:** Picovoice Porcupine (if key present) or built-in phrase match

```bash
python main.py --voice
```

If voice dependencies are missing, ROLEX AI automatically falls back to text
mode — it never crashes.

---

## The GUI

The GUI is built with **Kivy** and uses a locked, dark, futuristic Rolex theme
(gold `#D4AF37` + cyan `#00E5E5` on obsidian `#0B0E14`). It has five tabs:

1. **Chat** — conversational interface with bubbles
2. **Voice** — push-to-talk and wake-word controls
3. **Memory** — browse and manage stored memories
4. **Tasks** — task board
5. **System** — live status and diagnostics

```bash
python main.py --gui
```

The GUI is guarded so that if Kivy is unavailable, ROLEX AI falls back to the
CLI instead of crashing.

---

## Building the Android APK

ROLEX AI targets **Android API 34** (min API 23), **arm64-v8a**.

### Prerequisites

- Linux (or WSL2) build host
- Java JDK 17
- Android SDK + NDK (Buildozer installs these automatically on first run)
- ~10 GB free disk space

### Build

```bash
pip install buildozer cython
cd ROLEX_AI

# validate the build configuration first
python build/validate_build.py

# build the debug APK
buildozer -v android debug
```

The APK is written to `bin/rolexai-1.0.0-debug.apk`.

### Install on device

```bash
adb install -r bin/rolexai-1.0.0-debug.apk
adb logcat | grep -i rolex     # watch for crashes
```

### Crash-safety guarantees

ROLEX AI is engineered so the APK **does not crash or close on launch**:

- Every optional dependency (Kivy, voice, vision, documents) is imported inside
  a `try/except` guard with a graceful fallback.
- The database uses WAL mode and auto-recovers from corruption.
- The GUI falls back to CLI if the window cannot be created.
- A global error handler converts exceptions into user-safe messages.
- `build/validate_build.py` checks 8 categories (permissions, arch, secrets,
  imports, config) before you build.

### CI/CD

`.github/workflows/ci.yml` runs the full test suite on Python 3.10/3.11/3.12 and
can build the APK automatically on push.

---

## Security Model

- **No hard-coded secrets.** Everything comes from `.env`; the build validator
  scans the source tree for leaked keys.
- **Rolex-only policy.** Set `ROLEX_ONLY_MODE=true` to guarantee prompts never
  leave your device.
- **Encryption.** Sensitive local values are encrypted with an HMAC-derived key
  from `ROLEX_SECRET_KEY`.
- **Audit log.** Every significant action is recorded in the `audit_log` table.
- **Secret redaction.** Logs pass through a filter that strips API keys and
  tokens before writing to disk.
- **Access roles.** Owner / trusted / guest roles gate sensitive operations.

---

## Testing

```bash
cd ROLEX_AI
python -m pytest tests/ -v
```

Expected: **85 passed**.

Coverage includes:

- `tests/test_math_engine.py` — evaluator, geometry, units, electrical, RPM
- `tests/test_core.py` — config, database, memory, tasks, planner, knowledge
- `tests/test_integration.py` — end-to-end routing, brain, policy, security

Build safety check:

```bash
python build/validate_build.py
# RESULT: 47 passed, 8 warnings, 0 failures
```

---

## Project Layout

```
ROLEX_AI/
├── app.py                  # Application facade (single entry point)
├── brain.py                # Reasoning pipeline
├── router.py               # Intent detection + tool dispatch
├── config.py               # Central config (.env loader, no secrets)
├── main.py                 # CLI entry point
├── buildozer.spec          # Android APK configuration
├── requirements.txt        # Optional dependencies
├── .env.example            # Configuration template
├── data/
│   ├── database.py         # SQLite (WAL), migrations, backup/restore
│   └── rolex.db            # Local database (created at runtime)
├── modules/
│   ├── logger.py           # Logging + secret redaction
│   ├── memory.py           # Personal memory
│   ├── math_engine.py      # Scientific / geometry / electrical / RPM
│   ├── tasks.py            # Task manager
│   ├── planner.py          # Planning engine
│   ├── documents.py        # Document intelligence
│   ├── knowledge.py        # Knowledge base
│   ├── providers.py        # OpenAI / Gemini / Ollama / HF / Local
│   ├── parallel_ai.py      # Parallel orchestration
│   ├── verification.py     # Hallucination detection
│   ├── web.py              # Web search + weather
│   ├── voice.py            # STT / TTS / wake word
│   ├── vision.py           # OCR / image analysis
│   ├── security.py         # Encryption, roles, audit
│   ├── policy.py           # Rolex-only policy engine
│   ├── automation.py       # Scheduling / routines
│   ├── diagnostics.py      # System health
│   ├── package_check.py    # Dependency validation
│   ├── plugins.py          # Plugin architecture
│   └── sync.py             # Backup / restore / cloud sync
├── gui/
│   ├── theme.py            # Rolex color theme + KV styles
│   └── rolex_gui.py        # Kivy application
├── tests/                  # 82 tests
├── build/
│   └── validate_build.py   # Pre-build safety validator
├── assets/                 # Icons and images
├── docs/                   # Additional documentation
└── .github/workflows/      # CI/CD
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: kivy` | `pip install kivy` (GUI is optional) |
| GUI won't open on a headless server | Use the CLI, or run under `xvfb-run` |
| Voice not working | Install `SpeechRecognition` + `pyttsx3`, check microphone |
| Weather returns nothing | Set `OPENWEATHER_API_KEY` or rely on keyless Open-Meteo |
| APK build fails | Run `python build/validate_build.py` and check the report |
| Database locked | ROLEX AI uses WAL; ensure only one instance writes at a time |

---

## Roadmap

- On-device wake word via `openwakeword` (no Picovoice key needed)
- Local LLM bundling for fully offline reasoning
- Widgets and quick-settings tiles on Android
- Encrypted multi-device sync
- Plugin marketplace

---

**ROLEX AI** — *Your intelligence. Your device. Your rules.*
