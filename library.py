"""Output naming and terminal feedback, shared by the production paths."""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import uuid

from providers import save_json


def slug(title, fallback="animated_story"):
    words = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", words.casefold()).strip("_")[:72].rstrip("_") or fallback


def job_name(title):
    return f"{slug(title)}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"


def phase(stage, detail):
    if sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb":
        print(f"\033[36;1m[{stage}]\033[0m {detail}", flush=True)
    else:
        print(f"[{stage}] {detail}", flush=True)


def finish(job, title, video, duration, resolution, language, renderer):
    save_json(job / "metadata.json", {
        "title": title, "file": video.name, "duration_seconds": duration,
        "resolution": resolution.replace(":", "x"), "language": language,
        "renderer": renderer,
    })
    phase("COMPLETE", f"{title} | {video.name} | {resolution.replace(':', 'x')} | {duration}s | {language}")
    print(video.resolve(), flush=True)


def completed_video(job):
    metadata = job / "metadata.json"
    if metadata.is_file():
        name = json.loads(metadata.read_text(encoding="utf-8")).get("file", "")
        if name and Path(name).name == name and (job / name).is_file():
            return job / name
    old = job / "movie.mp4"
    return old if old.is_file() else None
