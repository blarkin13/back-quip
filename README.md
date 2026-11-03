# Back Quip v1.2.0 — compact local response studio

Back Quip runs its AI engine itself (built on [llama.cpp](https://github.com/ggml-org/llama.cpp) through `llama-cpp-python`). There's nothing extra to install: no Ollama and no separate service.

## Quick start

- **Windows:** double-click `start.bat`.
- **macOS / Linux:** run `./start.sh` in Terminal from the `back-quip` folder.

The launcher creates a Python environment, installs dependencies and opens Back Quip at the first free port starting at 8001. If the same version is already running on a port between 8001 and 8100, it opens that instance instead.

Requirements:
- Python 3.10 or newer. Some Linux distributions need a separate `python3-venv` package.
- On the first run, `pip` may build the AI engine from source, which takes a few minutes. That needs a C++ compiler: Xcode Command Line Tools on macOS (`xcode-select --install`), `build-essential` on Linux, or [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) ("Desktop development with C++") on Windows.

## Download response engines

Select a missing response engine in the dropdown, then click **Download Quick / Sharp / Beefy**. Back Quip downloads the model file from Hugging Face into the `models/` folder. Models aren't bundled, which keeps the download small.

| Display name | Model file (Hugging Face) | Approximate download |
|---|---|---:|
| Quick | `mradermacher/Huihui-Qwen3-4B-Instruct-2507-abliterated-GGUF` (Q4_K_M) | 2.5 GB |
| Sharp | `Qwen/Qwen3-8B-GGUF` (Q4_K_M) | 5.0 GB |
| Beefy | `Qwen/Qwen3-14B-GGUF` (Q4_K_M) | 9.0 GB |

Only one model is loaded into memory at a time. Switching modes unloads the previous one. The first reply after switching takes longer while the model loads. On Apple Silicon the engine uses the GPU (Metal) automatically.

Optional settings:
- `BACKQUIP_MODELS_DIR`: where model files are stored (default: `models/` in the project folder).
- `BACKQUIP_CONTEXT`: context window in tokens (default 8192).

## Existing behavior

- Dark/white monochrome interface and supplied hand logo.
- Recent generations and advanced intensity/humor/sarcasm/aggression controls are collapsed by default.
- Mature/dark humor enabled by default. Profanity remains independently adjustable.
- User-entered text never leaves your computer; the engine runs inside Back Quip. Browser history uses localStorage.
- The app binds to localhost by default. Nothing is posted automatically.
- If port 8001 is in use by a different app, Back Quip automatically tries 8002, 8003, and so on (through 8100). If this version of Back Quip itself is already running on one of those ports, it opens the existing instance instead. Older instances are left running and a different port is selected. The selected address is printed in the terminal.


## Roadmap

Back Quip generates AI responses to social media posts and comments. Planned platforms:

- [x] Local web app (current)
- [ ] Browser extension (Chrome/Firefox) with a "Quip" button on social media pages
- [ ] Mobile app (iOS/Android)
