"""Launch from the application directory and provision local Python dependencies."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def dependencies(args):
    full = "--local-animation" in args or "--setup-all" in args
    modules = ["edge_tts", "PIL"]
    if not shutil.which("ffmpeg"):
        modules.append("imageio_ffmpeg")
    if full:
        modules += ["moderngl", "numpy"]
    if all(importlib.util.find_spec(name) for name in modules):
        return sys.executable
    venv = ROOT / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    requirement = ROOT / ("requirements.txt" if full else "requirements-core.txt")
    versions = hashlib.sha256(requirement.read_bytes() + (ROOT / "requirements-core.txt").read_bytes()).hexdigest()
    marker = venv / (".cyber-all" if full else ".cyber-core")
    try:
        if not python.is_file():
            print("[SETUP] Creating the project environment", flush=True)
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, timeout=120)
        if not marker.is_file() or marker.read_text(encoding="ascii") != versions:
            print("[SETUP] Installing the video dependencies", flush=True)
            subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                            "--retries", "1", "--timeout", "12", "-r", str(requirement)], check=True, timeout=240)
            marker.write_text(versions, encoding="ascii")
        return str(python)
    except (OSError, subprocess.SubprocessError):
        print("[SETUP] Dependencies could not be installed. The CLI can still open. Retry Cyber --setup when ready.", file=sys.stderr)
        return str(python) if python.is_file() else sys.executable


def main():
    args = sys.argv[1:]
    if sys.version_info < (3, 11):
        print("Cyber requires Python 3.11 or newer.", file=sys.stderr)
        return 2
    if "--login" in args:
        args[args.index("--login")] = "--api-open"
    informational = any(flag in args for flag in ("--help", "-h", "--list-styles", "--api-check", "--api-setup", "--api-open", "--online-check", "--player-check", "--play"))
    environment = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if informational or "--no-install" in args:
        python = str(environment) if environment.is_file() else sys.executable
    else:
        python = dependencies(args)
    if "--setup" in args or "--setup-all" in args:
        return 0
    args = [arg for arg in args if arg != "--no-install"]
    return subprocess.call([python, str(ROOT / "main.py"), *args], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
