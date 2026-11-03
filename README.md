# Back Quip v1.5.1

Back Quip is a compact, monochrome, local AI social reply studio, powered by llama.cpp (no separate Ollama installation). It offers 18 original fictional personas, adjustable comedy/profanity controls, three model sizes, conversation context, URL article/post reading, optional comment targets, multiple replies, and browser-local history. It does not post comments automatically.

## Startup

- **Windows 10/11:** Install 64-bit Python 3.10–3.12; double-click `start.bat`. It uses prebuilt CPU engine wheels, avoiding Visual Studio/nmake errors.
- **macOS:** Install Python 3.10–3.12; run `bash start.sh` from Terminal. Uses compatible Metal-accelerated engine wheels.
- **Linux:** Install Python 3.10–3.12 and its `venv` package; run `bash start.sh`. Uses CPU engine wheels where supported.
- Startup picks the first available local port, starting at http://127.0.0.1:8001. It reuses a running instance of the same version.

**Important:** Windows v1.4 initially uses a CPU prebuilt engine. CUDA (NVIDIA RTX 5060 Ti) acceleration is not yet automatically installed. Large models may be slow or exceed your memory. A future installer can support hardware-specific builds.

## Models

Use the selector and explicit **Download** button for missing response engines. Models download separately (multiple GB) from Hugging Face into `models/`; the app ZIP contains no model weights. The three options are:

- Quick: Qwen3 4B Instruct abliterated GGUF Q4_K_M
- Sharp: Qwen3 8B GGUF Q4_K_M
- Beefy: Qwen3 14B GGUF Q4_K_M

The names identify approximate sizes, not guaranteed speed or quality. A model downloaded in Ollama is not automatically imported into Back Quip.

## Personas

The 12 Signature personas and six Back Quip Originals are original comic character presets, not celebrity impersonations. Choosing one sets suggested slider defaults. You can modify sliders afterward; the selected personality provides an additional writing mechanism.

## GitHub release updates

The app checks the latest **published GitHub Release** from `blarkin13/back-quip`. Checking does not modify the app. When a newer release exists and has a ZIP named exactly `Back-Quip-vX.Y.Z.zip`, the **Check updates** control offers installation. Choosing installation downloads the release ZIP, validates its contents, backs up application files, replaces only allowlisted source files, and relaunches Back Quip. It preserves `.venv/`, `models/`, and browser-local history. The update uses HTTPS and requires a deliberate click.

**Publishing updates:** On GitHub, create a Release tagged `v1.4.1` (or newer) and attach a ZIP asset named `Back-Quip-v1.4.1.zip` containing root-level app files. Simply pushing commits to `main` does **not** trigger this updater. Avoid deleting the Git repository to preserve history unless you specifically want a clean history.

If an update fails, inspect `.backquip-update.log` and backups in `.backquip-update-backup/`.

## Privacy and portability

By default the app listens only on `127.0.0.1`; prompts are processed locally. Model downloads and GitHub update checks require network access. Browser history is stored in localStorage; it is not written into the repository.

The first startup requires pip network access and the availability of compatible prebuilt wheels for the selected operating system/Python version. Windows/macOS installation and actual AI output were not tested in this build environment.

## Linked article and post responses

Paste a public article or social-post URL and choose **Load post** to preview its title and extracted text. Enter a specific comment to respond to that comment using the post as context, or leave the comment blank to respond to the article/post itself. You can still paste a standalone comment without any URL.

Some sites (including Reddit, X, Instagram, and paywalled publications) may block automated fetching, require login, or render text only with JavaScript. Back Quip shows an error instead of claiming it read the page. In that case, paste the post text into the comment field to reply to it, or into **Add conversation context** when replying to a particular comment.

URL fetching requires internet access. The webpage text is downloaded by the local server; it is then processed locally by your selected model. The app blocks non-public/local addresses and limits download size and redirects.

## Article-reader improvements (v1.5.1)

Reads publisher-supplied JSON-LD `articleBody` and article-tag paragraphs as well as ordinary text. If only a title or summary can be retrieved, the page shows a warning and the response prompt explicitly limits itself to that information. Some MSN pages still block access entirely, in which case use the original publisher link or paste the text. An article URL is never assumed to contain accessible full text.
