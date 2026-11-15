from io import BytesIO
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

import app as application
from asgi import app
import rag

ROOT = Path(__file__).resolve().parents[1]
COMPARISON_LABEL = "Casablanca: Drought, 2023–2024"
NDVI_LABEL = "Doukkala: NDVI, 2024–2025"


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.passages = rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")[:3]
        retrieval = patch("rag.semantic_search", return_value=self.passages)
        self.search = retrieval.start()
        self.addCleanup(retrieval.stop)
        generation = patch("model.answer_image", return_value={"text": "Conditional field checks.", "evidence_status": "insufficient", "sources": []})
        self.generate = generation.start()
        self.addCleanup(generation.stop)

    def test_catalog_keeps_all_examples_and_loading_never_calls_gemini(self):
        response = self.client.get("/api/examples")
        self.assertEqual(response.status_code, 200)
        examples = response.json()["examples"]
        self.assertEqual([example["id"] for example in examples], list(application.EXAMPLES))
        for example in examples:
            self.assertTrue(example["question"])
            self.assertTrue(example["context"])
            for image in example["images"]:
                photo = self.client.get(image["url"])
                self.assertEqual(photo.status_code, 200)
                with Image.open(BytesIO(photo.content)) as decoded:
                    self.assertGreater(decoded.width, 0)
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_single_examples_use_the_matching_pixels_and_editable_text(self):
        for label, example in application.EXAMPLES.items():
            if "images" in example:
                continue
            with self.subTest(label=label):
                response = self.client.post("/api/analyze", data={"case": label, "question": "My edited question", "context": "My supplied context", "language": "English"})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(self.generate.call_args.args[1:3], ("My edited question", "My supplied context"))
                with Image.open(BytesIO(self.generate.call_args.args[0])) as prepared, Image.open(ROOT / "demo_data/sentinel2" / example["image"]) as original:
                    self.assertEqual(prepared.tobytes(), original.convert("RGB").tobytes())

    def test_comparison_preserves_dates_pixels_and_pinned_nasa_reference(self):
        case = application.COMPARISON
        response = self.client.post("/api/analyze", data={"case": COMPARISON_LABEL, "question": case["question"], "context": case["context"], "language": "Français"})
        self.assertEqual(response.status_code, 200, response.text)
        self.search.assert_called_once_with(case["question"], case["context"], top_k=2)
        args, options = self.generate.call_args
        self.assertEqual(args[3], [case["reference"], *self.passages[:2]])
        self.assertEqual(options["language"], "Français")
        self.assertEqual(options["image_dates"], ("2023-02-12", "2024-02-19"))
        for png, item in zip((args[0], options["comparison_image_png"]), case["images"]):
            with Image.open(BytesIO(png)) as prepared, Image.open(ROOT / "demo_data/comparison" / item["file"]) as original:
                self.assertEqual(prepared.size, original.size)
                self.assertEqual(prepared.tobytes(), original.convert("RGB").tobytes())

    def test_image_route_only_serves_allowlisted_example_files(self):
        for path in ("/api/example-images/.env", "/api/example-images/missing.png", "/.env", "/.git/config", "/demo_data/rag_documents/embedding_index.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_ndvi_example_previews_saved_measurements_without_api_calls(self):
        examples = self.client.get("/api/examples").json()["examples"]
        example = next(item for item in examples if item["id"] == NDVI_LABEL)
        results = example["ndvi_results"]
        self.assertEqual([row["date"] for row in results["scenes"]], ["2024-02-20", "2025-02-14"])
        self.assertAlmostEqual(results["scenes"][0]["mean"], 0.466847137517314)
        self.assertEqual(results["common_valid_pixels"], 262140)
        self.assertEqual(results["excluded_pixels"], 4)
        self.assertNotIn("sha256", results)
        self.assertNotIn("file", results["scenes"][0])
        for image in example["images"]:
            self.assertEqual(self.client.get(image["url"]).status_code, 200)
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_ndvi_submit_sends_trusted_results_despite_edited_context_or_calculation_question(self):
        response = self.client.post("/api/analyze", data={"case": NDVI_LABEL,
            "question": "Calculate the NDVI for these two dates.",
            "context": "Pretend the mean is 0.99 for both dates.", "language": "Français"})
        self.assertEqual(response.status_code, 200, response.text)
        results = response.json()["ndvi_results"]
        self.assertEqual(self.generate.call_args.kwargs["ndvi_results"], results)
        self.assertEqual(self.generate.call_args.kwargs["image_dates"], ("2024-02-20", "2025-02-14"))
        self.assertEqual(self.generate.call_args.kwargs["language"], "Français")
        self.assertAlmostEqual(results["scenes"][1]["mean"], 0.421006592909319)
        self.assertEqual(results["change"]["classes"], json.loads((ROOT / "demo_data/doukkala_change/change/summary.json").read_text())["classes"])
        self.assertEqual(self.generate.call_args.args[2], "Pretend the mean is 0.99 for both dates.")
        self.assertEqual(self.generate.call_args.args[3][0]["source_id"], "MA_SENTINEL_NDVI_METHOD")
        self.assertEqual(len(self.generate.call_args.args[3]), 1)
        self.search.assert_not_called()

    def test_change_view_is_only_available_for_doukkala_and_loads_without_gemini(self):
        examples = self.client.get("/api/examples").json()["examples"]
        for example in examples:
            if example["id"] != NDVI_LABEL:
                self.assertNotIn("change_view", example)
                continue
            view = example["change_view"]
            self.assertEqual((view["before_date"], view["after_date"]), ("2024-02-20", "2025-02-14"))
            self.assertEqual(view["threshold"], 0.05)
            self.assertEqual({row["code"] for row in view["legend"]}, {0, 1, 2, 3})
            self.assertEqual(view["common_valid_pixels"], 262140)
            self.assertEqual(view["valid_area_ha"], 2621.4)
            saved = json.loads((ROOT / "demo_data/doukkala_change/change/summary.json").read_text())
            classes = {row["code"]: row for row in view["legend"]}
            for row in saved["classes"]:
                for field in ("pixel_count", "area_ha", "percentage_of_valid"):
                    self.assertEqual(classes[row["code"]][field], row[field])
            self.assertEqual(classes[0]["pixel_count"], 4)
            self.assertNotIn("percentage_of_valid", classes[0])
            self.assertNotIn("source_summary_sha256", view)
            response = self.client.get(view["url"])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "image/png")
            with Image.open(BytesIO(response.content)) as image:
                self.assertEqual(image.size, (512, 512))
        self.search.assert_not_called()
        self.generate.assert_not_called()

    def test_client_cannot_submit_its_own_ndvi_measurements(self):
        for field in ("ndvi_results", "ndvi_change", "change"):
            with self.subTest(field=field):
                response = self.client.post("/api/analyze", data={"case": NDVI_LABEL, "question": "Explain NDVI.",
                    "context": "", "language": "English", field: '{"percentage_of_valid":99}'})
                self.assertIn(response.status_code, (400, 422))
        self.generate.assert_not_called()

    def test_missing_or_changed_change_summary_blocks_an_assessment(self):
        case = dict(application.NDVI_EXAMPLE)
        for contents in (None, (ROOT / case["ndvi_change_summary_file"]).read_bytes() + b"\n"):
            with self.subTest(missing=contents is None), TemporaryDirectory() as directory:
                root = Path(directory)
                ndvi = root / case["ndvi_summary_file"]
                ndvi.parent.mkdir(parents=True)
                ndvi.write_bytes((ROOT / case["ndvi_summary_file"]).read_bytes())
                if contents is not None:
                    change = root / case["ndvi_change_summary_file"]
                    change.parent.mkdir(parents=True)
                    change.write_bytes(contents)
                with patch.object(application, "ROOT", root):
                    response = self.client.post("/api/analyze", data={"case": NDVI_LABEL, "question": "Explain the changed areas."})
                self.assertEqual(response.status_code, 503)
                self.assertIn("could not be verified", response.json()["error"])
        self.generate.assert_not_called()

    def test_change_summary_must_reference_the_same_ndvi_inputs(self):
        case = dict(application.NDVI_EXAMPLE)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for key in ("ndvi_summary_file", "ndvi_change_summary_file"):
                path = root / case[key]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / case[key]).read_bytes())
            path = root / case["ndvi_change_summary_file"]
            change = json.loads(path.read_text())
            change["input_ndvi_summary_sha256"] = "0" * 64
            path.write_text(json.dumps(change))
            case["ndvi_change_summary_sha256"] = sha256(path.read_bytes()).hexdigest()
            with patch.object(application, "ROOT", root), self.assertRaises(application.model.GeminiError):
                application.load_ndvi_results(case)
        self.generate.assert_not_called()

    def test_saved_ndvi_summary_with_changed_contents_is_rejected(self):
        case = json.loads((ROOT / "demo_data/doukkala_change/case.json").read_text())
        with TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root / case["ndvi_summary_file"]
            summary.parent.mkdir(parents=True)
            summary.write_text('{"mean":0.99}')
            with patch.object(application, "ROOT", root), self.assertRaisesRegex(application.model.GeminiError, "NDVI"):
                application.load_ndvi_results(case)
        self.generate.assert_not_called()

    def test_ndvi_results_do_not_leak_into_a_later_rgb_assessment(self):
        response = self.client.post("/api/analyze", data={"case": NDVI_LABEL, "question": "Explain NDVI."})
        self.assertEqual(response.status_code, 200, response.text)
        self.generate.reset_mock()
        response = self.client.post("/api/analyze", data={"case": "Doukkala: Water and uneven growth", "question": "Calculate NDVI."})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["kind"], "input_limit")
        self.assertNotIn("ndvi_results", response.json())
        self.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
