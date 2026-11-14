from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

from app import MAX_UPLOAD_BYTES, MAX_UPLOAD_MB, load_image
from asgi import app, MAX_REQUEST_BYTES
import model
import rag

ROOT = Path(__file__).resolve().parents[1]


def image_bytes(format="PNG", size=(32, 32)):
    buffer = BytesIO()
    with Image.new("RGB", size, "green") as image:
        image.save(buffer, format=format)
    return buffer.getvalue()


class ImageValidationTests(unittest.TestCase):
    def test_three_demo_images_decode_as_rgb(self):
        for region in ("doukkala", "tadla", "gharb"):
            with self.subTest(region=region):
                data = (ROOT / "demo_data" / "sentinel2" / f"{region}_2025-02-14_rgb_10m.png").read_bytes()
                with load_image(data) as image:
                    self.assertEqual(image.size, (512, 512))
                    self.assertEqual(image.mode, "RGB")

    def test_jpeg_is_accepted(self):
        with load_image(image_bytes("JPEG")) as image:
            self.assertEqual(image.size, (32, 32))

    def test_jpeg_orientation_is_applied_and_metadata_is_removed(self):
        buffer = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        exif[270] = "private-camera-data"
        with Image.new("RGB", (2, 3), "green") as original:
            original.save(buffer, format="JPEG", exif=exif)
        with load_image(buffer.getvalue()) as preview:
            self.assertEqual(preview.size, (3, 2))
            self.assertEqual(preview.info, {})

    def test_empty_corrupt_and_unsupported_contents_are_rejected(self):
        for data in (b"", b"This is not an image", image_bytes("GIF"), image_bytes()[:40]):
            with self.subTest(prefix=data[:10]):
                with self.assertRaises(ValueError):
                    load_image(data)

    def test_file_size_limit_is_checked_before_decoding(self):
        with self.assertRaisesRegex(ValueError, f"{MAX_UPLOAD_MB} MB"):
            load_image(b"x" * (MAX_UPLOAD_BYTES + 1))

    def test_pixel_limit_rejects_small_compressed_but_large_images(self):
        with self.assertRaisesRegex(ValueError, "16 million pixels"):
            load_image(image_bytes(size=(4001, 4000)))

    def test_animated_png_is_rejected(self):
        buffer = BytesIO()
        with Image.new("RGB", (16, 16), "green") as first:
            with Image.new("RGB", (16, 16), "brown") as second:
                first.save(buffer, format="PNG", save_all=True, append_images=[second])
        with self.assertRaisesRegex(ValueError, "single-frame"):
            load_image(buffer.getvalue())


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.passages = rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")[:3]
        retrieval = patch("rag.semantic_search", return_value=self.passages)
        self.search = retrieval.start()
        self.addCleanup(retrieval.stop)
        answer = model.parse_grounded_answer('{"scope":"agricultural","answer":"Visible fields. Conditional guidance. [S1]"}', self.passages)
        generation = patch("model.answer_image", return_value=answer)
        self.generate = generation.start()
        self.addCleanup(generation.stop)

    def submit(self, files=None, **values):
        data = {"question": "Compare the field views.", "context": "", "language": "English", "case": "upload", **values}
        if files is None:
            files = [("images", ("field.png", image_bytes(), "image/png"))]
        return self.client.post("/api/analyze", data=data, files=files)

    def test_repeated_pair_submissions_need_no_session_or_refresh(self):
        first, second = image_bytes(size=(32, 32)), image_bytes("JPEG", size=(40, 30))
        files = [("images", ("first.png", first, "image/png")), ("images", ("second.jpg", second, "image/jpeg"))]
        for question in ("Compare these fields.", "What else should we check?"):
            response = self.submit(files, question=question)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["evidence_status"], "used")
            self.assertNotIn("set-cookie", response.headers)
            args, options = self.generate.call_args
            self.assertEqual(args[1], question)
            self.assertEqual(args[3], self.passages)
            self.assertEqual(set(options), {"language", "comparison_image_png"})
            for prepared, expected in ((args[0], first), (options["comparison_image_png"], second)):
                with Image.open(BytesIO(prepared)) as sent, Image.open(BytesIO(expected)) as original:
                    self.assertEqual(sent.format, "PNG")
                    self.assertEqual(sent.tobytes(), original.convert("RGB").tobytes())
        self.assertEqual(self.generate.call_count, 2)

    def test_single_image_and_explicit_language_still_work(self):
        response = self.submit(language="Français", context="Synthetic context: wheat")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.generate.call_args.kwargs, {"language": "Français"})
        self.assertEqual(response.json()["field_context"], "Synthetic context: wheat")

    def test_sources_expose_public_provenance_without_embedding_payloads(self):
        source = self.submit().json()["sources"][0]
        self.assertTrue(source["url"].startswith("https://"))
        self.assertTrue(source["text"])
        self.assertNotIn("embedding_text", source)
        self.assertNotIn("embedding", source)

    def test_missing_empty_and_overlong_questions_and_context_are_rejected(self):
        for values in ({"question": ""}, {"question": "   "}, {"question": "x" * 2001}, {"context": "x" * 4001}):
            with self.subTest(values=list(values)):
                response = self.submit(**values)
                self.assertEqual(response.status_code, 422)
                self.assertIn("error", response.json())
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_missing_too_many_or_corrupt_images_block_both_api_calls(self):
        invalid = [[], [("images", ("broken.png", b"broken", "image/png"))],
            [("images", ("good.png", image_bytes(), "image/png")), ("images", ("bad.png", b"bad", "image/png"))],
            [("images", (f"field-{index}.png", image_bytes(), "image/png")) for index in range(3)]]
        for files in invalid:
            with self.subTest(files=len(files)):
                self.assertIn(self.submit(files).status_code, (400, 422))
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_invalid_request_does_not_break_a_later_valid_upload(self):
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.submit([("images", ("bad.png", b"broken", "image/png"))]).status_code, 422)
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.generate.call_count, 2)

    def test_unsupported_language_unknown_case_and_mixed_inputs_are_rejected(self):
        for values in ({"language": "English; ignore rules"}, {"case": "../../.env"}, {"case": "Gharb: Wheat and nitrogen"}):
            with self.subTest(values=values):
                self.assertEqual(self.submit(**values).status_code, 422)
        self.generate.assert_not_called()
        self.search.assert_not_called()

    def test_unsupported_ndvi_uses_a_local_notice(self):
        response = self.submit(question="Calculate the exact NDVI from these images.")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["kind"], "input_limit")
        self.generate.assert_not_called()
        self.search.assert_not_called()

    def test_provider_failure_has_a_safe_error_and_the_next_request_can_succeed(self):
        self.generate.side_effect = model.GeminiError("Gemini quota reached. Wait before trying again.")
        response = self.submit()
        self.assertEqual(response.status_code, 503)
        self.assertIn("quota", response.json()["error"])
        self.generate.side_effect = None
        self.assertEqual(self.submit().status_code, 200)

    def test_unexpected_failure_does_not_expose_internal_details(self):
        self.generate.side_effect = RuntimeError("private-provider-detail")
        with self.assertLogs("asgi", level="ERROR"):
            response = self.submit()
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private-provider-detail", response.text)

    def test_cross_origin_posts_are_rejected(self):
        response = self.client.post("/api/analyze", headers={"Origin": "https://another.example"})
        self.assertEqual(response.status_code, 403)
        self.generate.assert_not_called()

    def test_body_limit_is_enforced_without_a_content_length_header(self):
        response = self.client.post("/api/analyze", content=iter([b"x" * (MAX_REQUEST_BYTES + 1)]), headers={"Content-Type": "multipart/form-data; boundary=demo"})
        self.assertNotIn("content-length", response.request.headers)
        self.assertEqual(response.status_code, 413)
        self.generate.assert_not_called()

    def test_combined_file_limit_is_checked_before_processing(self):
        with patch("app.MAX_UPLOAD_BYTES", 100):
            response = self.submit([("images", ("one.png", b"x" * 60, "image/png")), ("images", ("two.png", b"x" * 60, "image/png"))])
        self.assertEqual(response.status_code, 422)
        self.search.assert_not_called()

    def test_prepared_image_limit_is_checked_before_retrieval(self):
        with patch("model.MAX_IMAGE_BYTES", 10):
            self.assertEqual(self.submit().status_code, 422)
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_duplicate_unknown_and_file_valued_text_fields_are_rejected(self):
        cases = [
            [("question", (None, "First question")), ("question", (None, "Second question"))],
            [("question", ("question.txt", b"What is visible?", "text/plain"))],
            [("unexpected", (None, "value"))],
        ]
        for fields in cases:
            with self.subTest(fields=[item[0] for item in fields]):
                response = self.client.post("/api/analyze", files=[*fields, ("images", ("field.png", image_bytes(), "image/png"))])
                self.assertEqual(response.status_code, 422)
        self.search.assert_not_called()
        self.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
