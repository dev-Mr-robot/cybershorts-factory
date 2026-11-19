"""Launch from the application directory and provision local Python dependencies."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def codex_login():
    from chatgpt_planner import login_env

    codex = shutil.which("codex")
    if not codex:
        print("Codex CLI is unavailable. Cyber can still launch.", file=sys.stderr)
        print("https://developers.openai.com/codex/cli/", file=sys.stderr)
        return
    try:
        subprocess.run([codex, "login"], env=login_env(), check=False)
    except (OSError, KeyboardInterrupt):
        print("Codex sign-in did not finish. Cyber can still launch.", file=sys.stderr)


def needs_login(args):
    if not sys.stdin.isatty() or "--offline" in args or args not in ([], ["--studio"], ["--chatgpt"]):
        return False
    if os.getenv("OPENAI_API_KEY", "").strip() and "--chatgpt" not in args:
        return False
    if "--chatgpt" not in args:
        for name in ("config.local.json", "config.json"):
            try:
                config = json.loads((ROOT / name).read_text(encoding="utf-8-sig"))
                if str(config.get("openai_api_key") or "").strip():
                    return False
            except (OSError, ValueError, AttributeError):
                continue
    from chatgpt_planner import signed_in

    return not signed_in()


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
    explicit_login = "--login" in args
    if explicit_login:
        args.remove("--login")
    if explicit_login or needs_login(args):
        if not explicit_login:
            print("[LOGIN] Opening ChatGPT sign-in. You can cancel to continue with local stories.", flush=True)
        codex_login()
        if "--chatgpt" not in args:
            args.append("--chatgpt")
    informational = any(flag in args for flag in ("--help", "-h", "--list-styles", "--api-check", "--api-setup", "--api-open"))
    python = sys.executable if informational or "--no-install" in args else dependencies(args)
    if "--setup" in args or "--setup-all" in args:
        return 0
    args = [arg for arg in args if arg != "--no-install"]
    return subprocess.call([python, str(ROOT / "main.py"), *args], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
