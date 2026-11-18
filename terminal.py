"""Prompt-first interactive terminal, using Studio for actual creation."""
import copy
import json
import os
import re
import sys

from library import phase

BANNER = r"""
+--------------------------------------------------+
|   V I D E O A I   /   C Y B E R S H O R T S      |
|   Full-screen pilot animation                   |
|   Hindi by default  /  Cinematic 2D               |
+--------------------------------------------------+
"""
LANG = {"hindi": "Hindi", "hinglish": "Hinglish", "english": "English",
        "punjabi": "Punjabi", "urdu": "Urdu", "bengali": "Bengali", "tamil": "Tamil",
        "telugu": "Telugu", "marathi": "Marathi", "gujarati": "Gujarati",
        "malayalam": "Malayalam", "kannada": "Kannada", "french": "French",
        "spanish": "Spanish", "japanese": "Japanese", "arabic": "Arabic", "chinese": "Chinese"}
STYLES = {"anime": "Anime", "pixelated": "Modern 3D Pixel Cinematic",
          "2d": "2D Cinematic Illustration", "documentary": "Documentary",
          "realistic": "Realistic cinematic", "cartoon": "Cartoon"}


def duration_hint(line):
    line = re.sub(r"\b(one|two|three|five|ten)\s+(?=minutes?\b)", lambda m: {
        "one": "1 ", "two": "2 ", "three": "3 ", "five": "5 ", "ten": "10 "}[m[1]], line)
    match = re.search(r"\b(\d+)\s*[- ]?\s*(seconds?|secs?|s\b|minutes?|mins?)\b", line)
    return int(match[1]) * (60 if match[2].startswith("m") else 1) if match else None


def interpret(text, prior):
    line = text.casefold().strip(" .!")
    language = next((value for name, value in LANG.items()
                     if re.search(rf"\b(?:in|to|use)\s+{name}\b|\b{name}\s+(?:video|story|dialogue)", line)), None)
    style = next((value for name, value in STYLES.items()
                  if re.search(rf"\b(?:use|in)\s+{name}\b|\b{name}\s+style\b", line)), None)
    timing = duration_hint(line)
    reuse = bool(re.search(r"same (?:character|cast)", line))
    revision = bool(prior and re.match(r"^(?:make it|make the|make a \d.*version|use |change |longer|shorter|one minute|two minutes|same )", line)
                    and (language or style or timing or reuse or "longer" in line or "shorter" in line or "smoother" in line))
    result = dict(prior) if revision else {"idea": text, "duration": None, "language": "Hindi",
                                            "style": "2D Cinematic Illustration", "random": False, "reuse": False}
    if language:
        result["language"] = language
    if style:
        result["style"] = style
    if timing is not None:
        result["duration"] = timing
    if revision and timing is None and ("longer" in line or "shorter" in line):
        result["duration"] = max(15, min(3600, (prior.get("duration") or 60) + (15 if "longer" in line else -15)))
    if revision and "smoother" in line:
        result["idea"] += "\nUse a stable character pose within each shot, eased movement and deliberate cuts."
    result["reuse"] |= reuse
    if not revision:
        result["random"] = line == "random" or bool(re.search(r"\b(random|another idea|another video)\b", line))
    return result


def latest_jobs(root):
    return sorted(root.glob("videos/**/metadata.json"), key=lambda item: item.stat().st_mtime, reverse=True)


def conversation(args, root, config, generate):
    colored = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
    print(f"\033[36;1m{BANNER}\033[0m" if colored else BANNER)
    print("Describe a video, or type help, random, demo, history, settings, new or exit.")
    prior = None
    while True:
        try:
            text = input("videoai > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        command = text.casefold().strip(".!")
        if command in {"exit", "quit", "bye", "बाहर"}:
            return
        if not text:
            continue
        if command in {"help", "menu"}:
            print('Try "Create a 30-second Hindi horror story in anime style". Afterward say "Make it longer".')
            print("Commands: demo, random, history, settings, new, exit")
            continue
        if command in {"new", "start over"}:
            prior = None
            print("What would you like to create?")
            continue
        if command == "history" or re.search(r"\b(previous videos|my videos|show.*history)\b", command):
            items = latest_jobs(root)
            for path in items[:10]:
                item = json.loads(path.read_text(encoding="utf-8"))
                print(f"{item['title']}  |  {path.parent / item['file']}")
            if not items:
                print("No videos in the new library yet.")
            continue
        if command == "settings":
            print("Hindi | Original Phishing pilot format | 1080×1920 portrait by default")
            print(root / "videos")
            continue
        run = copy.copy(args)
        run.studio = False
        openai = os.getenv("OPENAI_API_KEY") or config.get("openai_api_key")
        if command == "demo":
            run.demo = True
        else:
            if prior is None and re.search(r"\b(last|previous) video", command):
                for metadata in latest_jobs(root):
                    path = metadata.parent / "production.json"
                    if not path.is_file():
                        continue
                    project = json.loads(path.read_text(encoding="utf-8"))
                    spec, story = project["spec"], project["story"]
                    prior = {"idea": spec.get("idea") or story["summary"], "duration": spec.get("duration"),
                             "language": spec.get("language", "Hindi"), "style": story.get("style", "2D Cinematic Illustration"),
                             "random": False, "reuse": False}
                    break
            request = interpret(text, prior)
            prior = request
            if request["random"] and command in {"random", "random video", "make a random video", "create a random video", "create a random video for me", "create another video", "give me another idea"} and not openai:
                run.random = True
            elif not openai:
                print("Custom prompts need OPENAI_API_KEY for the screenplay. Type demo or random for the local illustrated stories.")
                continue
            else:
                if request["duration"] is None:
                    try:
                        answer = input("How long? Enter for 60 seconds: ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return
                    request["duration"] = duration_hint(answer.casefold()) or (int(answer) if answer.isdecimal() else 60)
                run.prompt = request["idea"]
                run.random = request["random"]
                run.duration, run.language, run.style = request["duration"], request["language"], request["style"]
                run.mode = "cyber" if re.search(r"\b(cyber\w*|scam\w*|hacker|phishing|malware)\b", run.prompt.casefold()) else "general"
                if request["reuse"]:
                    for metadata in latest_jobs(root):
                        source = metadata.parent / "production.json"
                        if source.exists() and any(metadata.parent.glob("*.jpg")):
                            run.cast_from = source
                            break
                    if not run.cast_from:
                        print("Create a Runway production first to reuse its cast artwork.")
                        continue
        try:
            phase("START", "Preparing production")
            generate(run)
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            print(f"VideoAI: {error}")
