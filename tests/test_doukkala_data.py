from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "demo_data/doukkala_change"


class DoukkalaDataTests(unittest.TestCase):
    def test_two_dated_scenes_have_aligned_analytical_bands_and_quality_layers(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        self.assertEqual([scene["date"] for scene in manifest["scenes"]], ["2024-02-20", "2025-02-14"])
        self.assertEqual(manifest["interval_days"], 360)
        tiles = json.loads((ROOT / "demo_data/sentinel2/manifest.json").read_text())["tiles"]
        original = next(tile for tile in tiles if tile["name"] == "doukkala")
        self.assertEqual(manifest["grid"]["transform_gdal"], original["transform_gdal"])
        self.assertEqual(manifest["grid"]["crs"], "EPSG:32629")
        self.assertEqual((DATA / manifest["scenes"][1]["assets"]["rgb"]["file"]).read_bytes(),
                         (ROOT / "demo_data/sentinel2" / original["png_file"]).read_bytes())
        for scene in manifest["scenes"]:
            source = json.loads((DATA / scene["source_stac_file"]).read_text())
            self.assertEqual(source["collection"], "sentinel-2-c1-l2a")
            self.assertEqual(source["id"], scene["source_scene_id"])
            self.assertEqual(source["properties"]["platform"], "sentinel-2b")
            self.assertTrue(scene["acquired_utc"].startswith(scene["date"]))
            for band in ("red", "nir", "scl"):
                with self.subTest(date=scene["date"], band=band):
                    asset = scene["assets"][band]
                    with Image.open(DATA / asset["file"]) as image:
                        self.assertEqual(image.size, (512, 512))
                        self.assertEqual(tuple(image.tag_v2[33550]), (10.0, 10.0, 0.0))
                        self.assertEqual(tuple(image.tag_v2[33922]), (0.0, 0.0, 0.0, 556270.0, 3617770.0, 0.0))
                        keys = image.tag_v2[34735][4:]
                        self.assertIn((3072, 0, 1, 32629), list(zip(*(iter(keys),) * 4)))
                        self.assertEqual(image.tag_v2[42113].strip("\x00"), "0")
                        if band == "scl":
                            self.assertEqual(image.mode, "L")
                            counts = {str(k): v for k, v in Counter(image.tobytes()).items()}
                            self.assertEqual(counts, scene["scl_class_counts_10m"])
                            self.assertTrue(set(counts).issubset({"4", "5", "6"}))
                        else:
                            self.assertEqual(image.mode, "I;16")
                            self.assertGreater(image.getextrema()[1], 255)
                            metadata = ET.fromstring(image.tag_v2[42112])
                            calibration = {item.attrib["role"]: float(item.text) for item in metadata if item.attrib.get("role") in ("scale", "offset")}
                            self.assertEqual(calibration, {"scale": 0.0001, "offset": -0.1})
                            self.assertEqual((asset["scale"], asset["offset"]), (0.0001, -0.1))
            with Image.open(DATA / scene["assets"]["rgb"]["file"]) as image:
                self.assertEqual(image.size, (512, 512))
                self.assertEqual(image.mode, "RGB")

    def test_downloaded_assets_and_source_metadata_match_their_checksums(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        expected = set()
        for scene in manifest["scenes"]:
            expected.update((scene["source_stac_file"], scene["product_metadata_file"]))
            expected.update(asset["file"] for asset in scene["assets"].values())
        self.assertEqual(set(manifest["sha256"]), expected)
        for name, digest in manifest["sha256"].items():
            with self.subTest(file=name):
                self.assertEqual(sha256((DATA / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
