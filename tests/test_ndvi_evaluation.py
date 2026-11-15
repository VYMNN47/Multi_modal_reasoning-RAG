import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests import evaluate_ndvi_answers as evaluator


class NdviEvaluationTests(unittest.TestCase):
    def test_area_probe_accepts_both_number_formats_and_catches_wrong_totals(self):
        for language, correct, wrong in (("English", "2,621.40", "2,614.40"), ("Français", "2 621,40", "2 614,40")):
            for value, expected in ((correct, True), (wrong, False)):
                with self.subTest(language=language, value=value), TemporaryDirectory() as directory:
                    path = Path(directory) / "cases.json"
                    path.write_text(json.dumps([{"id": "area", "question": "Explain the saved area.",
                        "language": language, "context": "", "expected": {"contains": [], "regex": ".*"}}]))
                    middle, last = ("Evidence and interpretations", "Next checks") if language == "English" else ("Références et interprétations", "Vérifications à réaliser")
                    answer = {"text": f"### Observations\n\n{value} ha\n\n### {middle}\n\nSaved results.\n\n### {last}\n\nCheck field observations.",
                        "sources": [], "evidence_status": "insufficient"}
                    with patch.object(evaluator, "CASES", path), patch("app.assess", return_value=answer), patch("builtins.print"):
                        report = evaluator.evaluate(Path(directory) / "report.json")
                    self.assertEqual(report["cases"][0]["checks"]["reported_areas_match_saved_values"], expected)
                    self.assertEqual(report["passed"], int(expected))


if __name__ == "__main__":
    unittest.main()
