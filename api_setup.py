"""Optional API setup. Keys stay in the environment or ignored local config."""
import getpass
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote

from providers import ProviderHTTPError, request_json
from library import phase


def active_key(config):
    return (os.getenv("OPENAI_API_KEY") or config.get("openai_api_key") or "").strip()


def check(config, candidate=None):
    key = active_key(config) if candidate is None else candidate
    if not key:
        phase("API", "No OpenAI key. Random genres and the demo can still run locally.")
        return False
    model = config.get("openai_model") or "gpt-4o-mini"
    try:
        request_json("https://api.openai.com/v1/models/" + quote(model, safe=""), key, timeout=20)
    except ProviderHTTPError as error:
        hints = {401: "The key was rejected. Create a fresh project key and run Cyber --api-setup.",
                 403: "The project key lacks permission to access this model.",
                 404: f"Model {model} is unavailable for this key. Set openai_model in config.local.json.",
                 429: "OpenAI is rate-limiting the check. Retry, and check project limits and billing."}
        phase("API", hints.get(error.status, str(error)))
        return False
    except (RuntimeError, OSError) as error:
        phase("API", str(error))
        return False
    phase("API", f"Key can access {model}. Generation still depends on available quota.")
    return True


def setup(root, config):
    if not sys.stdin.isatty():
        phase("API", "Use an interactive terminal, or export OPENAI_API_KEY and run Cyber --api-check.")
        return
    if os.getenv("OPENAI_API_KEY"):
        phase("API", "Your environment key takes precedence. Unset OPENAI_API_KEY before saving a different key.")
        check(config)
        return
    print("Create a project API key at https://platform.openai.com/api-keys")
    try:
        key = getpass.getpass("OpenAI API key (hidden, Enter to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not key or not check(config, key):
        return
    path = root / "config.local.json"
    settings = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    settings["openai_api_key"] = key
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as output:
        tmp = Path(output.name)
        try:
            json.dump(settings, output, ensure_ascii=False, indent=2)
        except BaseException:
            output.close()
            tmp.unlink(missing_ok=True)
            raise
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    config["openai_api_key"] = key
    phase("API", "Saved to the ignored local configuration.")
