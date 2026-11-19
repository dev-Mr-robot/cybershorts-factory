"""Optional API setup. Keys stay in the environment or ignored local config."""
import getpass
import json
import os
from pathlib import Path
import sys
import webbrowser

from providers import ProviderHTTPError, request_json
from library import phase
from chatgpt_planner import CHATGPT, signed_in, request_story


def active_key(config):
    return (os.getenv("OPENAI_API_KEY") or config.get("openai_api_key") or "").strip()


def planning_access(config):
    key = active_key(config)
    if config.get("prefer_chatgpt"):
        return CHATGPT if signed_in() else key
    return key or (CHATGPT if signed_in() else "")


KEYS_URL = "https://platform.openai.com/api-keys"
BILLING_URL = "https://platform.openai.com/settings/organization/billing/overview"


def open_key_page():
    print(KEYS_URL, flush=True)
    try:
        if not webbrowser.open(KEYS_URL):
            phase("API", "Open that link in your regular browser.")
    except (OSError, webbrowser.Error):
        phase("API", "Open that link in your regular browser.")


def check(config, candidate=None):
    key = planning_access(config) if candidate is None else candidate
    if key is CHATGPT:
        try:
            if request_story("Return a JSON object with ok set to true.", {}).get("ok") is not True:
                raise ValueError("Unexpected response.")
        except (RuntimeError, ValueError) as error:
            phase("API", f"ChatGPT planning check failed. {error}")
            return False
        phase("API", "ChatGPT planning via Codex works.")
        return True
    if not key:
        phase("API", "Run Cyber --login for ChatGPT, Cyber --api-setup for an API key, or Cyber --demo for a local video.")
        return False
    model = config.get("openai_model") or "gpt-4o-mini"
    try:
        result = request_json("https://api.openai.com/v1/chat/completions", key, {
            "model": model, "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": "Return a tiny JSON object with ok set to true."}],
            "max_completion_tokens": 32,
        }, timeout=25)
        reply = json.loads(result["choices"][0]["message"]["content"])
        if not isinstance(reply, dict) or reply.get("ok") is not True:
            raise ValueError("The model did not return the expected JSON response.")
    except ProviderHTTPError as error:
        if error.code == "insufficient_quota":
            phase("API", f"The key has insufficient API quota. Check billing and project limits: {BILLING_URL}")
            return False
        hints = {400: f"The configured model {model} rejected the JSON generation request. Check openai_model.",
                 401: "The key was rejected. Create a fresh project key and run Cyber --api-setup.",
                 403: "The project key lacks permission to generate with this model. Check permissions in the API dashboard.",
                 404: f"Model {model} is unavailable for this key. Set openai_model in config.local.json.",
                 429: "OpenAI is rate-limiting the check. Retry, and check project limits and billing."}
        phase("API", hints.get(error.status, str(error)))
        return False
    except (RuntimeError, OSError, ValueError, KeyError, IndexError, TypeError) as error:
        phase("API", f"The generation check could not finish. {error}")
        return False
    phase("API", f"OpenAI generation works with {model}.")
    return True


def setup(root, config):
    if not sys.stdin.isatty():
        phase("API", "Use an interactive terminal, or export OPENAI_API_KEY and run Cyber --api-check.")
        return
    if os.getenv("OPENAI_API_KEY"):
        phase("API", "Your environment key takes precedence. Unset OPENAI_API_KEY before saving a different key.")
        check(config)
        return
    print(f"Create a project API key at {KEYS_URL}. Run Cyber --api-open to open it in your browser.")
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
