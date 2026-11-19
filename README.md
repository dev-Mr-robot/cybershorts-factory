# CyberShorts Factory

Describe a video in natural language. OpenAI's Responses API writes and checks the storyboard. Runway Gen‑4.5 generates moving clips, Edge TTS supplies the voices, and FFmpeg assembles the MP4. Hindi and vertical 1080×1920 are defaults. The previous 2D pilot renderer remains available explicitly.

## Install on Kali

```sh
sh install_kali.sh
Cyber
```

The installer lists missing packages and asks before using APT. Python packages go into the app's own virtual environment. If the installer says the launcher folder needs to be added to PATH, run the command it prints. On other Linux distributions use `sh install.sh`. On Windows use `powershell -NoProfile -File install.ps1`.

Manual Kali setup:

```sh
sudo apt update
sudo apt install python3 python3-venv ffmpeg mpv fonts-noto-core
sh install.sh
```

Kali's [Python environment guidance](https://www.kali.org/docs/general-use/python3-external-packages/) recommends isolating Python packages. A desktop session is needed for the video window.

## Configure online generation

Copy `.env.example` to `.env` and add your keys locally:

```dotenv
OPENAI_API_KEY=
VIDEO_PROVIDER_API_KEY=
```

Use an [OpenAI project API key](https://platform.openai.com/api-keys) and a [Runway API key](https://dev.runwayml.com/). Exported variables take precedence over `.env`. `RUNWAYML_API_SECRET` is accepted as an alternative video-key variable. Edge TTS needs internet access and uses no TTS key. Keep `.env` out of Git.

Run `Cyber --online-check` to test OpenAI JSON generation and read the Runway project's credit balance. A positive balance doesn't establish that there are enough credits for your whole film. OpenAI API billing and Runway's [video credits](https://docs.dev.runwayml.com/guides/pricing/) are separate. `Cyber --api-open` opens the OpenAI API key page.

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
