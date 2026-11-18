"""Translate dubbed speech timing into provider prompts and verify downloads."""
import csv
from pathlib import Path
import tempfile
import unicodedata


def words(text):
    clean = "".join(char if unicodedata.category(char)[0] in "LMN" else " "
                    for char in unicodedata.normalize("NFC", text).casefold())
    return clean.split()


def motion_timeline(shot, captions, speakers):
    tokens = []
    for start, _, text in captions:
        tokens.extend((word, start) for word in words(text))
    sequence = [word for word, _ in tokens]
    events = []
    for cue in shot.get("visual_cues", []):
        phrase = words(cue["phrase"])
        if not phrase:
            continue
        for i in range(len(sequence) - len(phrase) + 1):
            if sequence[i:i + len(phrase)] == phrase:
                events.append({"start": round(tokens[i][1], 2), "action": cue["action"]})
                break
    events.sort(key=lambda event: event["start"])
    return {"duration": shot["seconds"], "events": events, "speakers": [
        {"name": name, "start": round(start, 2), "end": round(end, 2)}
        for name, start, end in speakers
    ]}


def visual_prompts(look, story, timeline):
    events = " ".join(f"At {event['start']:g}s: {event['action']}" for event in timeline["events"])
    story_prompt = f"{events} {story}".strip()
    intervals = ", ".join(f"{segment['start']:g}–{segment['end']:g}s"
                          for segment in timeline["speakers"] if segment["name"] == "Narrator")
    performance = f"Speak during {intervals}; pause with mouth resting outside those windows. " if intervals else ""
    host_prompt = (f"{performance}{look}. Centered storyteller with natural blinking, small facial reactions, "
                   "restrained conversational hand gestures and gentle posture shifts. Consistent lighting and set.")
    return story_prompt, host_prompt


def inspect_clip(tool, ffmpeg, path, seconds):
    """Catch empty, corrupt, too-short or frozen outputs before compositing."""
    with tempfile.TemporaryDirectory(prefix=".motion-check-", dir=path.parent) as folder:
        raw = Path(folder) / "frames.md5"
        ffmpeg(tool, "-xerror", "-i", path, "-map", "0:v:0", "-an", "-t", seconds,
               "-vf", "fps=4,scale=64:36", "-f", "framemd5", raw)
        with raw.open(encoding="utf-8") as source:
            samples = [row[-1].strip() for row in csv.reader(source) if row and not row[0].startswith("#")]
    if len(samples) < (seconds - .75) * 4:
        raise RuntimeError(f"Provider clip {path.name} is shorter than the planned {seconds}s. Inspect {path.parent}.")
    if len(set(samples)) < 2:
        raise RuntimeError(f"Provider clip {path.name} contains no detectable frame motion. Inspect {path.parent}.")
