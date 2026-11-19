"""Cloud configuration and the Responses API screenplay transport."""
import json
import os

from providers import request_json


def load_env(path):
    if not path.is_file():
        return
    allowed = {"OPENAI_API_KEY", "VIDEO_PROVIDER_API_KEY", "RUNWAYML_API_SECRET"}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.removeprefix("export ").partition("=")
        name, value = name.strip(), value.strip()
        if sep and name in allowed and name not in os.environ:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ[name] = value


def video_key(config):
    return (os.getenv("VIDEO_PROVIDER_API_KEY") or os.getenv("RUNWAYML_API_SECRET") or config.get("runway_api_key") or "").strip()


def respond(key, model, instructions, payload, timeout=100):
    result = request_json("https://api.openai.com/v1/responses", key, {
        "model": model, "instructions": instructions + " Return exactly one JSON object.",
        "input": json.dumps(payload, ensure_ascii=False),
        "text": {"format": {"type": "json_object"}}, "store": False,
    }, timeout=timeout)
    text = "".join(part.get("text", "") for item in result.get("output", [])
                   if item.get("type") == "message" for part in item.get("content", [])
                   if part.get("type") == "output_text")
    if not text or result.get("status") == "incomplete":
        raise ValueError("OpenAI returned no complete screenplay response.")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("OpenAI returned a response other than a JSON object.")
    return data
