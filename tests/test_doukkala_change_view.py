from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image, ImageColor

import prepare_doukkala_change_view as renderer


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "demo_data/doukkala_change"
OUTPUT = ROOT / "assets/doukkala-change"


class ChangeViewRenderTests(unittest.TestCase):
    def test_class_codes_become_exact_colours_and_nodata_is_transparent(self):
        source = Image.frombytes("L", (2, 2), bytes([0, 1, 2, 3]))
        original = source.tobytes()
        result = renderer.colour_classes(source)
        self.assertEqual(result.size, source.size)
        self.assertEqual(result.mode, "RGBA")
        self.assertEqual(result.get_flattened_data(), (
            (0, 0, 0, 0), (177, 91, 58, 255), (217, 222, 216, 255), (35, 100, 64, 255)))
        self.assertEqual(source.tobytes(), original)

    def test_wrong_mode_or_unknown_class_is_rejected(self):
        for source in (Image.new("RGB", (1, 1)), Image.new("L", (1, 1), 4)):
            with self.subTest(mode=source.mode), self.assertRaises(ValueError):
                renderer.colour_classes(source)

    def test_existing_output_is_not_replaced(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            marker = output / "keep.txt"
            marker.write_text("keep")
            with patch.object(renderer, "OUTPUT", output), self.assertRaisesRegex(SystemExit, "already exists"):
                renderer.main()
            self.assertEqual(marker.read_text(), "keep")

    def test_renderer_copies_saved_class_metrics_with_the_valid_pixel_denominator(self):
        summary = json.loads((DATA / "change/summary.json").read_text())
        with TemporaryDirectory() as directory, patch.object(renderer, "OUTPUT", Path(directory) / "view"):
            renderer.main()
            view = json.loads((renderer.OUTPUT / "view.json").read_text())
        self.assertEqual(view["common_valid_pixels"], 262140)
        self.assertEqual(view["valid_area_ha"], 2621.4)
        classes = {row["code"]: row for row in view["legend"]}
        for saved in summary["classes"]:
            row = classes[saved["code"]]
            for field in ("pixel_count", "area_ha", "percentage_of_valid"):
                self.assertEqual(row[field], saved[field])
            self.assertAlmostEqual(row["area_ha"], row["pixel_count"] * 0.01)
            self.assertAlmostEqual(row["percentage_of_valid"], 100 * row["pixel_count"] / view["common_valid_pixels"])
        self.assertEqual(sum(classes[code]["pixel_count"] for code in (1, 2, 3)), view["common_valid_pixels"])
        self.assertAlmostEqual(sum(classes[code]["percentage_of_valid"] for code in (1, 2, 3)), 100)
        self.assertAlmostEqual(sum(classes[code]["area_ha"] for code in (1, 2, 3)), view["valid_area_ha"])
        self.assertEqual(classes[0]["pixel_count"], 4)
        self.assertEqual(classes[0]["area_ha"], 0.04)
        self.assertNotIn("percentage_of_valid", classes[0])


class SavedChangeViewTests(unittest.TestCase):
    def test_generated_view_dates_threshold_and_source_hashes_match_saved_results(self):
        metadata = json.loads((OUTPUT / "view.json").read_text())
        summary_path = DATA / "change/summary.json"
        summary = json.loads(summary_path.read_text())
        case = json.loads((DATA / "case.json").read_text())
        self.assertEqual(metadata["source_summary_sha256"], sha256(summary_path.read_bytes()).hexdigest())
        self.assertEqual(metadata["source_classification_sha256"], sha256((DATA / "change" / summary["classification"]["file"]).read_bytes()).hexdigest())
        self.assertEqual(metadata["source_ndvi_summary_sha256"], case["ndvi_summary_sha256"])
        self.assertEqual([metadata["before_date"], metadata["after_date"]], [row["date"] for row in case["images"]])
        self.assertEqual(metadata["threshold"], summary["threshold"])
        self.assertEqual(metadata["url"], "/assets/doukkala-change/change.png")
        self.assertEqual(metadata["image_sha256"], sha256((OUTPUT / "change.png").read_bytes()).hexdigest())

    def test_every_png_pixel_matches_the_class_raster_without_resampling(self):
        metadata = json.loads((OUTPUT / "view.json").read_text())
        summary = json.loads((DATA / "change/summary.json").read_text())
        colours = {row["code"]: ImageColor.getcolor(row["color"], "RGBA") for row in metadata["legend"]}
        self.assertEqual(set(colours), {0, 1, 2, 3})
        with Image.open(DATA / "change" / summary["classification"]["file"]) as source, Image.open(OUTPUT / "change.png") as rendered:
            self.assertEqual(rendered.size, source.size)
            self.assertEqual(rendered.size, (metadata["width"], metadata["height"]))
            self.assertEqual(rendered.mode, "RGBA")
            self.assertEqual(rendered.get_flattened_data(), tuple(colours[code] for code in source.get_flattened_data()))
            counts = Counter(rendered.get_flattened_data())
        self.assertEqual(counts[colours[0]], 4)
        for row in summary["classes"]:
            self.assertEqual(counts[colours[row["code"]]], row["pixel_count"])


if __name__ == "__main__":
    unittest.main()
