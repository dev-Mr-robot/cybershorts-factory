"""The Phishing pilot. Scene cues drive voice, animation, props and captions."""
import asyncio
from array import array
from dataclasses import dataclass
from functools import lru_cache
import math
import os
from pathlib import Path
import subprocess
import textwrap
import wave

from PIL import Image, ImageDraw, ImageFont, ImageOps

from sprites import CAST, sprite

FPS = 24
W, H = 540, 960
VOICES = {"BUNTY": "hi-IN-MadhurNeural", "MEERA": "hi-IN-SwaraNeural", "PATCH": "en-IN-PrabhatNeural"}

@dataclass(frozen=True)
class Shot:
    speaker: str
    line: str
    camera: str
    mood: str
    gesture: str
    event: str
    weight: float

SHOTS = (
    Shot("BUNTY", "Meera, chai meri taraf se! Aaj mera lucky day hai.", "wide", "happy", "down", "walk", 4.0),
    Shot("BUNTY", "Oye! Pachaas hazaar ka reward! Chai ke saath samose bhi!", "phone", "happy", "phone", "reward", 4.9),
    Shot("MEERA", "Ruk. Ye link dekh. Teri game company ka naam tak galat hai.", "single", "confused", "point", "warning", 5.4),
    Shot("BUNTY", "Arre ek click hi toh hai. Login bhi kar diya. Ab dekh!", "phone", "happy", "phone", "tap", 5.2),
    Shot("BUNTY", "Arre! Naya login? Mera password kisne badla? Meera!", "phone", "shock", "phone", "lock", 4.8),
    Shot("MEERA", "Patch, idhar aa. Isne account ka password reward form mein daal diya.", "duo", "angry", "point", "patch", 5.4),
    Shot("PATCH", "Ye phishing hai, bhai. Page game jaisa tha. Password seedha scammer ko gaya.", "single", "confused", "shrug", "diagnose", 5.5),
    Shot("MEERA", "Asli app khol. Official help se account recover kar, phir baaki logins hata.", "duo", "confused", "point", "recover", 5.7),
    Shot("BUNTY", "Ho gaya! Naya password, two-factor on. Ab reward sirf asli app mein check karunga.", "phone", "happy", "phone", "safe", 5.6),
    Shot("BUNTY", "Chai meri taraf se. Samose sponsor karega? Follow kar lo yaar!", "wide", "happy", "shrug", "end", 4.6),
)

PHONE = {
    "reward": ("INCOMING MESSAGE", "YOU WON", "₹50,000", "CLAIM REWARD", "#ffe079"),
    "tap": ("REWARD PAGE", "Sign-in sent", "", "Loading...", "#ffe079"),
    "lock": ("ACCOUNT ALERT", "New login", "Password changed", "ACCESS LOST", "#ff728a"),
    "recover": ("OFFICIAL APP", "Account recovery", "Sign out other devices", "REVIEW DEVICES", "#8cf5e0"),
    "safe": ("SECURITY CHECK", "Account recovered", "2-factor is on", "ACCOUNT SECURED", "#8cf5e0"),
}

@lru_cache(maxsize=24)
def font(size, bold=True):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size=size)

def fit_font(draw, text, width, size):
    while size > 12 and draw.textlength(text, font=font(size)) > width:
        size -= 1
    return font(size)

def draw_phone(frame, event, local, phone=None):
    d = ImageDraw.Draw(frame)
    title, heading, value, button, color = phone or PHONE[event]
    slide = round(65 * (1 - min(1, local * 5)) ** 2)
    x, y = 278 + slide, 313
    d.rounded_rectangle((x + 8, y + 11, x + 246, y + 356), 27, fill="#120d20")
    d.rounded_rectangle((x, y, x + 236, y + 344), 24, fill="#302441", outline=color, width=3)
    d.rounded_rectangle((x + 9, y + 10, x + 226, y + 333), 19, fill="#1a192b")
    d.rounded_rectangle((x + 91, y + 20, x + 145, y + 25), 2, fill="#665978")
    d.text((x + 118, y + 65), title, fill=color, font=font(15), anchor="mm")
    d.line((x + 24, y + 88, x + 212, y + 88), fill="#564764", width=2)
    d.text((x + 118, y + 142), heading, fill="white", font=fit_font(d, heading, 203, 25), anchor="mm")
    d.text((x + 118, y + 192), value, fill="white", font=fit_font(d, value, 203, 32), anchor="mm")
    d.rounded_rectangle((x + 23, y + 246, x + 213, y + 289), 9, fill=color)
    d.text((x + 118, y + 267), button, fill="#171326", font=fit_font(d, button, 175, 17), anchor="mm")
    if event == "tap" and local < 0.48:
        radius = 16 + round(local * 74)
        d.ellipse((x + 118 - radius, y + 268 - radius, x + 118 + radius, y + 268 + radius),
                  outline="#fff4c9", width=4)

@lru_cache(maxsize=180)
def actor(name, mood, gesture, mouth, stride, height):
    art = sprite(name, mood, gesture, mouth, stride)
    return art.resize((round(art.width * height / art.height), height), Image.Resampling.BILINEAR)

def place(frame, name, center, top, height, shot, local, talking, walk=False, motion_speaker=None):
    active = name == shot.speaker
    mood = shot.mood if active else ("shock" if shot.event == "lock" else "confused")
    gesture = shot.gesture if active else "down"
    mouth = (1 + int(local * 10) % 2) if name == (motion_speaker or shot.speaker) and talking else 0
    stride = (8 if int(local * 5) % 2 else -8) if walk else 0
    art = actor(name, mood, gesture, mouth, stride, height)
    bob = round(math.sin(local * (12 if walk else 4.0)) * (6 if walk else 3))
    frame.paste(art, (round(center - art.width / 2), top + bob), art)

def frame_at(background, shot, index, local, length, spoken, caption, *,
             partner=None, count=10, label="PORT NAGAR  /  PHISHING",
             speaker_label=None, phone=None, motion_speaker=None, evidence=None):
    cut = round(13 * local / length)
    box = (36 + cut, 31 + cut, background.width - 36 - cut, background.height - 31 - cut)
    frame = background.resize((W, H), Image.Resampling.BILINEAR, box)
    if shot.event == "lock" and local < 0.32:
        frame = Image.blend(frame, Image.new("RGB", frame.size, "#b71e45"), 0.38 * (1 - local / 0.32))
    def draw_actor(name, center, top, height, cue, time, audio, walk=False):
        place(frame, name, center, top, height, cue, time, audio, walk, motion_speaker)

    if shot.camera == "single":
        draw_actor( shot.speaker, 272, 191, 1160, shot, local, spoken)
    elif shot.camera == "phone":
        draw_actor( shot.speaker, 154, 257, 850, shot, local, spoken)
        draw_phone(frame, shot.event, local, phone)
    elif shot.camera == "duo":
        other = partner or ("PATCH" if shot.event in ("patch", "recover") else "BUNTY")
        draw_actor( other, 375, 272, 643, shot, local, spoken)
        draw_actor( shot.speaker, 165, 240, 745, shot, local, spoken)
        if shot.event == "recover":
            draw_phone(frame, shot.event, local, phone)
    else:
        walking = shot.event == "walk"
        draw_actor( partner or "MEERA", 354, 342, 478, shot, local, spoken)
        draw_actor( shot.speaker if partner else "BUNTY", 161 - (min(96, 105 - local * 28) if walking and local < 3.75 else 0),
              333, 502, shot, local, spoken, walk=walking)

    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((29, 56, 266, 118), 12, fill="#18152c")
    d.text((44, 69), "CYBERSHORTS", fill="#f4eaff", font=font(19))
    d.text((44, 94), label[:34], fill="#a3a0bc", font=font(11))
    d.rounded_rectangle((433, 62, 506, 110), 11, fill="#231832")
    d.text((469, 86), f"{index + 1:02d}/{count:02d}", font=font(16), fill="#d6c5ee", anchor="mm")
    if evidence:
        heading, detail = evidence
        d.rounded_rectangle((36, 138, 504, 217), 12, fill="#18152c", outline="#8cf5e0", width=2)
        d.text((53, 153), heading, fill="#8cf5e0", font=fit_font(d, heading, 428, 18))
        d.text((53, 180), detail, fill="#f9f5ed", font=fit_font(d, detail, 428, 21))
    if shot.event == "lock" and local < 1.5:
        d.text((267, 209), "MISSION FAILED", font=font(44), fill="#ff7f9e",
               stroke_width=4, stroke_fill="#221026", anchor="mm")
    if caption or speaker_label:
        color = CAST[motion_speaker or shot.speaker]["accent"]
        d.rounded_rectangle((31, 750, 499, 867), 16, fill="#171427", outline=color, width=2)
        edge = 77 if shot.camera == "phone" else 175
        d.polygon(((edge, 746), (edge + 12, 733), (edge + 26, 751)), fill=color)
        d.text((51, 762), speaker_label or shot.speaker, font=font(14), fill=color)
        d.multiline_text((51, 787), caption, font=font(25), fill="#fff8ef", spacing=3)
    return frame

def make_score(path, shot_starts, sample_count):
    """A quiet synth bed plus short, original notification and lockout cues."""
    rate = 16000
    notes = (110, 110, 130.81, 98)
    start_times = [shot_starts[i] for i in (1, 3, 4, 8)]
    audio = array("h")
    for sample in range(sample_count):
        t = sample / rate
        beat = t % 0.52
        bass = notes[int(t / 2.08) % 4]
        value = 450 * math.sin(math.tau * bass * t) * math.exp(-beat * 7)
        value += 115 * math.sin(math.tau * bass * 3 * t)
        for index, start in enumerate(start_times):
            age = t - start
            if 0 <= age < 0.40:
                frequency = (840, 540, 190, 1040)[index]
                value += 2100 * math.sin(math.tau * frequency * age) * math.exp(-age * 12)
        audio.append(round(value * min(1, t * 4, (sample_count - sample) / (rate * 0.3))))
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(audio.tobytes())

async def all_dialogue(edge_voice, staging, voices):
    return await asyncio.gather(*(edge_voice(shot.line, voices[shot.speaker], staging / f"spoken{i}.mp3")
                                  for i, shot in enumerate(SHOTS)))

def render_episode(executable, staging, config, ffmpeg, edge_voice, stamp, captions, offline=False):
    voices = VOICES | config.get("character_voices", {})
    if offline:
        raise RuntimeError("The character episode requires Edge TTS for its three distinct voices.")
    try:
        timings = asyncio.run(all_dialogue(edge_voice, staging, voices))
    except Exception as error:
        raise RuntimeError(f"Character dialogue synthesis failed ({type(error).__name__}). Check Edge TTS access and character voices.") from error
    duration = config["duration"]
    total_weight = sum(shot.weight for shot in SHOTS)
    marks = [0]
    elapsed = 0
    cues = []
    talking_times = []
    for index, shot in enumerate(SHOTS):
        elapsed += shot.weight
        marks.append(round(duration * FPS * elapsed / total_weight))
        slot = (marks[-1] - marks[-2]) / FPS
        pcm = staging / f"raw{index}.wav"
        ffmpeg(executable, "-i", staging / f"spoken{index}.mp3", "-ac", "1", "-ar", "24000", pcm)
        with wave.open(str(pcm), "rb") as audio:
            spoken = audio.getnframes() / audio.getframerate()
        tempo = max(0.86, spoken / (slot - 0.22))
        ffmpeg(executable, "-i", pcm, "-af", f"atempo={tempo:.7f},apad", "-t", slot,
               staging / f"line{index}.wav")
        talking_times.append([(a / tempo, b / tempo) for a, b, _ in timings[index]] or [(0, spoken / tempo)])
        offset = marks[-2] / FPS
        cues.append(list(captions(shot.line, timings[index], spoken, offset, tempo, slot)))
    (staging / "lines.txt").write_text("".join(f"file line{i}.wav\n" for i in range(len(SHOTS))), encoding="ascii")
    ffmpeg(executable, "-f", "concat", "-safe", "1", "-i", "lines.txt", "-c:a", "libmp3lame",
           "-b:a", "96k", "voice.mp3", cwd=staging)
    make_score(staging / "score.wav", [mark / FPS for mark in marks], duration * 16000)
    background_path = Path(__file__).resolve().parent / "assets" / "story" / "city.png"
    with Image.open(background_path) as image:
        background = ImageOps.fit(image.convert("RGB"), (660, 1050))
    width, height = config["resolution"]
    filename = "phishing_short.mp4"
    command = [executable, "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
               "-i", "voice.mp3", "-i", "score.wav", "-filter_threads", "2",
               "-vf", f"scale={width}:{height}:flags=bicubic,setsar=1",
               "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]",
               "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "libx264", "-preset", "veryfast",
               "-threads", "4", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", filename]
    print("Rendering 10 animated character shots...", flush=True)
    with (staging / "encoder.log").open("w+b") as errors:
        with subprocess.Popen(command, cwd=staging, stdin=subprocess.PIPE, stderr=errors) as encoder:
            try:
                for index, shot in enumerate(SHOTS):
                    for frame_number in range(marks[index], marks[index + 1]):
                        t = frame_number / FPS
                        local = (frame_number - marks[index]) / FPS
                        length = (marks[index + 1] - marks[index]) / FPS
                        talking = any(start <= local <= end + 0.04 for start, end in talking_times[index])
                        current = next((line for start, end, line in cues[index] if start <= t < end), "")
                        frame = frame_at(background, shot, index, local, length, talking, current)
                        encoder.stdin.write(frame.tobytes())
            except BrokenPipeError:
                pass
            finally:
                encoder.stdin.close()
            if encoder.wait():
                errors.seek(0)
                raise RuntimeError(errors.read().decode("utf-8", "replace"))
    entries = [(shot.speaker, start, end, line) for shot, shot_cues in zip(SHOTS, cues)
               for start, end, line in shot_cues]
    (staging / "subtitles.srt").write_text("\n".join(
        f"{i}\n{stamp(start)} --> {stamp(end)}\n{speaker}: {line}\n"
        for i, (speaker, start, end, line) in enumerate(entries, 1)), encoding="utf-8")
    screenplay = "\n\n".join(
        f"{marks[i] / FPS:05.1f}s | {shot.camera.upper()} | {shot.event.upper()}\n{shot.speaker}: {shot.line}"
        for i, shot in enumerate(SHOTS))
    (staging / "script.txt").write_text("PHISHING | Port Nagar\n\n" + screenplay + "\n", encoding="utf-8")
    (staging / "metadata.txt").write_text(
        "Title: Bunty ka ₹50,000 reward | Phishing Mini Episode\n\n"
        "Description: Bunty ko laga reward mil gaya. Meera aur Patch ne sikhaaya ki fake login se kaise bachein.\n\n"
        "Hashtags: #Phishing #Hinglish #CyberSecurity #Shorts\n\n"
        "Tags: phishing, Hinglish animation, gaming story, cybersecurity\n\n"
        "Thumbnail text: ₹50,000 KA TRAP\n", encoding="utf-8")
    return filename
