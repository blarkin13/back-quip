# Back Quip v1.7.0

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

## Updates: Development and Stable

The default update channel is **Development**, because the project is currently maintained by uploading commits to `main` without publishing Releases. Switch channels in the top-right header. The selection is stored only on your computer in `.backquip-settings.json`.

- **Development:** compares local managed app files to GitHub `main` using Git blob hashes. Detects a change even if the application version number stays the same. Shows which files differ; downloads a ZIP archive pinned to that commit SHA, validates paths and file hashes, and asks before installing. No GitHub Release is required.
- **Stable:** checks the latest published GitHub Release, requires a newer version and an attached `Back-Quip-vX.Y.Z.zip` asset, and asks before installing. No Releases currently exist, so Stable reports that rather than downloading from `main`.

Both startup scripts check the selected channel before opening the page (after dependency installation). The browser's **Check updates** button uses the same selection. Updates back up only allowlisted application files, leaving `models/`, `.venv/`, `.git/`, local settings and browser history untouched. Development uses the archive for the latest commit of `main`, but only changes recognized application files, not arbitrary new scripts. Restart the app after uploading this package to GitHub to establish the new updater. If you see a repeated prompt immediately after a GitHub upload, run Check updates; the updater compares actual file contents instead of relying only on commit IDs.

For startup without a check, set `BACKQUIP_SKIP_STARTUP_UPDATE=1`. Network errors do not prevent offline use. An already-running Back Quip instance remains running; use the in-app updater to safely replace it.


## Privacy and portability

By default the app listens only on `127.0.0.1`; prompts are processed locally. Model downloads and GitHub update checks require network access. Browser history is stored in localStorage; it is not written into the repository.

The first startup requires pip network access and the availability of compatible prebuilt wheels for the selected operating system/Python version. Windows/macOS installation and actual AI output were not tested in this build environment.

## Linked article and post responses

Paste a public article or social-post URL and choose **Load post** to preview its title and extracted text. Enter a specific comment to respond to that comment using the post as context, or leave the comment blank to respond to the article/post itself. You can still paste a standalone comment without any URL.

Some sites (including Reddit, X, Instagram, and paywalled publications) may block automated fetching, require login, or render text only with JavaScript. Back Quip shows an error instead of claiming it read the page. In that case, paste the post text into the comment field to reply to it, or into **Add conversation context** when replying to a particular comment.

URL fetching requires internet access. The webpage text is downloaded by the local server; it is then processed locally by your selected model. The app blocks non-public/local addresses and limits download size and redirects.

## Article-reader improvements (introduced in v1.5.1)

Reads publisher-supplied JSON-LD `articleBody` and article-tag paragraphs as well as ordinary text. If only a title or summary can be retrieved, the page shows a warning and the response prompt explicitly limits itself to that information. Some MSN pages still block access entirely, in which case use the original publisher link or paste the text. An article URL is never assumed to contain accessible full text.

## Lifecycle controls

Restart and Shutdown are available from the header. The updater never overwrites a live server; it installs only after the old process exits and then launches the application again.
