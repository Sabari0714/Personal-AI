# ROLEX AI — Architecture

This document explains how ROLEX AI is put together and why.

## Design principles

1. **Local-first.** The core runs with zero third-party dependencies. Every
   optional capability (GUI, voice, vision, documents, cloud AI) is imported
   behind a guard and degrades gracefully.
2. **Private by default.** External AI providers are only consulted when the
   policy engine permits it and a key is present.
3. **Never crash.** Every subsystem is defensive. A failure in one module never
   takes down the application — especially important for the Android APK.
4. **Deterministic before generative.** Local tools (math, memory, tasks) are
   tried first; the AI brain is the fallback, not the default.

## Request lifecycle

```
user input
   │
   ▼
RolexApp.process()            app.py
   │  log conversation
   ▼
Router.route()               router.py
   │  regex intent detection (EN / TA / Tanglish)
   ├── matched ──► tool handler ──► RolexResponse (provider="local")
   │
   └── no match
          ▼
       Brain.reason()         brain.py
          │  normalize → build context → reason → decompose
          ▼
       ParallelAI.query()     modules/parallel_ai.py
          │  fan-out to available providers
          ▼
       Verification.verify()  modules/verification.py
          │  similarity + hedging detection
          ▼
       RolexResponse
```

## Module responsibilities

### Core

- **`config.py`** — loads `.env` with a dependency-free parser, exposes a
  `RolexConfig` dataclass and a `CONFIG` singleton. No secrets in source.
- **`app.py`** — the facade. Owns every subsystem, exposes `process()`,
  `voice_turn()`, `status()`, `diagnostics_report()`, `shutdown()`.
- **`brain.py`** — reasoning pipeline: normalize, build context from memory and
  knowledge, reason via providers, decompose complex goals.
- **`router.py`** — intent detection and tool dispatch. Handles remember,
  forget, recall, calculate, task_*, plan*, document, knowledge, weather,
  web_search, status, time, diagnostics, help, providers, policy.

### Data

- **`data/database.py`** — thread-safe SQLite in WAL mode. Schema version 3.
  Tables: `schema_meta`, `memory`, `tasks`, `plans`, `plan_steps`, `cache`,
  `documents`, `knowledge`, `audit_log`, `conversations`, `scheduled_jobs`.
  Provides `integrity_check()`, `backup()`, `restore()`, `transaction()`.

### Intelligence

- **`modules/providers.py`** — `BaseProvider` plus `LocalProvider`,
  `OpenAIProvider`, `GeminiProvider`, `OllamaProvider`, `HuggingFaceProvider`.
  Uses stdlib `urllib` so it works on Android/Termux.
- **`modules/parallel_ai.py`** — `ThreadPoolExecutor` fan-out with `query`,
  `best`, and `compare`.
- **`modules/verification.py`** — `SequenceMatcher` similarity plus hedging
  phrase detection to flag unreliable answers.
- **`modules/web.py`** — `NetworkManager`, `WeatherService` (Open-Meteo,
  keyless), `WebSearch` (DuckDuckGo HTML), and a `WebManager` facade.

### Productivity

- **`modules/memory.py`** — long-term personal memory with categories.
- **`modules/tasks.py`** — task manager with states and priorities.
- **`modules/planner.py`** — multi-step plans and goal decomposition.
- **`modules/documents.py`** — extractive summarization and indexing for
  txt/md/csv/json/pdf/docx/xlsx/pptx.
- **`modules/knowledge.py`** — personal knowledge base.

### Interaction

- **`modules/voice.py`** — STT, TTS, wake-word detection
  (`hey rolex`, `hey guru`, `rolex`, `guru`).
- **`gui/theme.py`** — Rolex color palette and KV styles.
- **`gui/rolex_gui.py`** — Kivy app with five tabs, guarded by
  `KIVY_AVAILABLE`.

### Security & reliability

- **`modules/security.py`** — HMAC-based encryption, roles, audit logging,
  source secret scanning.
- **`modules/policy.py`** — Rolex-only policy engine.
- **`modules/diagnostics.py`** — system, storage, memory, CPU, network health.
- **`modules/package_check.py`** — optional dependency status.

### Ecosystem

- **`modules/automation.py`** — one-shot and recurring schedules, action
  registry, tick loop.
- **`modules/plugins.py`** — plugin manager with 11 built-in manifests.
- **`modules/sync.py`** — local backup/restore, config export, cloud hooks.
- **`modules/vision.py`** — OCR, image analysis, QR detection (optional).

## Data flow & storage

All persistent state lives in `data/rolex.db` (SQLite, WAL). Backups go to
`data/backups/`. Logs go to `logs/rolex.log` with a secret-redaction filter.

## Android considerations

- Only stdlib + Kivy + pyjnius + android + plyer are required for the APK.
- Heavy optional deps (pypdf, openpyxl, pillow) are commented out in
  `buildozer.spec` and can be enabled once validated.
- `build/validate_build.py` checks permissions, architecture, secrets, imports,
  and config before a build.

## Extending ROLEX AI

1. Add a module under `modules/` with a `get_*()` singleton accessor.
2. Register it in `app.py`.
3. Add an intent pattern and handler in `router.py`.
4. Add tests under `tests/`.

That's it — the router will pick it up automatically.
