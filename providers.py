"""Remote generation adapters. Task IDs and downloads survive interrupted runs."""
import base64
import json
from pathlib import Path
import shutil
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class ProviderHTTPError(RuntimeError):
    def __init__(self, host, status, code=None):
        self.host = host
        self.status = status
        self.code = code
        guidance = {
            "insufficient_quota": "Check the API project's billing, available quota, and spending limit.",
            "invalid_api_key": "Run Cyber --api-setup to configure a valid project key.",
            "model_not_found": "Check the configured model and the project's model permissions.",
        }.get(code, "Check credentials, credits, inputs or rate limits.")
        super().__init__(f"{host} returned HTTP {status}. {guidance}")


class ProviderConnectionError(RuntimeError):
    def __init__(self, host, reason):
        self.host = host
        super().__init__(f"Could not reach {host}: {reason}")


def request_json(url, key, body=None, headers=None, *, timeout=100):
    request = Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"} | (headers or {}))
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        host = urlsplit(url).hostname
        code = None
        try:
            code = json.loads(error.read(8192)).get("error", {}).get("code")
        except (ValueError, AttributeError, OSError):
            pass
        raise ProviderHTTPError(host, error.code, code if isinstance(code, str) else None) from error
    except URLError as error:
        raise ProviderConnectionError(urlsplit(url).hostname, error.reason) from error
    except TimeoutError as error:
        raise ProviderConnectionError(urlsplit(url).hostname, "request timed out") from error


def save_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class VideoProvider(Protocol):
    def character(self, prompt: str, target: Path, ratio: str = "720:960") -> None: ...
    def clip(self, opening: str, action: str, seconds: int, ratio: str,
             references: dict[str, Path], target: Path, seed: int | None = None) -> None: ...


class Runway:
    BASE_URL = "https://api.dev.runwayml.com/v1"
    HEADERS = {"X-Runway-Version": "2024-11-06"}
    VIDEO_MODEL = "gen4.5"

    def __init__(self, key):
        self.key = key

    def task(self, endpoint, body, target):
        if target.exists():
            return
        record = target.with_suffix(target.suffix + ".task.json")
        if record.exists():
            task_id = json.loads(record.read_text(encoding="utf-8"))["id"]
        else:
            result = request_json(self.BASE_URL + endpoint, self.key, body, self.HEADERS)
            task_id = result["id"]
            save_json(record, {"id": task_id, "provider": "Runway", "endpoint": endpoint, "model": body["model"]})
        deadline = time.monotonic() + 1800
        failures = 0
        while time.monotonic() < deadline:
            try:
                result = request_json(f"{self.BASE_URL}/tasks/{task_id}", self.key, headers=self.HEADERS)
            except ProviderHTTPError as error:
                if error.status not in {429, 500, 502, 503, 504} or failures >= 4:
                    raise
                failures += 1
                time.sleep(min(30, 3 * 2 ** failures))
                continue
            failures = 0
            status = result["status"]
            if status == "SUCCEEDED":
                url = result["output"][0]
                if urlsplit(url).scheme != "https":
                    raise RuntimeError("Runway returned a non-HTTPS media URL.")
                temporary = target.with_suffix(".download")
                with urlopen(Request(url), timeout=120) as response, temporary.open("wb") as output:
                    shutil.copyfileobj(response, output)
                temporary.replace(target)
                return
            if status in {"FAILED", "CANCELED", "CANCELLED"}:
                raise RuntimeError(f"Runway task {task_id} {status.lower()} ({result.get('failureCode', 'unknown reason')}). "
                                   f"Revise the plan if necessary, then remove {record.name} before retrying this asset.")
            time.sleep(6)
        raise RuntimeError(f"Runway task {task_id} is still pending. Resume this job to continue polling.")

    def character(self, prompt, target, ratio="720:960"):
        self.task("/text_to_image", {"model": "gen4_image", "ratio": ratio,
                                    "promptText": bounded_prompt(prompt)}, target)

    def clip(self, opening, action, seconds, ratio, references, target, seed=None):
        if not 2 <= seconds <= 10 or ratio not in {"1280:720", "720:1280"}:
            raise ValueError("Runway Gen-4.5 clips need 2–10 seconds and a supported landscape or portrait ratio.")
        if target.exists():
            return
        body = {"model": self.VIDEO_MODEL, "ratio": ratio, "duration": seconds,
                "promptText": bounded_prompt(action)}
        if seed is not None:
            body["seed"] = seed
        if not references:
            body["promptText"] = bounded_prompt(opening + " " + action)
            self.task("/text_to_video", body, target)
            return
        frame = target.with_suffix(".jpg")
        tagged = [{"tag": tag, "uri": image_uri(path)} for tag, path in references.items()]
        self.task("/text_to_image", {"model": "gen4_image", "ratio": ratio,
                                    "promptText": bounded_prompt(opening), "referenceImages": tagged}, frame)
        body["promptImage"] = image_uri(frame)
        self.task("/image_to_video", body, target)


def bounded_prompt(text):
    return text.encode("utf-16-le")[:2000].decode("utf-16-le", errors="ignore").strip()


def image_uri(path):
    # Runway can return a different image format from the requested filename.
    from io import BytesIO
    from PIL import Image

    with Image.open(path) as image:
        image.thumbnail((1280, 1280))
        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
