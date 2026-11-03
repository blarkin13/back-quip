# Back Quip v1.1.2 — compact local response studio

## Windows quick start

Double-click `start.bat`. On first launch, Back Quip checks whether the local AI engine is responding. If the engine isn't installed, it **asks permission** to install Ollama using the Windows Package Manager (`winget`). It then starts the engine if needed, prepares its Python environment, and opens Back Quip at the first available port starting at 8001. If the same version of Back Quip is already running on a port between 8001 and 8100, it opens that instance instead.

Ollama is an external runtime: **it is not bundled inside the ZIP**. Installing it requires internet access and may display Windows installer prompts. You can decline the prompt. If `winget` is unavailable or installation fails, install from https://ollama.com/download/windows and rerun `start.bat`.

Python 3.10 or newer must still be installed for this web-app version. The ZIP does not include Python. If `py` is unavailable, install Python from https://www.python.org/downloads/windows/.

## Download response engines

Select a missing response engine in the dropdown, then click the visible **Download Quick / Sharp / Beefy** button. This also works when no engines are installed and Quick is already selected; no selection-change event is needed. Models aren't pre-bundled. This keeps the ZIP small.

| Display name | Internal model | Approximate download |
|---|---|---:|
| Quick | `dolphinlabs/qwen3.5-uncensored:latest` | 2.1 GB |
| Sharp | `qwen3:8b` | 5.2 GB |
| Beefy | `qwen3:14b` | 9.3 GB |

## macOS and Linux quick start

Open Terminal in the extracted `back-quip` folder and run `./start.sh` (or `bash start.sh`). The launcher checks for a local AI engine, asks permission to install it using the **official Ollama installer** when missing, then starts the engine, sets up the Python virtual environment, and opens the web page on an available port between 8001 and 8100. Installing the AI engine requires internet access and may prompt for system permissions. Alternatively, install from https://ollama.com/download manually.

Python 3.10+ and venv support are still prerequisites. Some Linux distributions require a separate `python3-venv` package. If your AI engine is configured on a custom host, set `OLLAMA_URL` before launching.

The Linux installer may register Ollama as a system service; the launcher checks whether it is already running before attempting to start another copy. Models are still downloaded from inside Back Quip.


## Existing behavior

- Dark/white monochrome interface and supplied hand logo.
- Recent generations and advanced intensity/humor/sarcasm/aggression controls are collapsed by default.
- Mature/dark humor enabled by default. Profanity remains independently adjustable.
- User-entered text stays local to the engine by default. Browser history uses localStorage.
- The app binds to localhost by default. Nothing is posted automatically.
- If port 8001 is in use by a different app, Back Quip automatically tries 8002, 8003, and so on (through 8100). If this version of Back Quip itself is already running on one of those ports, it opens the existing instance instead. Older instances are left running and a different port is selected. The selected address is printed in the terminal.

This update provides a guided Windows runtime installation during startup. It is **not yet a self-contained desktop installer**.

## Roadmap

Back Quip generates AI responses to social media posts and comments. Planned platforms:

- [x] Local web app (current)
- [ ] Browser extension (Chrome/Firefox) with a "Quip" button on social media pages
- [ ] Mobile app (iOS/Android)
