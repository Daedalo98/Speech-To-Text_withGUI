"""
Main entry point for the speech-to-text GUI package.

This module wires together the GUI with the underlying audio and
speech-to-text components.
"""

from __future__ import annotations

import tkinter as tk

from .gui.app import SpeechToTextApp


def run() -> None:
    """
    Run the main GUI application.

    The logic is intentionally simple: build the Tk root window,
    create the app frame, and start the mainloop.
    """
    # Create the main Tk root window.
    root = tk.Tk()

    # Set some basic window metadata for clarity.
    root.title("Local Speech-to-Text (Vosk)")

    # Instantiate and pack our main application frame.
    app = SpeechToTextApp(master=root)
    app.pack(fill="both", expand=True)

    # Start the Tk event loop (this call blocks until the window closes).
    root.mainloop()


if __name__ == "__main__":
    run()
