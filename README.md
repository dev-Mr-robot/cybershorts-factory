# Shadow Video AI

Describe a video in natural language. ChatGPT via Codex writes and checks the storyboard. The original full-screen 2D pilot animates the story, Edge TTS supplies the voices, and FFmpeg assembles the MP4. Hindi and vertical 1080×1920 are defaults.

## Install on Kali

```sh
sh install_kali.sh
videoai
```

The Kali installer lists missing packages and asks before using APT. It installs the official Codex CLI if needed. Python packages go into the app's own virtual environment. If the installer says the launcher folder needs to be added to PATH, run the command it prints. On other Linux distributions use `sh install.sh`. On Windows use `powershell -NoProfile -File install.ps1`.

Manual Kali setup:

```sh
sudo apt update
sudo apt install python3 python3-venv ffmpeg mpv fonts-noto-core curl
sh install_kali.sh
```

Kali's [Python environment guidance](https://www.kali.org/docs/general-use/python3-external-packages/) recommends isolating Python packages. A desktop session is needed for the video window.

## Sign in

After installation, run:

```sh
videoai
```

Press Enter at the sign-in prompt and approve the login in your browser. On a remote shell, type `device` or run `videoai --login --device-auth`. Device sign-in may need to be enabled in your ChatGPT or workspace security settings. On Windows, use `Cyber.cmd` in place of `videoai`.

The official Codex CLI stores and refreshes the account session in an app-specific state directory. Type `status` to see connections, `online check` to test them, and `logout` to sign out of Shadow Video AI. The equivalent flags are `--auth-status`, `--online-check`, and `--logout`.

ChatGPT sign-in enables screenplay and story review through Codex, subject to the account's plan and usage limits. Live source lookup uses a separately managed OpenAI Platform connection when available. Edge TTS uses the internet and needs no account.

Enter your idea in the prompt. Include a duration or genre if you have a preference. Otherwise the app uses its defaults and starts rendering immediately. It saves the MP4 and production files to `videos/` and offers playback.

The official [Sign in with ChatGPT developer route](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations) does not grant this CLI access to hosted image generation or connected media tools. The [Sora API was discontinued](https://help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation). The app automatically renders illustrated animation with ChatGPT-planned scenes and labels it accordingly. Existing deployments with managed video access can still use that backend.

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
