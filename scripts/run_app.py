### 3.4 `scripts/run_app.py`

"""
Entry script to run the Speech-to-Text GUI application.

This keeps the `stt_gui` package clean and provides a simple
`python -m scripts.run_app` entry point.
"""

from stt_gui.main import run


def main() -> None:
    """Main CLI entry point."""
    # Simply delegate to the package-level run() function so the
    # behavior is centralized.
    run()


if __name__ == "__main__":
    main()
