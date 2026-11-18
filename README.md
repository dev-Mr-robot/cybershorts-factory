# CyberShorts Factory

## Default video format

New productions use the actual animated Phishing pilot renderer: its 2D sprite cast, full-screen portrait layout, 24 fps, distinct shot framings, dialogue cards and speech-timed mouths. This is the default for custom stories and `--demo`. Custom screenplay planning uses OpenAI and dialogue uses Edge TTS. Use `--video-backend runway` or `--demo --video-backend illustrated` to explicitly select the older alternate renderers.

Before rendering a custom story, Studio reviews what viewers will actually see and hear. If the logic is unclear, it revises the affected chapter and can add time for missing beats. The requested duration is a starting target. Review results and the final timeline are saved in `production.json`. The built-in refund demo uses an authored 60-second walkthrough.

## Linux

```sh
sudo apt install ffmpeg fonts-noto-core python3-venv   # Debian/Ubuntu
sh install.sh
./videoai
```

Python 3.11 or newer and an FFmpeg build with libass are required. The launcher uses the project virtual environment and can run from any directory. Add the application directory to your PATH if you want to invoke it as `videoai`.

Describe a story in your own words. Examples include "Make a 30-second Hindi horror story in anime style", "Make it longer", and "Use the same character as my previous video". Interactive settings stay in the conversation. Reuse of a character's saved visual references requires a previous Runway production. Commands include `help`, `menu`, `new`, `random`, `demo`, `history`, `settings`, and `exit`. Use `--cast-from path/to/production.json` for explicit reference reuse.

New renders go inside the application under `videos/` with separate job folders, safe video filenames, scripts, subtitles, per-shot audio and footage, and `metadata.json`. Old files under `output/` are preserved. Custom prompts require an OpenAI key for planning. Runway requires a separate key only when selected explicitly. With no keys, `random` rotates the authored demos. Edge TTS needs internet access.

## Windows

In this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The prompt-first terminal accepts defensive cybersecurity ideas and general original films. Scripted calls also accept `--mode cyber` and `--mode general`. Both create full-screen stories with Hindi and cinematic 2D illustration as defaults. Use `--recurring-cast` to reuse the established cyber characters. `--studio` opens the same menu explicitly.

Set `OPENAI_API_KEY` for planning and `RUNWAYML_API_SECRET` for moving footage in your shell. You can also set `openai_api_key` and `runway_api_key` in a private `config.local.json`. Edge TTS uses an internet connection. Studio sends prompts, character references and lines to the selected services and Runway jobs consume credits.

## Examples

```powershell
python main.py --mode cyber --topic "Password Security" --duration 60 --language Hinglish
python main.py --mode cyber --duration 30
python main.py --mode general --prompt "Two friends hear a mysterious signal from Mars" --duration 30 --language English --style "Pixel art"
python main.py --list-styles
```

- Use `--style auto` for a recommendation, a preset number, or custom style text. Use `--format portrait` or `--format landscape` for framing.
- Set `--characters 0` to `--characters 8` in General mode. Cyber mode starts with at least two. Each generated shot uses up to three visible character references. Use `--locale en-GB` to request an accent, or repeat `--voice "Bunty=hi-IN-MadhurNeural"` for exact Edge voice IDs. View the catalog with `python -m edge_tts --list-voices`.
- Use a language name or provider locale such as `fr-CA`. For invented languages, name the language in the prompt or language field and specify an approximate voice accent with `--locale`. The planner writes phonetic dialogue and translated subtitles. Edge gives distinct voices and changes delivery with rate and pitch. Exact emotion, pronunciation, lip sync and visual identity can vary by scene.
- Set `--duration` in seconds from 15 through 3600. A 60-minute film plans hundreds of short clips and can take substantial provider time and credits. Use `--plan-only` to review the saved screenplay and shot list before any Runway requests.
- Each production writes `movie.mp4`, `script.txt`, `subtitles.srt` and a resumable `production.json` under `videos/studio/`. Resume a plan or interrupted render with `python main.py --resume JOB_NAME`. Optional music goes in `assets/music/`; otherwise the editor uses its own quiet synth bed. Generated scenes use Runway Gen-4.5 motion, with reference-guided first frames for character shots, and are dubbed and assembled with FFmpeg.

## Random video

```powershell
python main.py --random
python main.py --random --local-animation
python main.py --random --local-animation --style Pixelated --seed 379826793
```

Each new job receives a seed for creative direction, pacing, visual treatment and music. Studio also passes recent concepts to the planner and carries a continuity brief and character references between shots. A recurring location can get its own visual reference. A seed is reproducible for local animation. Cloud planning and footage can still vary with the same seed. Use `--resume` to continue a specific Studio plan.

With both API keys present, `--random` runs the full AI video pipeline. Without both keys, a plain `--random` renders the authored full-screen Hindi 2D fallback. With an explicit `--local-animation`, it instead renders an English **Modern 3D Pixel Cinematic** short from a small story library. It varies casting, palettes, camera direction and music, and rotates recent premises. The local renderer uses an OpenGL 3.3 graphics driver for actual 3D geometry, shaded pixel materials, cast shadows, atmospheric depth, and moving cameras. It needs Edge TTS for dialogue, supports 24–120 seconds in landscape, and saves under `videos/random/`.

## Pixel styles

`Pixelated`, `Pixel Art`, and preset `5` select **Modern 3D Pixel Cinematic**. Other Studio presets include High-Resolution Pixel Art, 3D Voxel Cinematic, Pixel-Shader 3D, Hybrid 3D + Pixel, Pixel Cyberpunk, Pixel Fantasy, and Pixel Realism. These are distinct Runway art directions. The local generator implements Modern 3D Pixel Cinematic plus **Retro Pixel Art**, which is available only by explicit selection (for example, `--style "Retro Pixel Art"` or `--style "8-bit"`).

## Full-screen Hindi demo

```powershell
python main.py --demo
python main.py --demo --video-backend illustrated
python main.py --demo --video-backend runway
```

**पैसे आए या गए?** is a six-scene Hindi short about a fake refund and a friend who notices the payment warning. Use `--demo-story flame` for **शहर की आख़िरी लौ**, the earlier rooftop story. The default uses the original Phishing pilot renderer. Runway Gen-4.5 is available with explicit backend selection. The illustrated version uses original ImageGen art, articulated 2D animation, Edge TTS, Devanagari captions, and an original soundtrack. The built-in screenplay is authored, so `--demo` needs no planning key. The illustrated version is available without paid video credits. Both render full-screen.

Custom productions have stable cast reference images, a character-design manifest, and per-shot timing and provider records. When available, captions and dialogue timings guide generated movement. Text-based timing is approximate. Custom generation requires OpenAI for the screenplay and Runway for moving clips. Prior split-screen files are archived.

## Existing animated pilot

`python main.py --topic "Phishing"` still renders the locally illustrated Bunty, Meera and Patch episode. It needs Edge TTS but uses neither the OpenAI nor Runway API key. To make a new Phishing film with Runway, use `--mode cyber --topic "Phishing"`.

Provider references: [Runway API](https://docs.dev.runwayml.com/api/), [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), and [Edge TTS](https://github.com/rany2/edge-tts).

## Example

[Download the 60-second Hindi refund-scam demo](examples/paise_aaye_ya_gaye.mp4). It uses the original Phishing pilot renderer.
