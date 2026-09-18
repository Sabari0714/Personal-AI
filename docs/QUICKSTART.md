# ROLEX AI — Quick Start

Get ROLEX AI running in under five minutes.

## 1. Run it (zero dependencies)

ROLEX AI's core runs on the Python standard library alone.

```bash
cd ROLEX_AI
python main.py --status
```

You should see a JSON status block showing your version, online state, provider
availability, memory count, and task stats.

## 2. Try a few commands

```bash
python main.py --ask "calculate 2^10 + sqrt(144)"
python main.py --ask "remember my favourite colour is blue"
python main.py --ask "what is my favourite colour"
python main.py --ask "convert 5 km to miles"
python main.py --ask "add task finish the report"
python main.py --ask "list my tasks"
```

## 3. Interactive mode

```bash
python main.py
```

Type `help` for the full command list, `exit` to quit.

## 4. Add your API keys (optional)

```bash
cp .env.example .env
nano .env      # paste your OpenAI / Gemini / Ollama / etc. keys
```

Then confirm they're detected:

```bash
python main.py --status
```

## 5. Install the full experience (optional)

```bash
pip install -r requirements.txt
python main.py --gui       # Kivy GUI
python main.py --voice     # voice mode
```

## 6. Build the Android APK (optional)

```bash
pip install buildozer cython
python build/validate_build.py
buildozer -v android debug
adb install -r bin/rolexai-1.0.0-debug.apk
```

## Everyday cheat sheet

| Goal | Command |
|------|---------|
| Chat | `python main.py` |
| One-shot question | `python main.py --ask "..."` |
| System status | `python main.py --status` |
| Diagnostics | `python main.py --diag` |
| Dependency check | `python main.py --packages` |
| GUI | `python main.py --gui` |
| Voice | `python main.py --voice` |
| Tests | `python -m pytest tests/ -q` |
| Build safety | `python build/validate_build.py` |

## Privacy in one line

Set `ROLEX_ONLY_MODE=true` in `.env` and ROLEX AI will never send a prompt to an
external provider — everything stays on your device.
