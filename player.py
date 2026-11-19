"""Playback hand-off from Cyber to mpv's native on-screen controls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def display_available():
    return not sys.platform.startswith("linux") or bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))


def backend():
    return ("mpv", shutil.which("mpv")) if shutil.which("mpv") else ("ffplay", shutil.which("ffplay"))


def latest(root):
    records = sorted((root / "videos").glob("**/metadata.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for record in records:
        try:
            title = json.loads(record.read_text(encoding="utf-8"))
            name = title["file"]
            video = record.parent / name
            if Path(name).name == name and video.is_file():
                return video
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def play(video, subtitles=None):
    if not video or not video.is_file():
        print("[PLAYER] Video file not found. Use history to find its path.")
        return False
    if subtitles and not subtitles.is_file():
        print("[PLAYER] That SRT file does not exist.")
        return False
    if not display_available():
        print("[PLAYER] Open a graphical Kali session to watch the video. For audio-only terminal playback: mpv --vo=null <video.mp4>.")
        return False
    name, program = backend()
    if not program:
        print("[PLAYER] Install mpv with sudo apt install mpv, or run sh install_kali.sh.")
        return False
    if name == "mpv":
        args = [program, "--no-config", "--hwdec=no", "--osc=yes", "--keep-open=yes",
                "--autofit=90%x90%", "--sub-auto=no"]
        if subtitles:
            args.append(f"--sub-file={subtitles.resolve()}")
        args += ["--", str(video.resolve())]
        print("[PLAYER] Space pause · arrows seek · 9/0 volume · f fullscreen · q stop")
    else:
        args = [program, "-autoexit", str(video.resolve())]
        if subtitles:
            print("[PLAYER] External SRT selection needs mpv. The generated video's burned-in captions remain visible.")
    try:
        result = subprocess.run(args, check=False)
        if result.returncode:
            print(f"[PLAYER] {name} exited with code {result.returncode}. Check your display and audio, or run Cyber --player-check.")
            return False
        return True
    except (OSError, KeyboardInterrupt) as error:
        print(f"[PLAYER] Playback ended: {error}")
        return False


def open_location(video):
    if not display_available():
        print(video.parent)
        return
    try:
        if os.name == "nt":
            os.startfile(str(video.parent))
        else:
            command = shutil.which("open" if sys.platform == "darwin" else "xdg-open")
            if command:
                subprocess.run([command, str(video.parent)], check=False)
            else:
                print(video.parent)
    except OSError as error:
        print(f"[PLAYER] {error}")


def check():
    print(f"[PLAYER] Python {sys.version.split()[0]}")
    for name in ("ffmpeg", "ffprobe", "mpv", "ffplay"):
        resolved = shutil.which(name)
        if not resolved and name == "ffmpeg":
            try:
                from imageio_ffmpeg import get_ffmpeg_exe
                resolved = f"{get_ffmpeg_exe()} (bundled)"
            except (ImportError, RuntimeError):
                pass
        print(f"  {name}: {resolved or 'not on PATH'}")
    print(f"  Graphical session: {'available' if display_available() else 'not detected'}")
    _, program = backend()
    if program and Path(program).stem == "mpv":
        for flag, label in (("--vd=help", "H.264 decoder"), ("--ao=help", "Audio outputs")):
            try:
                result = subprocess.run([program, "--no-config", flag], capture_output=True, timeout=10,
                                        encoding="utf-8", errors="replace", check=False)
                details = (result.stdout + result.stderr).casefold()
                found = "h264" in details if flag == "--vd=help" else any(x in details for x in ("pulse", "pipewire", "alsa", "wasapi", "coreaudio"))
                print(f"  {label}: {'reported by mpv' if found else 'not confirmed'}")
            except (OSError, subprocess.SubprocessError) as error:
                print(f"  {label}: {error}")
    if not program:
        print("  Install on Kali: sudo apt install ffmpeg mpv")
    print("  Play a file to verify the actual display and sound device.")


def after_export(video):
    while True:
        try:
            command = input("1 Play · 2 Open folder · 3 Another video · 4 Main prompt · 5 Exit: ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            return True
        if command in {"1", "play"}:
            play(video)
        elif command in {"2", "open"}:
            open_location(video)
        elif command in {"5", "exit", "quit"}:
            return True
        elif command in {"3", "4", "another", "menu", ""}:
            return False
        else:
            print("Choose play, open, another, menu, or exit.")
