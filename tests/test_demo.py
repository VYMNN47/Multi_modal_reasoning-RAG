from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from starlette.testclient import TestClient

import app as application
from asgi import app
import rag

ROOT = Path(__file__).resolve().parents[1]
COMPARISON_LABEL = "Casablanca: Drought, 2023–2024"


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


if __name__ == "__main__":
    unittest.main()
