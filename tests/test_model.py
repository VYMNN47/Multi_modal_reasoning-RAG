import base64
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from google import genai
import httpx2

import model


REAL_CLIENT = genai.Client


class CredentialTests(unittest.TestCase):
    def test_project_dotenv_is_loaded_without_overriding_environment(self):
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("GEMINI_API_KEY=local-test-key\n")
            with patch("model.ENV_FILE", env_file), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(model.get_api_key(), "local-test-key")
            with patch("model.ENV_FILE", env_file), patch.dict(os.environ, {"GEMINI_API_KEY": "environment-test-key"}):
                self.assertEqual(model.get_api_key(), "environment-test-key")

    def test_missing_key_prevents_a_request(self):
        with patch("model.load_dotenv"), patch.dict(os.environ, {"GEMINI_API_KEY": "  "}):
            with patch("model.genai.Client") as client:
                with self.assertRaisesRegex(model.GeminiError, "GEMINI_API_KEY"):
                    model.answer_image(b"validated-image", "What is visible?")
                client.assert_not_called()


class GeminiRequestTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.failure = None
        self.payload = {
            "candidates": [{
                "content": {"role": "model", "parts": [{"text": "Visible rectangular fields."}]},
                "finishReason": "STOP",
            }]
        }
        key_patch = patch("model.get_api_key", return_value="test-key")
        key_patch.start()
        self.addCleanup(key_patch.stop)
        client_patch = patch("model.genai.Client", side_effect=self.make_client)
        client_patch.start()
        self.addCleanup(client_patch.stop)

    def make_client(self, **options):
        options["http_options"] = options["http_options"].model_copy(update={
            "client_args": {"transport": httpx2.MockTransport(self.handle_request), "trust_env": False},
        })
        return REAL_CLIENT(**options)

    def handle_request(self, request):
        self.requests.append(request)
        if self.failure:
            raise self.failure("sensitive-provider-detail", request=request)
        return httpx2.Response(self.status, json=self.payload)

    def test_image_question_context_and_system_instructions_reach_the_api(self):
        answer = model.answer_image(b"validated-png", " Pourquoi ces zones ? ", " Blé déclaré par l'utilisateur ")
        self.assertEqual(answer, "Visible rectangular fields.")
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(request.url.host, "generativelanguage.googleapis.com")
        self.assertTrue(request.url.path.endswith(f"/{model.MODEL_NAME}:generateContent"))
        self.assertEqual(request.headers["x-goog-api-key"], "test-key")
        self.assertNotIn("test-key", str(request.url))
        body = json.loads(request.content)
        image_part, text_part = body["contents"][0]["parts"]
        self.assertEqual(image_part["inlineData"]["mime_type"], "image/png")
        self.assertEqual(base64.b64decode(image_part["inlineData"]["data"]), b"validated-png")
        user_text = json.loads(text_part["text"])
        self.assertEqual(user_text["question"], "Pourquoi ces zones ?")
        self.assertEqual(user_text["field_context"], "Blé déclaré par l'utilisateur")
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], model.SYSTEM_PROMPT)
        self.assertNotIn("test-key", request.content.decode())

    def test_provider_errors_are_actionable_and_do_not_leak_details_or_retry(self):
        for code, hint in ((400, "rejected"), (401, "key"), (403, "key"), (404, "model"), (429, "quota"), (503, "unavailable")):
            with self.subTest(code=code):
                self.status = code
                self.payload = {"error": {"code": code, "message": "sensitive-provider-detail"}}
                before = len(self.requests)
                with self.assertRaises(model.GeminiError) as caught:
                    model.answer_image(b"validated-png", "What is visible?")
                self.assertIn(hint, str(caught.exception).lower())
                self.assertNotIn("sensitive-provider-detail", str(caught.exception))
                self.assertEqual(len(self.requests) - before, 1)

    def test_timeout_and_connection_errors_are_safe(self):
        for failure, hint in ((httpx2.ReadTimeout, "timed out"), (httpx2.ConnectError, "connect")):
            with self.subTest(failure=failure):
                self.failure = failure
                with self.assertRaises(model.GeminiError) as caught:
                    model.answer_image(b"validated-png", "What is visible?")
                self.assertIn(hint, str(caught.exception))
                self.assertNotIn("sensitive-provider-detail", str(caught.exception))

    def test_blocked_empty_and_truncated_responses_are_not_success(self):
        responses = [
            {"promptFeedback": {"blockReason": "SAFETY"}},
            {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "Partial answer"}]}}]},
            {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "  "}]}}]},
        ]
        for response in responses:
            with self.subTest(response=response):
                self.payload = response
                with self.assertRaises(model.GeminiError):
                    model.answer_image(b"validated-png", "What is visible?")

    def test_only_public_answer_parts_are_returned(self):
        self.payload["candidates"][0]["content"]["parts"] = [
            {"text": "private test content", "thought": True},
            {"text": "Visible fields."},
        ]
        self.assertEqual(model.answer_image(b"validated-png", "What is visible?"), "Visible fields.")

    def test_prepared_image_size_is_checked_before_sending(self):
        for data in (b"", b"x" * (10 * 1024 * 1024 + 1)):
            with self.subTest(size=len(data)):
                with self.assertRaisesRegex(model.GeminiError, "smaller crop"):
                    model.answer_image(data, "What is visible?")
        self.assertFalse(self.requests)


if __name__ == "__main__":
    unittest.main()
