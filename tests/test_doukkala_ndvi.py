from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import unittest

from PIL import Image


DATA = Path(__file__).resolve().parents[1] / "demo_data/doukkala_change"
OUTPUT = DATA / "ndvi"


class DoukkalaNdviTests(unittest.TestCase):
    def assert_doukkala_grid(self, image):
        self.assertEqual(image.size, (512, 512))
        self.assertEqual(tuple(image.tag_v2[33550]), (10.0, 10.0, 0.0))
        self.assertEqual(tuple(image.tag_v2[33922]), (0.0, 0.0, 0.0, 556270.0, 3617770.0, 0.0))
        keys = image.tag_v2[34735]
        entries = [tuple(keys[index:index + 4]) for index in range(4, len(keys), 4)]
        self.assertIn((3072, 0, 1, 32629), entries)

    def test_saved_indices_preserve_the_grid_share_a_mask_and_match_calibrated_band_samples(self):
        inputs = json.loads((DATA / "manifest.json").read_text())
        summary = json.loads((OUTPUT / "summary.json").read_text())
        masks = []
        with Image.open(OUTPUT / "common_valid_mask.tif") as image:
            common = list(image.get_flattened_data())
            self.assert_doukkala_grid(image)
            self.assertTrue(set(common).issubset({0, 1}))
        for scene, result in zip(inputs["scenes"], summary["scenes"]):
            self.assertEqual(result["date"], scene["date"])
            with Image.open(OUTPUT / result["file"]) as image:
                self.assertEqual(image.mode, "F")
                self.assert_doukkala_grid(image)
                self.assertEqual(float(image.tag_v2[42113].strip("\x00")), -9999.0)
                values = list(image.get_flattened_data())
            masks.append([value != -9999 for value in values])
            self.assertEqual(masks[-1], [bool(value) for value in common])
            bands = {}
            for name in ("red", "nir", "scl"):
                with Image.open(DATA / scene["assets"][name]["file"]) as image:
                    bands[name] = list(image.get_flattened_data())
            for index in range(0, len(values), 4093):
                if common[index]:
                    self.assertIn(bands["scl"][index], (4, 5))
                    red = bands["red"][index] / 10000 - 0.1
                    nir = bands["nir"][index] / 10000 - 0.1
                    self.assertAlmostEqual(values[index], (nir - red) / (nir + red), places=6)
        self.assertEqual(masks[0], masks[1])
        self.assertEqual(sum(common), summary["common_valid_pixels"])
        self.assertEqual(summary["common_valid_pixels"], 262140)
        self.assertEqual(summary["excluded_pixels"], 4)

    def test_summary_statistics_and_output_checksums_match_the_saved_indices(self):
        summary = json.loads((OUTPUT / "summary.json").read_text())
        self.assertEqual(summary["input_manifest_sha256"], sha256((DATA / "manifest.json").read_bytes()).hexdigest())
        for scene in summary["scenes"]:
            with Image.open(OUTPUT / scene["file"]) as image:
                valid = [value for value in image.get_flattened_data() if value != -9999]
            self.assertTrue(all(math.isfinite(value) and -1 <= value <= 1 for value in valid))
            self.assertEqual(len(valid), summary["common_valid_pixels"])
            self.assertAlmostEqual(scene["mean"], math.fsum(valid) / len(valid), places=7)
            self.assertAlmostEqual(scene["median"], statistics.median(valid), places=7)
            self.assertEqual((scene["min"], scene["max"]), (min(valid), max(valid)))
        self.assertEqual(set(summary["sha256"]), {"common_valid_mask.tif", *(scene["file"] for scene in summary["scenes"])})
        for name, digest in summary["sha256"].items():
            self.assertEqual(sha256((OUTPUT / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
