# Speech-To-Text with GUI (Local, Vosk-based)

A **local, offline speech-to-text desktop application** built with Python,  
using **Vosk** for recognition, **sounddevice** for audio capture, and **Tkinter** for the GUI.

The goal is to provide an interpretable, speaker-aware transcription tool where you can:

- Manage multiple speakers with **names + colors**
- See **live transcription** as audio is processed
- Edit the text freely while keeping **timestamps protected**
- Attach **timestamped notes** to any sentence
- **Export** everything to a structured JSON file for later analysis

---

## ✨ Features

### 👥 Speaker Manager & Color Assignment

- Add speakers dynamically with **[Add Speaker]**
- Each speaker has:
  - A **name**
  - A unique **color**
  - A dedicated **button**
- **Double-click** a speaker button to edit:
  - Speaker name
  - Speaker color (via a color picker)
- **Click** a speaker button to set the **active speaker**
- When transcription starts, the **first speaker is automatically selected** (if none is active)
- When you add a new speaker, that speaker becomes the **active one by default**

---

### 📝 Live Transcription & Editable Text

The main transcription area has two parts:

1. **Live panel (top)**  
   - Shows partial recognition as the user speaks.
   - When you press **[Start]**, it first shows:
     - `Wait, starting...` while the Vosk model loads.
   - Once the engine is ready, the message disappears and live text appears.

2. **Editable transcript (bottom)**  
   - Each final recognized segment is stored as a **separate line**.
   - Line format:
     ```text
     [HH:MM:SS.mmm-HH:MM:SS.mmm] SpeakerName: transcribed text...
     ```
   - Times are **real-world wall clock times**, not “seconds since start”.
   - **Timestamps are protected** from editing (you can edit the text, not the time).
   - Each line is colored with the **speaker’s color**, making it easy to see who said what.

A segment (sentence-like unit) is considered **completed** when:

- The recognizer finalizes an utterance (usually after a pause), or
- The user switches the active speaker (semantic separation).

---

### 🗒 Notes & Annotations

- Right-click any sentence in the transcript area to create a **note**.
- Each note automatically includes:
  - The **timestamp range** from that line
  - The **speaker name** and color
- Notes are displayed in a separate **Notes** panel on the right.
- Notes are free-text: you can edit them to whatever you want (observations, tags, corrections, etc.).

---

### 📤 JSON Export

- The **[Export]** button (next to Start / Add Speaker) lets you export:
  - Speaker definitions (name + color)
  - Transcription with timestamps and speakers
  - Notes with timestamps and speakers
- Data is exported as a **single JSON file**.

The exported JSON structure is:

```json
{
  "metadata": {
    "exported_at": "2025-01-01T12:34:56.789"
  },
  "speakers": [
    {
      "name": "Alice",
      "color": "#1f77b4"
    },
    {
      "name": "Bob",
      "color": "#ff7f0e"
    }
  ],
  "transcript": [
    {
      "timestamp": "14:15:23.123-14:15:27.456",
      "speaker": "Alice",
      "text": "Hello, this is an example."
    }
  ],
  "notes": [
    {
      "timestamp": "14:15:23.123-14:15:27.456",
      "speaker": "Alice",
      "text": "User sounds uncertain here."
    }
  ]
}
````

This makes it easy to:

* Re-import data later.
* Run downstream analysis (NLP, diarization, statistics).
* Build your own visualizations or reports.

---

## 🧠 How It Works (High-Level)

* **Audio capture** uses [`sounddevice.InputStream`](https://python-sounddevice.readthedocs.io/):

  * Streams audio frames into a thread-safe queue.
  * Typically 16 kHz mono, 16-bit PCM.
* **Speech recognition** uses [Vosk](https://alphacephei.com/vosk/):

  * A local acoustic + language model is loaded from disk.
  * A `KaldiRecognizer` consumes raw audio chunks.
  * For each chunk:

    * `AcceptWaveform()` returns `True` when an utterance is finalized.
    * `Result()` gives a full JSON with final text + word timings.
    * `PartialResult()` gives intermediate text for the live view.
* **Timestamps**:

  * Vosk provides **relative times** (seconds since stream start).
  * The app records a **wall-clock start time** when streaming starts.
  * Real timestamps are computed as:

    ```text
    real_time = stream_start_wall_time + vosk_relative_time
    ```
  * Displayed as `HH:MM:SS.mmm-HH:MM:SS.mmm` in local time.
* **GUI** is built with Tkinter:

  * `SpeakerManager` manages speakers and colors.
  * `TranscriptionPanel` displays live + final transcript.
  * `NotesPanel` manages notes.
  * `TimestampedText` is a custom text widget:

    * Protects timestamp parts from editing.
    * Colors text according to speaker tags.

---

## 📦 Project Structure

```text
Speech-To-Text_withGUI/
├── .gitignore
├── README.md
├── requirements.txt
├── scripts/
│   └── run_app.py            # Entry point: python -m scripts.run_app
├── stt_gui/
│   ├── __init__.py
│   ├── main.py               # Package-level launcher
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py       # Paths, sample rate, GUI poll interval, model path
│   ├── audio/
│   │   ├── __init__.py
│   │   └── audio_stream.py   # sounddevice InputStream wrapper
│   ├── stt/
│   │   ├── __init__.py
│   │   └── vosk_engine.py    # Vosk engine + STTResult
│   └── gui/
│       ├── __init__.py
│       ├── app.py            # Main GUI frame: wires everything together
│       ├── speaker_manager.py
│       ├── transcription_panel.py
│       ├── notes_panel.py
│       └── widgets.py        # TimestampedText, etc.
└── tests/
    ├── __init__.py
    └── test_sentence_segmenter.py (optional / WIP)
```

---

## 🛠 Requirements

* **Python**: 3.10+ recommended
* **OS**:

  * Linux
  * macOS
  * Windows (with proper audio drivers)
* **Dependencies** (from `requirements.txt`):

  * `vosk`
  * `sounddevice`
  * `pytest` (for tests)

You also need to download a **Vosk model** (e.g., Italian or English).

---

## 🔧 Installation

### 1. Clone the repository

```bash
git clone git@github.com:Daedalo98/Speech-To-Text_withGUI.git
cd Speech-To-Text_withGUI
```

(or use the HTTPS URL if you prefer)

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\Activate.ps1    # Windows PowerShell
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download a Vosk model

Go to the official Vosk models page and download a model, for example:

* Italian: `vosk-model-it-0.22`
* English: `vosk-model-small-en-us-0.15`

Extract it under the `models/` directory (you may need to create it first):

```bash
mkdir -p models
# Example path:
# models/vosk-model-it-0.22
```

### 5. Point the app to your Vosk model

Open:

```text
stt_gui/config/settings.py
```

Find:

```python
DEFAULT_VOSK_MODEL_PATH = BASE_DIR / "models" / "vosk-model-small-en-us-0.15"
```

Change it if needed, for example:

```python
DEFAULT_VOSK_MODEL_PATH = BASE_DIR / "models" / "vosk-model-it-0.22"
```

Save the file.

---

## ▶️ Running the Application

From the project root (with the virtualenv active):

```bash
python3 -m scripts.run_app
```

This will open the GUI window.

---

## 🧭 Basic Usage Guide

1. **Add at least one speaker**

   * Click **[Add Speaker]**
   * Enter a name (e.g., "Alice")
   * A color will be assigned automatically (you can change it later by double-clicking the button).

2. **Start transcription**

   * Click **[Start]**
   * The live panel will show `Wait, starting...` while the model loads.
   * Once ready, the button text becomes **Stop** and transcription begins.

3. **Assign the active speaker**

   * Click on a speaker button to set who is speaking.
   * The first speaker is automatically selected when transcription starts.
   * When you add a new speaker, that speaker becomes active by default.

4. **Watch live text**

   * The top label shows partial text while you speak.
   * When an utterance is finalized, it moves into the transcript area as a full line with a timestamp.

5. **Edit transcript**

   * You can edit the **text** part of each line.
   * The **timestamp** at the start of the line is protected to preserve time information.

6. **Add notes**

   * Right-click on a line (sentence) in the transcript.
   * A new note will appear in the Notes panel with:

     * The line’s timestamp
     * The line’s speaker
   * Edit the note text as you like.

7. **Export everything**

   * Click **[Export]**.
   * Choose a destination `.json` file.
   * The file will contain: metadata, speakers, transcript, and notes.

---

## 🧪 Running Tests

If you add more tests (recommended), you can run them with:

```bash
pytest
```

You can extend the test suite to cover:

* VoskEngine behavior with mocked audio data
* Parsing and exporting functions
* GUI logic that can be tested without a display (e.g., using tags, text parsing)

---

## 🛤 Roadmap / Ideas

Potential future improvements:

* Better **sentence segmentation** based on silence length and punctuation.
* Toggleable **auto-scroll** for the transcript.
* Support for multiple **audio input devices** selection.
* Export to **Markdown** or **HTML** alongside JSON.
* Optional **autosave** of transcripts/notes to disk (with session recovery).
* Packaging as a **standalone executable** (PyInstaller, Briefcase, etc.).

---

## 📄 License

> **Note:** A license file has not been specified yet.
> You may want to add a `LICENSE` file (for example, MIT, Apache-2.0, or GPL-3.0)
> depending on how you intend others to use this project.

---

## 🤝 Contributing

Issues and pull requests are welcome:

* Report bugs (stack traces, OS, Python version).
* Suggest UI improvements or new export formats.
* Propose refactors to keep the code clean and maintainable.

---

## 💬 Contact

* GitHub: [@Daedalo98](https://github.com/Daedalo98)

If you use this project or build something on top of it, feel free to open an issue or PR and share your experience.

