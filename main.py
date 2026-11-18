import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import sys
import subprocess
import tempfile
import textwrap
import wave

from content import BEATS, generate, key
from library import finish, job_name, slug
from terminal import conversation, interpret
from api_setup import active_key, check as api_check, setup as api_setup
from random_stories import choose_genre, genre_in
from studio import studio_main, studio_parser

ROOT = Path(__file__).resolve().parent
LABELS = ("INCOMING ALERT", "THE SETUP", "WHAT HAPPENED", "HOW TO STAY SAFE", "NEXT MISSION")
VIDEO_TYPES = {".mp4", ".mov", ".mkv"}
MUSIC_TYPES = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

def ffmpeg_path():
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        raise SystemExit("FFmpeg missing. Run python -m pip install -r requirements.txt.")

def ffmpeg(executable, *args, cwd=None):
    result = subprocess.run([executable, "-hide_banner", "-loglevel", "error", "-y", *map(str, args)],
                            cwd=cwd, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "FFmpeg failed.")

async def edge_voice(text, voice, path):
    import edge_tts

    words = []
    async with asyncio.timeout(35):
        with path.open("wb") as audio:
            stream = edge_tts.Communicate(text, voice, boundary="WordBoundary",
                                          connect_timeout=6, receive_timeout=12)
            async for chunk in stream.stream():
                if chunk["type"] == "audio":
                    audio.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 10_000_000
                    end = start + chunk["duration"] / 10_000_000
                    words.append((start, end, chunk["text"]))
    return words

async def edge_beats(data, voice, staging):
    return await asyncio.gather(*(edge_voice(data[beat], voice, staging / f"{index}.mp3")
                                  for index, beat in enumerate(BEATS)))

def windows_beats(data, staging):
    for index, beat in enumerate(BEATS):
        (staging / f"{index}.txt").write_text(data[beat], encoding="utf-8")
    command = """
Add-Type -AssemblyName System.Speech
$tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $tts.GetInstalledVoices() | Where-Object {
    $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'en-IN'
} | Select-Object -First 1
if ($voice) { $tts.SelectVoice($voice.VoiceInfo.Name) }
foreach ($i in 0..4) {
    $text = [IO.File]::ReadAllText((Join-Path (Get-Location) "$i.txt"))
    $tts.SetOutputToWaveFile((Join-Path (Get-Location) "$i.wav"))
    $tts.Speak($text)
    $tts.SetOutputToNull()
}
$tts.Dispose()
"""
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    "$ErrorActionPreference = 'Stop'\n" + command], cwd=staging, check=True)
    return [[] for _ in BEATS]

def stamp(seconds, ass=False):
    unit = 100 if ass else 1000
    total = round(seconds * unit)
    minutes, remainder = divmod(total, 60 * unit)
    hours, minutes = divmod(minutes, 60)
    secs, fraction = divmod(remainder, unit)
    if ass:
        return f"{hours}:{minutes:02}:{secs:02}.{fraction:02}"
    return f"{hours:02}:{minutes:02}:{secs:02},{fraction:03}"

def captions(text, words, duration, offset, tempo, slot):
    if not words:
        tokens = text.split()
        step = duration / len(tokens)
        words = [(i * step, (i + 1) * step, word) for i, word in enumerate(tokens)]
    groups = []
    group = []
    for word in words:
        if group and (len(group) == 6 or sum(len(item[2]) + 1 for item in group) + len(word[2]) > 45):
            groups.append(group)
            group = []
        group.append(word)
    groups.append(group)
    for index, group in enumerate(groups):
        start = max(0, group[0][0] / tempo)
        next_time = groups[index + 1][0][0] / tempo if index + 1 < len(groups) else slot
        end = min(slot, next_time, max(group[-1][1] / tempo + 0.22, start + 0.55))
        if end > start:
            yield offset + start, offset + end, textwrap.fill(" ".join(w[2] for w in group), 25)

def make_voice(executable, data, config, staging, duration, offline):
    source = "Windows Speech" if offline else "Edge TTS"
    if offline:
        timings = windows_beats(data, staging)
        extension = "wav"
    else:
        try:
            timings = asyncio.run(edge_beats(data, config["voice"], staging))
            extension = "mp3"
        except Exception as error:
            if os.name != "nt":
                raise RuntimeError(f"Edge TTS failed ({type(error).__name__}). Check your connection and voice.") from error
            print(f"Edge TTS unavailable ({type(error).__name__}). Using Windows Speech with estimated captions.", flush=True)
            timings = windows_beats(data, staging)
            extension = "wav"
            source = "Windows Speech"
    # Scale the same five beat windows across the 35–60 second range.
    boundaries = [0, duration * 0.06, duration * 0.30, duration * 0.66, duration * 0.90, duration]
    lines = []
    for index, beat in enumerate(BEATS):
        original = staging / f"{index}.{extension}"
        pcm = staging / f"pcm{index}.wav"
        ffmpeg(executable, "-i", original, "-vn", "-ac", "1", "-ar", "24000", pcm)
        with wave.open(str(pcm), "rb") as audio:
            length = audio.getnframes() / audio.getframerate()
        start, end = boundaries[index:index + 2]
        slot = end - start
        tempo = length / (slot - 0.10)
        if tempo < 0.83:
            tempo = 0.83
        ffmpeg(executable, "-i", pcm, "-af", f"atempo={tempo:.7f},apad", "-t", f"{slot:.7f}",
               staging / f"beat{index}.wav")
        lines.extend(captions(data[beat], timings[index], length, start, tempo, slot))
    concat = staging / "audio.txt"
    concat.write_text("".join(f"file beat{i}.wav\n" for i in range(len(BEATS))), encoding="ascii")
    ffmpeg(executable, "-f", "concat", "-safe", "1", "-i", concat, "-c:a", "libmp3lame",
           "-b:a", "96k", staging / "voice.mp3")
    return boundaries, lines, source

def ass_text(text):
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", r"\N")

def write_captions(staging, data, boundaries, lines, placeholder):
    entries = [f"{i}\n{stamp(start)} --> {stamp(end)}\n{text}\n"
               for i, (start, end, text) in enumerate(lines, 1)]
    (staging / "subtitles.srt").write_text("\n".join(entries), encoding="utf-8")
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,Arial,69,&H00FFFFFF,&H00FFFFFF,&H0016100C,&H9016100C,-1,0,0,0,100,100,0,0,1,7,3,2,130,150,360,1
Style: Header,Arial,39,&H00FFE277,&H00FFFFFF,&H0017100A,&H9017100A,-1,0,0,0,100,100,3,0,1,4,1,8,110,130,156,1
Style: Topic,Arial,84,&H00FFFFFF,&H00FFFFFF,&H0017100A,&H9017100A,-1,0,0,0,100,100,0,0,1,5,2,5,100,130,0,1
Style: Note,Arial,29,&H00E4C5A2,&H00FFFFFF,&H0017100A,&H9017100A,0,0,0,0,100,100,2,0,1,3,0,2,110,130,242,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    def add(start, end, style, text):
        events.append(f"Dialogue: 0,{stamp(start, True)},{stamp(end, True)},{style},,0,0,0,,{text}\n")
    for i, label in enumerate(LABELS):
        add(boundaries[i], boundaries[i + 1], "Header", label)
    topic = ass_text(textwrap.fill(data["topic"].upper()[:68], 17, max_lines=3, placeholder="..."))
    add(0, boundaries[-1] if placeholder else boundaries[1], "Topic", topic)
    if placeholder:
        add(0, boundaries[-1], "Note", "CYBERSHORTS  /  TEST BACKGROUND")
    important = re.compile(r"\b(OTP|passwords?|phishing|passkeys?|ransomware|VPN|malware|SQL|XSS)\b", re.I)
    for start, end, text in lines:
        colored = important.sub(lambda match: r"{\c&H00E2FF&}" + match[0] + r"{\c}", ass_text(text))
        add(start, end, "Caption", colored)
    (staging / "graphics.ass").write_text(header + "".join(events), encoding="utf-8-sig")

def files_in(folder, extensions):
    if not folder.is_dir():
        return []
    return [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in extensions]

def render(executable, staging, data, config, boundaries, lines):
    width, height = config["resolution"]
    duration = config["duration"]
    clips = files_in(ROOT / config["gameplay_folder"], VIDEO_TYPES)
    random.shuffle(clips)
    parts = []
    if not clips:
        print("No gameplay footage found. Rendering a placeholder background.", flush=True)
    colors = ("0x141C36", "0x202C43", "0x142E36", "0x102B31", "0x1A2441")
    for i, color in enumerate(colors):
        seconds = boundaries[i + 1] - boundaries[i]
        clip = clips[i % len(clips)] if clips else None
        target = staging / f"scene{i}.mp4"
        parts.append(target.name)
        common = ["-t", f"{seconds:.7f}", "-an", "-c:v", "libx264", "-preset", "ultrafast",
                  "-crf", "19", "-pix_fmt", "yuv420p", "-threads", "4", target]
        if clip:
            zoom = [1.04, 1.12, 1.07, 1.16, 1.04][i]
            wide, tall = math.ceil(width * zoom / 2) * 2, math.ceil(height * zoom / 2) * 2
            filters = (f"fps=30,scale={wide}:{tall}:force_original_aspect_ratio=increase,"
                       f"crop={width}:{height},setsar=1,eq=contrast=1.05:saturation=0.92,"
                       f"vignette=PI/8")
            try:
                ffmpeg(executable, "-stream_loop", "-1", "-i", clip, "-map", "0:v:0",
                       "-filter_threads", "2", "-vf", filters, *common)
                continue
            except RuntimeError:
                print(f"Could not read {clip.name}. Using a placeholder for scene {i + 1}.", flush=True)
        step = max(24, width // 12)
        filters = (f"drawgrid=x={i * 13}:y={i * 32}:w={step}:h={step}:t=2:c=0x68B6DA@0.10,"
                   f"drawbox=x=iw*0.11:y=ih*0.36:w=iw*0.78:h=ih*0.28:c=0x0A1324@0.8:t=fill,"
                   f"drawbox=x=iw*0.11:y=ih*0.36:w=iw*0.78:h=ih*0.28:c=0x64DFFF@0.35:t=3,"
                   f"vignette=PI/7")
        ffmpeg(executable, "-f", "lavfi", "-i", f"color={color}:s={width}x{height}:r=30",
               "-filter_threads", "2", "-vf", filters, *common)
    write_captions(staging, data, boundaries, lines, not clips)
    (staging / "video.txt").write_text("".join(f"file {name}\n" for name in parts), encoding="ascii")
    inputs = ["-f", "concat", "-safe", "1", "-i", "video.txt", "-i", "voice.mp3"]
    music = files_in(ROOT / config["music_folder"], MUSIC_TYPES)
    audio = ["-map", "0:v:0", "-map", "1:a:0"]
    if music:
        inputs += ["-stream_loop", "-1", "-i", random.choice(music)]
        audio = ["-filter_complex", "[2:a]volume=0.09[bg];[1:a][bg]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]",
                 "-map", "0:v:0", "-map", "[a]"]
    slug = re.sub(r"[^\w]+", "_", data["topic"].casefold()).strip("_")[:75] or "cyber"
    filename = f"{slug}_short.mp4"
    encode = ["-filter_threads", "2", "-vf", "ass=graphics.ass", "-t", duration, "-c:a", "aac",
              "-b:a", "128k", "-c:v", "libx264", "-preset", "veryfast", "-threads", "4",
              "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", filename]
    try:
        ffmpeg(executable, *inputs, *audio, *encode, cwd=staging)
    except RuntimeError:
        if not music:
            raise
        print("Background music could not be mixed. Rendering with narration only.", flush=True)
        ffmpeg(executable, *inputs[:8], "-map", "0:v:0", "-map", "1:a:0", *encode, cwd=staging)
    return filename

def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default

def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Create a cybersecurity story or an original AI video.")
    topic_option = parser.add_mutually_exclusive_group()
    topic_option.add_argument("--topic", help="Cybersecurity topic")
    topic_option.add_argument("--auto", action="store_true", help="Pick a fresh topic without prompting")
    parser.add_argument("--offline-voice", action="store_true", help="Use Windows Speech for an offline render")
    parser.add_argument("--api-setup", action="store_true")
    parser.add_argument("--api-check", action="store_true")
    studio_parser(parser)
    args = parser.parse_args()
    if args.demo_story:
        args.demo = True
    if args.prompt:
        request = interpret(args.prompt, None)
        args.random = args.random or request["random"]
        args.genre = args.genre or request["genre"]
        args.duration = args.duration if args.duration is not None else request["duration"]
        args.language = args.language or request["language"]
        args.style = args.style or request["style"]
    config = read_json(ROOT / "config.json", {}) | read_json(ROOT / "config.local.json", {})
    library_root = (ROOT / "videos").resolve()
    if not library_root.is_relative_to(ROOT.resolve()):
        raise ValueError("The videos folder must be inside the application directory.")
    config.update(output_folder="videos", named_library=True)
    if args.api_setup:
        return api_setup(ROOT, config)
    if args.api_check:
        return api_check(config)
    if args.random and not args.genre and not args.local_animation and not args.demo and sys.stdin.isatty():
        args.genre = genre_in(args.prompt or args.topic or "") or choose_genre(local=args.offline or not active_key(config))
        if args.genre is None:
            return
    if len(sys.argv) == 1 or args.studio:
        return conversation(args, ROOT, config, lambda run: studio_main(
            run, ROOT, config, ffmpeg_path, ffmpeg, captions, stamp))

    studio_requested = bool(args.mode or args.studio or args.prompt or args.resume or args.list_styles
                            or args.plan_only or args.duration or args.style or args.language
                            or args.locale or args.characters is not None or args.voice or args.format
                            or args.random or args.local_animation or args.seed is not None
                            or args.split_screen or args.split_demo or args.layout != "auto" or args.narrator
                            or args.video_backend != "auto" or args.demo or args.recurring_cast or args.cast_from
                            or args.research is not None)
    if not studio_requested and not args.offline_voice and (
        args.auto or (args.topic and key(args.topic) != "phishing")
    ):
        args.mode = "cyber"
    if args.mode or studio_requested:
        if args.offline_voice:
            parser.error("The Studio uses online Edge voices. Omit --offline-voice.")
        return studio_main(args, ROOT, config, ffmpeg_path, ffmpeg, captions, stamp)
    duration = config["duration"]
    width, height = config["resolution"]
    if type(duration) is not int or not 35 <= duration <= 60:
        parser.error("duration must be an integer from 35 to 60 seconds")
    if min(width, height) < 2 or width % 2 or height % 2 or width * 16 != height * 9:
        parser.error("resolution must use even dimensions with a 9:16 aspect ratio")
    if args.offline_voice and os.name != "nt":
        parser.error("--offline-voice requires Windows")
    executable = ffmpeg_path()
    topic = args.topic
    if not topic and not args.auto:
        try:
            topic = input("Cybersecurity topic (Enter for an automatic idea): ")
        except EOFError:
            pass
    topic = " ".join(topic.split())[:100] if topic else None
    mix = config["content_mix"]
    weights = [mix.get(mode, 0) for mode in ("funny", "educational", "serious")]
    if any(not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0 for weight in weights) or not any(weights):
        parser.error("content_mix requires nonnegative weights and at least one positive weight")
    mode = random.choices(("funny", "educational", "serious"), weights=weights)[0]
    history_file = ROOT / ".history.json"
    history = read_json(history_file, [])
    pilot = bool(topic and "phishing" in key(topic).split())
    if pilot:
        data = {"topic": "Phishing", "title": "Bunty ka ₹50,000 reward"}
    else:
        data, writer = generate(topic or None, mode, history, config, duration)
        pilot = not topic and key(data["topic"]) == "phishing"
    destination = ROOT / "videos" / job_name(data["title"])
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".render-", dir=destination) as folder:
        staging = Path(folder)
        if pilot:
            from episode import render_episode

            print("Topic: Phishing | Character episode: Bunty, Meera and Patch", flush=True)
            filename = render_episode(executable, staging, config, ffmpeg, edge_voice,
                                      stamp, captions, args.offline_voice)
        else:
            print(f"Topic: {data['topic']} | Tone: {mode} | Script: {writer}", flush=True)
            boundaries, lines, voice = make_voice(executable, data, config, staging, duration, args.offline_voice)
            print(f"Voice: {voice}. Rendering {width}x{height} video...", flush=True)
            filename = render(executable, staging, data, config, boundaries, lines)
            script = [f"Topic: {data['topic']}\nTone: {mode}\nScript: {writer}\nVoice: {voice}"]
            script += [f"{boundaries[i]:05.1f}–{boundaries[i + 1]:05.1f}s  {beat.upper()}\n{data[beat]}"
                       for i, beat in enumerate(BEATS)]
            (staging / "script.txt").write_text("\n\n".join(script) + "\n", encoding="utf-8")
            metadata = [f"Title: {data['title'][:100]}", f"Description: {data['description']}",
                        f"Hashtags: {' '.join(data['hashtags'])}", f"Tags: {', '.join(data['tags'])}",
                        f"Thumbnail text: {data['thumbnail']}"]
            (staging / "metadata.txt").write_text("\n\n".join(metadata) + "\n", encoding="utf-8")
        for name in ("script.txt", "voice.mp3", "subtitles.srt", "metadata.txt", filename):
            (staging / name).replace(destination / name)
    history.append({"topic": data["topic"], "title": data["title"]})
    temporary = history_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(history[-35:], ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(history_file)
    named = destination / (slug(data["title"], "cybersecurity_story") + ".mp4")
    (destination / filename).replace(named)
    finish(destination, data["title"], named, duration, f"{width}:{height}", "Hinglish", "original-pilot" if pilot else "legacy-explainer")

if __name__ == "__main__":
    try:
        main()
    except (EOFError, ImportError, OSError, RuntimeError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"CyberShorts: {error}") from error
