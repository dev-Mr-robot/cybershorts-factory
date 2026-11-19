"""Optional API setup. Keys stay in the environment or ignored local config."""
import os

from providers import ProviderHTTPError
from library import phase
from cloud import respond
from chatgpt_planner import CHATGPT, HELP, request_story, signed_in


def active_key(config):
    return (os.getenv("OPENAI_API_KEY") or config.get("openai_api_key") or "").strip()


BILLING_URL = "https://platform.openai.com/settings/organization/billing/overview"


def planning_access(config):
    return CHATGPT if signed_in() else active_key(config)


def check(config):
    key = planning_access(config)
    if not key:
        phase("API", HELP)
        return False
    model = config.get("openai_model") or "gpt-4o-mini"
    try:
        prompt = "Reply with a tiny JSON object with ok set to true."
        reply = request_story(prompt, {}) if key is CHATGPT else respond(key, model, prompt, {}, timeout=25)
        if not isinstance(reply, dict) or reply.get("ok") is not True:
            raise ValueError("The model did not return the expected JSON response.")
    except ProviderHTTPError as error:
        if error.code == "insufficient_quota":
            phase("API", f"The key has insufficient API quota. Check billing and project limits: {BILLING_URL}")
            return False
        hints = {400: f"The configured model {model} rejected the JSON generation request. Check openai_model.",
                 401: "The key was rejected. Ask the deployment administrator to check its credential.",
                 403: "The project key lacks permission to generate with this model. Check permissions in the API dashboard.",
                 404: f"Model {model} is unavailable for this key. Set openai_model in config.local.json.",
                 429: "OpenAI is rate-limiting the check. Retry, and check project limits and billing."}
        phase("API", hints.get(error.status, str(error)))
        return False
    except (RuntimeError, OSError, ValueError, KeyError, IndexError, TypeError) as error:
        phase("API", f"The generation check could not finish. {error}")
        return False
    phase("API", "ChatGPT screenplay generation verified." if key is CHATGPT else f"Managed OpenAI generation verified with {model}.")
    return True
