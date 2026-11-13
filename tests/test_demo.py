from io import BytesIO
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

import app as application
import model
import rag


ROOT = Path(__file__).resolve().parents[1]
COMPARISON_LABEL = "Casablanca: Drought, 2023–2024"


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.passages = rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")[:3]
        retrieval = patch("rag.semantic_search", return_value=self.passages)
        self.search = retrieval.start()
        self.addCleanup(retrieval.stop)
        generation = patch("model.answer_image", return_value={
            "text": "Conditional field checks.", "evidence_status": "insufficient", "sources": [],
        })
        self.generate = generation.start()
        self.addCleanup(generation.stop)

    def test_default_example_is_ready_without_an_upload_or_api_call(self):
        page = AppTest.from_file(str(ROOT / "app.py")).run()
        self.assertFalse(page.exception)
        self.assertTrue(page.selectbox(key="image_source").value)
        self.assertTrue(page.image)
        self.assertTrue(page.text_area(key="question").value)
        self.assertIn("Synthetic", page.text_area(key="context").value)
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_each_example_loads_the_matching_image_question_and_context(self):
        page = AppTest.from_file(str(ROOT / "app.py")).run()
        for label, example in application.EXAMPLES.items():
            if "images" in example:
                continue
            with self.subTest(label=label):
                page.selectbox(key="image_source").select(label).run()
                self.assertEqual(page.text_area(key="question").value, example["question"])
                self.assertEqual(page.text_area(key="context").value, example["context"])
                self.assertFalse(page.success)
                page.button[0].click().run()
                self.assertFalse(page.exception)
                self.assertFalse(page.error)
                self.assertEqual(self.generate.call_args.args[1:3], (example["question"], example["context"]))
                with Image.open(BytesIO(self.generate.call_args.args[0])) as sent:
                    with Image.open(ROOT / "demo_data/sentinel2" / example["image"]) as original:
                        self.assertEqual(sent.tobytes(), original.convert("RGB").tobytes())

    def comparison_page(self):
        page = AppTest.from_file(str(ROOT / "app.py")).run()
        return page.selectbox(key="image_source").select(COMPARISON_LABEL).run()

    def test_comparison_sends_both_original_rgb_views_with_dates_and_pinned_nasa_reference(self):
        case = application.COMPARISON
        page = self.comparison_page()
        self.assertFalse(page.exception)
        self.assertEqual(len(page.image), 2)
        self.assertEqual(page.text_area(key="question").value, case["question"])
        self.assertEqual(page.text_area(key="context").value, case["context"])
        for preview, item in zip(page.image, case["images"]):
            self.assertEqual(preview.captions, [f"{item['date']} · {item['platform']} / {item['instrument']}"])
        captions = " ".join(item.value for item in page.caption)
        self.assertIn(case["attribution"], captions)
        self.assertNotIn("Copernicus", captions)
        self.assertNotIn("Sentinel-2", captions)
        page.radio(key="language").set_value("Français").run()
        page.button[0].click().run()
        self.assertFalse(page.exception)
        self.assertFalse(page.error)
        self.search.assert_called_once_with(case["question"], case["context"], top_k=2)
        first_png, question, context, references = self.generate.call_args.args
        self.assertEqual((question, context), (case["question"], case["context"]))
        self.assertEqual(references, [case["reference"], *self.passages[:2]])
        self.assertEqual(len(references), 3)
        options = self.generate.call_args.kwargs
        self.assertEqual(options["language"], "Français")
        self.assertEqual(options["image_dates"], ("2023-02-12", "2024-02-19"))
        second_png = options["comparison_image_png"]
        self.assertNotEqual(first_png, second_png)
        for prepared, item in zip((first_png, second_png), case["images"]):
            with Image.open(BytesIO(prepared)) as sent:
                with Image.open(ROOT / "demo_data/comparison" / item["file"]) as original:
                    self.assertEqual(sent.format, "PNG")
                    self.assertEqual(sent.size, original.size)
                    self.assertEqual(sent.tobytes(), original.convert("RGB").tobytes())

    def test_changed_comparison_metadata_or_reference_clears_the_old_assessment(self):
        case_path = ROOT / "demo_data/comparison/case.json"
        read_text = Path.read_text
        for change in ("title", "reference_source"):
            with self.subTest(change=change):
                self.generate.reset_mock()
                self.search.reset_mock()
                page = self.comparison_page()
                page.button[0].click().run()
                self.assertIn("Conditional field checks.", [item.value for item in page.markdown])
                changed = json.loads(json.dumps(application.COMPARISON))
                if change == "title":
                    changed["title"] += " (updated metadata)"
                else:
                    changed["reference"]["source_url"] += "?revision=2"

                def read_case(path, *args, **kwargs):
                    return json.dumps(changed) if path == case_path else read_text(path, *args, **kwargs)

                with patch.object(Path, "read_text", read_case):
                    page.run()
                self.assertFalse(page.exception)
                self.assertNotIn("Conditional field checks.", [item.value for item in page.markdown])
                self.search.assert_called_once()
                self.generate.assert_called_once()

    def test_changed_pixels_in_either_comparison_image_clear_the_old_assessment(self):
        read_bytes = Path.read_bytes
        for item in application.COMPARISON["images"]:
            with self.subTest(image=item["file"]):
                self.generate.reset_mock()
                self.search.reset_mock()
                page = self.comparison_page()
                page.button[0].click().run()
                target = ROOT / "demo_data/comparison" / item["file"]
                with Image.open(target) as original:
                    changed = original.convert("RGB")
                pixel = changed.getpixel((0, 0))
                changed.putpixel((0, 0), ((pixel[0] + 1) % 256, pixel[1], pixel[2]))
                buffer = BytesIO()
                changed.save(buffer, format="PNG")
                changed.close()

                def read_image(path):
                    return buffer.getvalue() if path == target else read_bytes(path)

                with patch.object(Path, "read_bytes", read_image):
                    page.run()
                self.assertFalse(page.exception)
                self.assertNotIn("Conditional field checks.", [item.value for item in page.markdown])
                self.search.assert_called_once()
                self.generate.assert_called_once()

    def test_missing_or_corrupt_comparison_image_prevents_both_api_calls(self):
        read_bytes = Path.read_bytes
        for item, missing in zip(application.COMPARISON["images"], (True, False)):
            with self.subTest(image=item["file"]):
                target = ROOT / "demo_data/comparison" / item["file"]

                def read_image(path):
                    if path == target:
                        if missing:
                            raise OSError("missing test image")
                        return b"not an image"
                    return read_bytes(path)

                with patch.object(Path, "read_bytes", read_image):
                    page = self.comparison_page()
                    self.assertIn("The comparison could not be loaded", " ".join(item.value for item in page.error))
                    page.button[0].click().run()
                self.assertFalse(page.exception)
                self.assertTrue(page.error)
                self.assertFalse(page.success)
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_cited_nasa_web_report_shows_its_publication_date_without_a_pdf_page(self):
        reference = application.COMPARISON["reference"]
        self.generate.return_value = {
            "text": "NASA describes regional drought conditions.", "evidence_status": "used",
            "sources": [{**reference, "citation": f"[{reference['source_id']}, {reference['publication_date']}]", "url": reference["source_url"]}],
        }
        page = self.comparison_page()
        page.button[0].click().run()
        self.assertFalse(page.exception)
        self.assertFalse(page.error)
        self.assertEqual(len(page.expander), 2)
        self.assertIn(reference["source_id"], page.expander[1].label)
        captions = " ".join(item.value for item in page.caption)
        self.assertIn("Published: 2024-02-22", captions)
        self.assertNotIn("Physical PDF page", captions)
        markup = " ".join(item.value for item in page.markdown)
        self.assertIn(f"[Open original report]({reference['source_url']})", markup)
        self.assertNotIn("#page=", markup)

    def test_upload_mode_clears_the_example_and_old_assessment(self):
        page = AppTest.from_file(str(ROOT / "app.py")).run()
        page.button[0].click().run()
        page.selectbox(key="image_source").select("Upload my own image").run()
        self.assertFalse(page.image)
        self.assertEqual(page.text_area(key="question").value, "")
        self.assertEqual(page.text_area(key="context").value, "")
        self.assertNotIn("Conditional field checks.", [item.value for item in page.markdown])
        page.button[0].click().run()
        self.assertEqual(len(page.error), 2)
        self.assertEqual(self.generate.call_count, 1)

    def test_reruns_do_not_restore_an_edited_or_cleared_example_question(self):
        page = AppTest.from_file(str(ROOT / "app.py")).run()
        page.text_area(key="question").input("")
        page.button[0].click().run()
        page.radio(key="language").set_value("Français").run()
        self.assertEqual(page.text_area(key="question").value, "")
        self.generate.assert_not_called()

    def test_vercel_assessment_needs_no_access_code(self):
        with patch.dict(os.environ, {"VERCEL": "1"}):
            os.environ.pop("DEMO_ACCESS_CODE", None)
            page = AppTest.from_file(str(ROOT / "app.py")).run()
            self.assertFalse(page.text_input)
            page.button[0].click().run()
            self.assertFalse(page.exception)
            self.assertFalse(page.error)
            self.assertTrue(page.success)
            self.search.assert_called_once()
            self.generate.assert_called_once()

    def test_vercel_comparison_needs_no_access_code(self):
        with patch.dict(os.environ, {"VERCEL": "1"}):
            os.environ.pop("DEMO_ACCESS_CODE", None)
            page = self.comparison_page()
            self.assertFalse(page.text_input)
            page.button[0].click().run()
            self.assertFalse(page.exception)
            self.assertFalse(page.error)
            self.assertTrue(page.success)
            self.search.assert_called_once_with(application.COMPARISON["question"], application.COMPARISON["context"], top_k=2)
            self.generate.assert_called_once()
            self.assertTrue(self.generate.call_args.kwargs["comparison_image_png"])
            self.assertEqual(self.generate.call_args.kwargs["image_dates"], ("2023-02-12", "2024-02-19"))


if __name__ == "__main__":
    unittest.main()
