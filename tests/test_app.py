from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

from app import MAX_UPLOAD_BYTES, load_image
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
        with self.assertRaisesRegex(ValueError, "10 MB"):
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


class UploadFormTests(unittest.TestCase):
    def setUp(self):
        self.passages = rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")[:3]
        retrieval_patch = patch("rag.semantic_search", return_value=self.passages)
        self.retrieval_mock = retrieval_patch.start()
        self.addCleanup(retrieval_patch.stop)
        answer = model.parse_grounded_answer('{"scope":"agricultural","answer":"Visible rectangular fields in the center. Conditional document guidance. [S1]"}', self.passages)
        answer_patch = patch("model.answer_image", return_value=answer)
        self.answer_mock = answer_patch.start()
        self.addCleanup(answer_patch.stop)

    def upload_app(self):
        app = AppTest.from_file(str(ROOT / "app.py")).run()
        app.selectbox(key="image_source").select("Upload my own image").run()
        return app

    def test_empty_submit_shows_image_and_question_errors(self):
        app = self.upload_app()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 2)
        self.assertFalse(app.success)
        self.answer_mock.assert_not_called()
        self.retrieval_mock.assert_not_called()

    def test_whitespace_question_is_rejected_and_context_retained(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("   ")
        app.text_area(key="context").input("Reported wheat in Doukkala")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("question", app.error[0].value.lower())
        self.assertEqual(app.text_area(key="context").value, "Reported wheat in Doukkala")
        self.assertFalse(app.success)
        self.answer_mock.assert_not_called()

    def test_valid_submit_preserves_inputs_and_does_not_repeat_success_on_rerun(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("Why are some field patches lighter?")
        app.text_area(key="context").input("Crop reported by user: wheat")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertIn("ready", app.success[0].value.lower())
        self.assertEqual(app.text_area(key="question").value, "Why are some field patches lighter?")
        self.assertEqual(app.text_area(key="context").value, "Crop reported by user: wheat")
        app.run()
        self.assertFalse(app.success)
        self.assertEqual(self.answer_mock.call_count, 1)
        self.retrieval_mock.assert_called_once_with("Why are some field patches lighter?", "Crop reported by user: wheat")
        self.assertIn("Visible rectangular fields", " ".join(item.value for item in app.markdown))
        image_data, question, context, passages = self.answer_mock.call_args.args
        with Image.open(BytesIO(image_data)) as image:
            self.assertEqual(image.format, "PNG")
        self.assertEqual(question, "Why are some field patches lighter?")
        self.assertEqual(context, "Crop reported by user: wheat")
        self.assertIn("Crop reported by user: wheat", [item.value for item in app.text])
        self.assertEqual(passages, self.passages)
        self.assertEqual(self.answer_mock.call_args.kwargs, {"language": "English"})
        self.assertEqual(len(app.expander), 1)
        self.assertIn("PDF p. 14", app.expander[0].label)
        self.assertIn(self.passages[0]["source_url"] + "#page=14", " ".join(item.value for item in app.markdown))

    def test_three_demo_images_preview_in_the_form(self):
        app = self.upload_app()
        for region in ("doukkala", "tadla", "gharb"):
            with self.subTest(region=region):
                path = ROOT / "demo_data" / "sentinel2" / f"{region}_2025-02-14_rgb_10m.png"
                app.file_uploader[0].set_value((path.name, path.read_bytes(), "image/png")).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(app.image[0].captions, ["512 × 512 pixels · RGB preview"])

    def test_misleading_png_filename_cannot_bypass_content_validation(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", b"Not an image", "image/png")).run()
        app.text_area(key="question").input("What is visible?")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("could not be read", app.error[0].value)
        self.assertFalse(app.image)
        self.assertFalse(app.success)
        self.answer_mock.assert_not_called()

    def test_changed_question_and_context_reach_the_next_request(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("Describe the visible fields.")
        app.button[0].click().run()
        app.text_area(key="question").input("What should I check in the lighter patches?")
        app.text_area(key="context").input("Synthetic context: wheat, early growth stage")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.answer_mock.call_count, 2)
        self.assertEqual(self.answer_mock.call_args.args[1:], (
            "What should I check in the lighter patches?",
            "Synthetic context: wheat, early growth stage",
            self.passages,
        ))

    def test_new_upload_clears_the_old_answer_without_calling_gemini(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("What is visible?")
        app.button[0].click().run()
        app.file_uploader[0].set_value(("new-field.png", image_bytes(size=(40, 40)), "image/png")).run()
        self.assertFalse(app.exception)
        self.assertEqual(self.answer_mock.call_count, 1)
        self.assertNotIn("Visible rectangular fields", " ".join(item.value for item in app.markdown))
        self.assertFalse(app.expander)

    def test_api_failure_preserves_inputs_and_clears_the_old_answer(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("What is visible?")
        app.text_area(key="context").input("Synthetic context: wheat")
        app.button[0].click().run()
        self.answer_mock.side_effect = model.GeminiError("Gemini quota reached. Wait before trying again.")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("quota", app.error[0].value)
        self.assertFalse(app.success)
        self.assertEqual(app.text_area(key="question").value, "What is visible?")
        self.assertEqual(app.text_area(key="context").value, "Synthetic context: wheat")
        self.assertNotIn("Visible rectangular fields", " ".join(item.value for item in app.markdown))
        self.assertFalse(app.expander)

    def test_retrieval_failure_preserves_inputs_without_another_vision_call(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("What should I check?")
        app.button[0].click().run()
        self.retrieval_mock.side_effect = model.GeminiError("Embedding quota reached. Try again later.")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertIn("quota", app.error[0].value)
        self.assertFalse(app.success)
        self.assertFalse(app.expander)
        self.assertEqual(self.answer_mock.call_count, 1)
        self.assertEqual(app.text_area(key="question").value, "What should I check?")

    def test_missing_or_unrelated_evidence_has_a_notice_and_no_source_panel(self):
        for status in ("insufficient", "out_of_scope"):
            with self.subTest(status=status):
                self.answer_mock.return_value = {"text": "No relevant reference evidence for this question.", "evidence_status": status, "sources": []}
                app = self.upload_app()
                app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
                app.text_area(key="question").input("What does the evidence support?")
                app.button[0].click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.expander)
                self.assertTrue(app.info)
                self.assertIn("No relevant reference", " ".join(item.value for item in app.markdown))

    def test_prompt_version_change_clears_the_cached_answer_and_sources(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("What is visible?")
        app.button[0].click().run()
        with patch("model.PROMPT_VERSION", "changed-prompt-version"):
            app.run()
        self.assertFalse(app.exception)
        self.assertFalse(app.expander)
        self.assertNotIn("Visible rectangular fields", " ".join(item.value for item in app.markdown))
        self.assertEqual(self.answer_mock.call_count, 1)

    def test_language_choice_clears_old_sources_and_reaches_the_next_request(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("Quelle analyse vérifier ?")
        app.button[0].click().run()
        app.radio(key="language").set_value("Français").run()
        self.assertFalse(app.expander)
        self.assertEqual(self.answer_mock.call_count, 1)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.answer_mock.call_args.kwargs, {"language": "Français"})

    def test_unsupported_calculation_is_a_notice_without_search_or_vision(self):
        app = self.upload_app()
        app.file_uploader[0].set_value(("field.png", image_bytes(), "image/png")).run()
        app.text_area(key="question").input("Calculate the exact NDVI from this RGB image.")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.success)
        self.assertFalse(app.expander)
        self.assertIn("Input limitation", [header.value for header in app.header])
        self.assertIn("No index was computed", " ".join(item.value for item in app.markdown))
        self.retrieval_mock.assert_not_called()
        self.answer_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
