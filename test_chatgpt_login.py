import os
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import unittest
from unittest.mock import patch

import chatgpt_planner as auth
from providers import ProviderConnectionError
from studio import select_video_backend


class LoginTests(unittest.TestCase):
    def test_delegated_login_persistence_expiry_and_logout(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "shadow-video-ai" / "codex"
            marker = state / "fixture-session"

            def codex(command, *, env, **kwargs):
                self.assertEqual(Path(env["CODEX_HOME"]), state)
                self.assertNotIn("OPENAI_API_KEY", env)
                self.assertNotIn("VIDEO_PROVIDER_API_KEY", env)
                if "status" in command:
                    return CompletedProcess(command, 0 if marker.exists() else 1,
                                            "Logged in using ChatGPT" if marker.exists() else "Not logged in", "")
                if "login" in command:
                    self.assertIn("--device-auth", command)
                    marker.write_text("active", encoding="utf-8")
                elif "logout" in command:
                    marker.unlink()
                elif marker.read_text(encoding="utf-8") == "expired":
                    return CompletedProcess(command, 1, "", "401 refresh token expired: private-value")
                else:
                    self.assertIn("features.shell_tool=false", command)
                    self.assertIn("read-only", command)
                    self.assertIn("Hindi", kwargs["input"])
                    Path(command[command.index("--output-last-message") + 1]).write_text('{"ok": true}')
                return CompletedProcess(command, 0, "", "")

            settings = {"LOCALAPPDATA": folder, "XDG_STATE_HOME": folder, "OPENAI_API_KEY": "example",
                        "VIDEO_PROVIDER_API_KEY": "example"}
            with (patch.dict(os.environ, settings), patch.object(auth.shutil, "which", return_value="codex"),
                  patch.object(auth.subprocess, "run", side_effect=codex)):
                self.assertFalse(auth.signed_in())
                self.assertTrue(auth.account("login", device=True))
                self.assertTrue(auth.signed_in())
                self.assertEqual(auth.request_story("Reply in Hindi", {}), {"ok": True})
                marker.write_text("expired", encoding="utf-8")
                with self.assertRaisesRegex(ProviderConnectionError, "session needs renewal") as failure:
                    auth.request_story("Reply in Hindi", {})
                self.assertNotIn("private-value", str(failure.exception))
                self.assertTrue(auth.account("logout"))
                self.assertFalse(auth.signed_in())

    def test_account_only_uses_pilot_without_requesting_provider_access(self):
        with patch("studio.check_video_provider") as check:
            self.assertEqual(select_video_backend("auto", ""), "pilot")
            check.assert_not_called()

    def test_unavailable_managed_video_falls_back_only_in_auto_mode(self):
        with patch("studio.check_video_provider", side_effect=ValueError("No credits")):
            self.assertEqual(select_video_backend("auto", "deployment"), "pilot")
            with self.assertRaisesRegex(ValueError, "No credits"):
                select_video_backend("runway", "deployment")
