"""Prompt-first interactive terminal, using Studio for actual creation."""
import asyncio
import copy
import json
import os
import re
import sys

from library import phase
from api_setup import active_key, check, planning_access
from chatgpt_planner import HELP, INSTALL, account, codex_executable, signed_in
from cloud import video_key
from random_stories import genre_in
import player

BANNER = r"""
+--------------------------------------------------+
|                SHADOW VIDEO AI                   |
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
    hindi = re.search(r"(\d+)\s*[- ]?\s*(सेकंड|सेकेण्ड|मिनट)", line)
    if hindi:
        return int(hindi[1]) * (60 if hindi[2] == "मिनट" else 1)
    if "एक मिनट" in line:
        return 60
    line = re.sub(r"\b(one|two|three|five|ten)\s+(?=minutes?\b)", lambda m: {
        "one": "1 ", "two": "2 ", "three": "3 ", "five": "5 ", "ten": "10 "}[m[1]], line)
    match = re.search(r"\b(\d+)\s*[- ]?\s*(seconds?|secs?|s\b|minutes?|mins?)\b", line)
    return int(match[1]) * (60 if match[2].startswith("m") else 1) if match else None


def choose_duration(local=False):
    minimum, maximum, default = (24, 60, 28) if local else (15, 3600, 60)
    while True:
        try:
            answer = input(f"How many seconds? [{default}, {minimum}–{maximum}, or cancel]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if answer.casefold() in {"cancel", "exit", "quit", "रद्द"}:
            return None
        seconds = default if not answer else int(answer) if answer.isdecimal() else duration_hint(answer.casefold())
        if seconds is not None and minimum <= seconds <= maximum:
            return seconds
        print(f"Enter a duration from {minimum} to {maximum} seconds.")


def interpret(text, prior):
    line = text.casefold().strip(" .!")
    language = next((value for name, value in LANG.items()
                     if line == name or re.search(rf"\b(?:in|to|use)\s+{name}\b|\b{name}\s+(?:video|story|dialogue)", line)), None)
    language = language or next((value for term, value in {
        "हिंदी": "Hindi", "हिन्दी": "Hindi", "अंग्रेज़ी": "English", "अंग्रेजी": "English",
        "पंजाबी": "Punjabi", "उर्दू": "Urdu", "हिंग्लिश": "Hinglish",
    }.items() if term in line), None)
    genre = genre_in(line)
    style = next((value for name, value in STYLES.items()
                  if line == name or re.search(rf"\b(?:use|in)\s+{name}\b|\b{name}\s+style\b", line)), None)
    timing = duration_hint(line)
    reuse = bool(re.search(r"same (?:character|cast)", line))
    revision = bool(prior and (line in LANG or line in STYLES or re.match(r"^(?:इसे|इसको|make it|make the|make a \d.*version|use |change |longer|shorter|one minute|two minutes|same )", line))
                    and (language or style or timing or reuse or genre or any(w in line for w in ("longer", "shorter", "smoother", "लंबा", "छोटा"))))
    result = dict(prior) if revision else {"idea": text, "duration": None, "language": "Hindi",
                                            "style": "2D Cinematic Illustration", "random": False, "reuse": False, "genre": None}
    result["revision"] = revision
    if genre:
        result["genre"] = genre
    if language:
        result["language"] = language
    if style:
        result["style"] = style
    if timing is not None:
        result["duration"] = timing
    if revision and timing is None and any(w in line for w in ("longer", "shorter", "लंबा", "छोटा")):
        result["duration"] = max(15, min(3600, (prior.get("duration") or 60) + (15 if "longer" in line or "लंबा" in line else -15)))
    if revision and "smoother" in line:
        result["idea"] += "\nUse a stable character pose within each shot, eased movement and deliberate cuts."
    result["reuse"] |= reuse
    if not revision:
        result["random"] = bool(re.search(r"\b(random|another idea|another video|surprise me)\b", line)) or any(word in line for word in ("रैंडम", "यादृच्छिक", "कोई भी"))
    return result


def latest_jobs(root):
    return sorted(root.glob("videos/**/metadata.json"), key=lambda item: item.stat().st_mtime, reverse=True)


def service_status(config, verify=False):
    logged_in = signed_in()
    print("[CHATGPT] Signed in through Codex." if logged_in else f"[CHATGPT] Signed out. {HELP}")
    if not codex_executable():
        print(f"[CHATGPT] {INSTALL}")
    if active_key(config):
        print("[OPENAI] Managed Responses API access configured.")
    text_ok = check(config) if verify else bool(logged_in or active_key(config))
    runway = video_key(config)
    video_ok = not runway
    if runway and verify:
        from studio import check_video_provider
        try:
            video_ok = check_video_provider(runway)
        except (OSError, RuntimeError, ValueError) as error:
            print(f"[RUNWAY] {error}")
    elif runway:
        print("[RUNWAY] Managed connection configured. Run videoai --online-check to verify it.")
    else:
        print("[VIDEO] Full-screen illustrated animation available. Account-only generative video is unavailable.")
    if runway:
        print("[IMAGES] Managed Runway image generation is verified during rendering.")
    voice_ok = False
    if verify:
        try:
            import edge_tts
            voices = asyncio.run(asyncio.wait_for(edge_tts.list_voices(), timeout=15))
            voice_ok = any(voice.get("Locale") == "hi-IN" for voice in voices)
            print("[VOICE] Edge TTS lists Hindi voices." if voice_ok else "[VOICE] Hindi voice unavailable.")
        except (ImportError, OSError, RuntimeError, TimeoutError, ValueError) as error:
            print(f"[VOICE] Edge TTS voice check failed ({type(error).__name__}).")
    else:
        print("[VOICE] Edge TTS uses an online connection and requires no account.")
    return text_ok and (not verify or (video_ok and voice_ok))


def conversation(args, root, config, generate):
    colored = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
    print(f"\033[36;1m{BANNER}\033[0m" if colored else BANNER)
    if not args.offline and sys.stdin.isatty() and not planning_access(config):
        if codex_executable():
            print("[CHATGPT] Press Enter to sign in with your browser. Type device for remote login, or skip.")
            try:
                choice = input("Sign in > ").strip().casefold()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if choice in {"", "device"} and account("login", device=choice == "device"):
                service_status(config, verify=True)
        else:
            print(f"[CHATGPT] {INSTALL}")
    print("नमस्ते! आज कैसी वीडियो बनानी है?")
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
            print("Commands: demo, random, history, settings, login, login device, logout, status, new, exit")
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
        if command in {"play", "play last"}:
            player.play(player.latest(root))
            continue
        if command == "settings":
            print("Hindi | Original Phishing pilot format | 1080×1920 portrait by default")
            print(root / "videos")
            continue
        if command in {"login", "login device", "logout", "status", "online check"}:
            if command == "status":
                service_status(config)
            elif command == "online check":
                service_status(config, verify=True)
            elif command == "logout":
                account("logout")
            elif account("login", device=command == "login device"):
                service_status(config, verify=True)
            continue
        run = copy.copy(args)
        run.studio = False
        run.offline = run.offline or "offline" in command.split()
        openai = "" if run.offline else planning_access(config)
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
            if request["random"] and run.offline:
                if request["language"] != "Hindi":
                    print("The local story bank is in Hindi. Type login to use ChatGPT for other languages.")
                    continue
                run.random = True
                run.genre = request.get("genre")
                run.duration = request["duration"]
                if request["revision"] and (run.genre in (None, "any", request.get("last_local_genre"))):
                    run.local_story = request.get("last_local_story")
            elif not openai:
                print(f"{HELP} You can also type login here.")
                continue
            else:
                run.prompt = request["idea"]
                run.random = request["random"]
                run.genre = request.get("genre")
                run.duration, run.language, run.style = request["duration"], request["language"], request["style"]
                run.mode = "cyber" if run.genre == "cybersecurity" else "general"
                if request["reuse"]:
                    for metadata in latest_jobs(root):
                        source = metadata.parent / "production.json"
                        if source.is_file() and json.loads(source.read_text(encoding="utf-8")).get("pilot_art"):
                            run.cast_from = source
                            break
                    if not run.cast_from:
                        print("Create a pilot production first to reuse its character designs.")
                        continue
        try:
            phase("START", "Preparing production")
            before = player.latest(root)
            generate(run)
            after = player.latest(root)
            if after and after != before and sys.stdin.isatty() and player.after_export(after):
                return
            if run.random and not openai and prior is not None and (jobs := latest_jobs(root)):
                record = jobs[0].parent / "production.json"
                if record.is_file():
                    local = json.loads(record.read_text(encoding="utf-8"))
                    prior.update(last_local_story=local.get("local_story"), last_local_genre=local["spec"].get("genre"),
                                 duration=local["spec"].get("duration", prior["duration"]))
        except (ImportError, OSError, RuntimeError, ValueError, KeyError) as error:
            print(f"VideoAI: {error}")
            if run.random and openai:
                print("You can also type offline random to use the local story bank.")
