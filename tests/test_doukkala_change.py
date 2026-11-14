from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import struct
import unittest

from PIL import Image


DATA = Path(__file__).resolve().parents[1] / "demo_data/doukkala_change"
INPUT = DATA / "ndvi"
OUTPUT = DATA / "change"


def float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


class DoukkalaChangeTests(unittest.TestCase):
    def test_saved_differences_and_classes_match_every_shared_valid_pixel_and_grid(self):
        summary = json.loads((OUTPUT / "summary.json").read_text())
        ndvi = json.loads((INPUT / "summary.json").read_text())
        with Image.open(INPUT / "common_valid_mask.tif") as image:
            common = list(image.get_flattened_data())
            grid = {tag: image.tag_v2[tag] for tag in (33550, 33922, 34735)}
        inputs = []
        for scene in ndvi["scenes"]:
            with Image.open(INPUT / scene["file"]) as image:
                inputs.append(list(image.get_flattened_data()))
        outputs = []
        for key, mode, nodata in (("difference", "F", -9999), ("classification", "L", 0)):
            with Image.open(OUTPUT / summary[key]["file"]) as image:
                self.assertEqual(image.mode, mode)
                self.assertEqual(image.size, (512, 512))
                self.assertEqual(float(image.tag_v2[42113].strip("\x00")), nodata)
                for tag, expected in grid.items():
                    self.assertEqual(image.tag_v2[tag], expected)
                outputs.append(list(image.get_flattened_data()))
        cutoff = float32(summary["threshold"])
        for valid, before, after, difference, code in zip(common, *inputs, *outputs):
            if valid:
                self.assertEqual(difference, float32(after - before))
                self.assertTrue(math.isfinite(difference) and -2 <= difference <= 2)
                expected = 1 if difference < -cutoff else 3 if difference > cutoff else 2
                self.assertEqual(code, expected)
            else:
                self.assertEqual((difference, code), (-9999, 0))
        self.assertEqual(Counter(outputs[1])[0], 4)

    def test_summary_statistics_class_areas_denominator_and_checksums_are_reproducible(self):
        summary = json.loads((OUTPUT / "summary.json").read_text())
        ndvi = json.loads((INPUT / "summary.json").read_text())
        self.assertEqual((summary["before_date"], summary["after_date"]), ("2024-02-20", "2025-02-14"))
        self.assertEqual(summary["input_ndvi_summary_sha256"], sha256((INPUT / "summary.json").read_bytes()).hexdigest())
        self.assertEqual(summary["input_manifest_sha256"], sha256((DATA / "manifest.json").read_bytes()).hexdigest())
        self.assertEqual(summary["threshold"], 0.05)
        self.assertEqual(summary["comparison_dtype"], "float32")
        self.assertEqual(summary["common_valid_pixels"], ndvi["common_valid_pixels"])
        self.assertEqual(summary["common_valid_pixels"], 262140)
        self.assertEqual(summary["excluded_pixels"], 4)
        self.assertEqual(summary["pixel_area_m2"], 100)
        self.assertEqual(summary["valid_area_ha"], 2621.4)
        self.assertEqual(summary["excluded_area_ha"], 0.04)
        with Image.open(OUTPUT / summary["difference"]["file"]) as image:
            values = [value for value in image.get_flattened_data() if value != -9999]
        with Image.open(OUTPUT / summary["classification"]["file"]) as image:
            counts = Counter(image.get_flattened_data())
        self.assertAlmostEqual(summary["difference"]["mean"], math.fsum(values) / len(values), places=10)
        self.assertEqual(summary["difference"]["median"], statistics.median(values))
        self.assertEqual((summary["difference"]["min"], summary["difference"]["max"]), (min(values), max(values)))
        self.assertAlmostEqual(summary["difference"]["mean"], ndvi["scenes"][1]["mean"] - ndvi["scenes"][0]["mean"], places=7)
        self.assertEqual([(row["code"], row["label"]) for row in summary["classes"]], [(1, "decreased"), (2, "stable"), (3, "increased")])
        for row in summary["classes"]:
            count = counts[row["code"]]
            self.assertEqual(row["pixel_count"], count)
            self.assertEqual(row["area_ha"], count / 100)
            self.assertAlmostEqual(row["percentage_of_valid"], count / len(values) * 100)
        self.assertEqual(sum(row["pixel_count"] for row in summary["classes"]), len(values))
        self.assertAlmostEqual(sum(row["percentage_of_valid"] for row in summary["classes"]), 100)
        self.assertAlmostEqual(sum(row["area_ha"] for row in summary["classes"]), summary["valid_area_ha"])
        self.assertEqual(set(summary["sha256"]), {summary[key]["file"] for key in ("difference", "classification")})
        for filename, digest in summary["sha256"].items():
            self.assertEqual(sha256((OUTPUT / filename).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
