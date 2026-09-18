"""
ROLEX AI — Main Entry Point (CLI)
Run:  python main.py            -> interactive chat
      python main.py --status   -> system status
      python main.py --diag     -> diagnostics
      python main.py --voice    -> voice mode
      python main.py --gui      -> launch GUI
"""
from __future__ import annotations

import argparse
import sys

from config import CONFIG
from modules.logger import get_logger

log = get_logger("rolex.main")

BANNER = r"""
  ____   ___  _     _____  __
 |  _ \ / _ \| |   | ____| \ \/ /
 | |_) | | | | |   |  _|    \  /
 |  _ <| |_| | |___| |___   /  \
 |_| \_\\___/|_____|_____| /_/\_\   A I
"""


def print_banner() -> None:
    print(BANNER)
    print(f"  {CONFIG.app_name} v{CONFIG.version} — local-first personal AI")
    print(f"  Mode: {'ROLEX-ONLY' if CONFIG.rolex_only_mode else 'external AI allowed'}")
    print("  Type 'help' for commands, 'exit' to quit.\n")


def run_cli() -> int:
    from app import get_app
    app = get_app()
    print_banner()
    while True:
        try:
            user = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nRolex > Goodbye!")
            break
        if not user:
            continue
        if user.lower() in ("exit", "quit", "bye"):
            print("Rolex > Goodbye!")
            break
        resp = app.process(user)
        print(f"Rolex > {resp.text}")
        if resp.tool:
            print(f"        [{resp.tool} | {resp.provider} | conf {resp.confidence:.2f}]")
    app.shutdown()
    return 0


def run_voice() -> int:
    from app import get_app
    app = get_app()
    print_banner()
    if not app.voice.stt_available():
        print("Voice input is not available (install 'SpeechRecognition' + microphone).")
        print("Falling back to text mode.\n")
        return run_cli()
    print("Voice mode active. Say 'Hey Rolex ...' (Ctrl+C to exit).\n")
    try:
        while True:
            resp = app.voice_turn()
            if resp:
                print(f"Rolex > {resp.text}")
    except KeyboardInterrupt:
        print("\nRolex > Goodbye!")
    app.shutdown()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ROLEX AI")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--diag", action="store_true", help="Show diagnostics")
    parser.add_argument("--packages", action="store_true", help="Show optional package status")
    parser.add_argument("--voice", action="store_true", help="Start voice mode")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI")
    parser.add_argument("--ask", type=str, help="Process a single message and exit")
    args = parser.parse_args(argv)

    if args.gui:
        try:
            from gui.rolex_gui import run_gui
            return run_gui()
        except Exception as e:
            log.error("GUI failed to start: %s", e)
            print("GUI unavailable. Falling back to CLI.")
            return run_cli()

    from app import get_app
    app = get_app()

    if args.status:
        import json
        print(json.dumps(app.status(), indent=2))
        return 0
    if args.diag:
        print(app.diagnostics_report()["summary"])
        return 0
    if args.packages:
        print(app.packages())
        return 0
    if args.ask:
        resp = app.process(args.ask)
        print(resp.text)
        return 0
    if args.voice:
        return run_voice()
    return run_cli()


if __name__ == "__main__":
    sys.exit(main())
