# Shadow Video AI

Describe a video in natural language. ChatGPT via Codex writes and checks the storyboard. Runway Gen‑4.5 generates moving clips, Edge TTS supplies the voices, and FFmpeg assembles the MP4. Hindi and vertical 1080×1920 are defaults. The previous 2D pilot renderer remains available explicitly.

## Install on Kali

```sh
sh install_kali.sh
videoai
```

The installer lists missing packages and asks before using APT. Python packages go into the app's own virtual environment. If the installer says the launcher folder needs to be added to PATH, run the command it prints. On other Linux distributions use `sh install.sh`. On Windows use `powershell -NoProfile -File install.ps1`.

Manual Kali setup:

```sh
sudo apt update
sudo apt install python3 python3-venv ffmpeg mpv fonts-noto-core
sh install.sh
```

Kali's [Python environment guidance](https://www.kali.org/docs/general-use/python3-external-packages/) recommends isolating Python packages. A desktop session is needed for the video window.

## Sign in

Install the [official Codex CLI](https://developers.openai.com/codex/cli/) and make sure `codex` is on PATH. Then run:

```sh
videoai
```

Press Enter at the sign-in prompt and approve the login in your browser. On a remote shell, type `device` or run `videoai --login --device-auth`. Device sign-in may need to be enabled in your ChatGPT or workspace security settings. On Windows, use `Cyber.cmd` in place of `videoai`.

The official Codex CLI stores and refreshes the account session in an app-specific state directory. Type `status` to see connections, `online check` to test them, and `logout` to sign out of Shadow Video AI. The equivalent flags are `--auth-status`, `--online-check`, and `--logout`.

ChatGPT sign-in enables screenplay and story review through Codex, subject to the account's plan and usage limits. Live source lookup uses a separately managed OpenAI Platform connection when available. Edge TTS uses the internet and needs no account.

The CLI's Runway adapter uses the [Runway developer API](https://docs.dev.runwayml.com/guides/setup/). A deployment administrator can provide a funded project via `VIDEO_PROVIDER_API_KEY` (or `RUNWAYML_API_SECRET`). A managed `OPENAI_API_KEY` is also supported for existing deployments. End users are never prompted for keys. Runway's [separate browser-authorized media connector](https://help.runwayml.com/hc/en-us/articles/51931843164691-Connecting-to-Runway-MCP) can generate media inside supported clients, but is not wired to this CLI's clip assembler. Choose the illustrated pilot when the CLI has no Runway connection.

## Create and watch

Type an idea into `Cyber`, or run:

```sh
Cyber --prompt 'एक हॉरर कहानी बनाओ, हिंदी में, 2 मिनट की।'
Cyber --random --genre comedy --duration 45
Cyber --play
```

Each production is saved under `videos/`, with its MP4, script, SRT, per-scene audio, and metadata. In the interactive CLI, choose **Play** after the export or type `play last` at the prompt. The mpv window supplies the timeline, elapsed and total time, pause, fullscreen and volume. Space pauses, arrows seek, 9/0 adjust volume, f toggles fullscreen, and q stops playback and returns to Cyber.

`Cyber --play /path/to/video.mp4 --subtitles /path/to/dialogue.srt` attaches an optional external SRT. Cyber already burns its own captions into the video. mpv starts with software decoding and a window sized to the display. If mpv is missing, Cyber tries ffplay for basic playback.

- Run `Cyber --player-check` to inspect FFmpeg, FFprobe, player, display, and available mpv decoder and audio drivers. It takes playback to verify the actual display and sound device.
- On a headless session, copy the MP4 to a desktop or use `mpv --vo=null /path/to/video.mp4` for audio only.
- Use `--plan-only` for a screenplay without Runway clips. Use `--video-backend pilot` for an online screenplay with the original illustrated renderer, or `Cyber --offline --demo` for the authored local screenplay and illustrated renderer. Voices still use the online Edge service.

## Example

[Watch the earlier 60-second Hindi refund-scam demo](examples/paise_aaye_ya_gaye.mp4). It uses the illustrated pilot renderer.
