"""
Diagnostic entry point for the AI Miniature Painting Assistant.
"""

import traceback


def run():
    print("[1] Starting main.py", flush=True)

    try:
        print("[2] Importing GUI...", flush=True)
        from src.gui.app import main as gui_main

        print("[3] GUI import succeeded", flush=True)
        print("[4] Launching GUI...", flush=True)

        gui_main()

        print("[5] GUI exited normally", flush=True)

    except Exception:
        print("\nAPPLICATION FAILED\n", flush=True)
        traceback.print_exc()

        input("\nPress Enter to close...")


if __name__ == "__main__":
    run()
