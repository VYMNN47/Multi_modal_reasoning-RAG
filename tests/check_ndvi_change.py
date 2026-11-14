"""Change calculation checks using the separate Rasterio author environment."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import Affine

import calculate_doukkala_change as change
from calculate_doukkala_change import calculate_change


class NdviChangeCalculationTests(unittest.TestCase):
    def test_after_minus_before_and_three_classes_include_both_stable_boundaries(self):
        before = np.zeros((1, 7), dtype=np.float32)
        after = np.array([[0.25, -0.25, 0, -0.05, 0.05, 0.06, -0.06]], dtype=np.float32)
        difference, classes = calculate_change(before, after, np.ones(before.shape, dtype=bool))
        np.testing.assert_array_equal(difference, after)
        np.testing.assert_array_equal(classes, [[3, 1, 2, 2, 2, 3, 1]])
        self.assertEqual(difference.dtype, np.float32)
        self.assertEqual(classes.dtype, np.uint8)

    def test_values_immediately_outside_the_float32_threshold_are_not_stable(self):
        threshold = np.float32(0.05)
        larger = np.nextafter(threshold, np.float32(np.inf))
        after = np.array([[-larger, -threshold, threshold, larger]], dtype=np.float32)
        _, classes = calculate_change(np.zeros_like(after), after, np.ones(after.shape, dtype=bool))
        np.testing.assert_array_equal(classes, [[1, 2, 2, 3]])

    def test_negative_ndvi_and_the_full_change_range_are_valid(self):
        before = np.array([[-1, 1, -0.2]], dtype=np.float32)
        after = np.array([[1, -1, -0.4]], dtype=np.float32)
        difference, classes = calculate_change(before, after, np.ones(before.shape, dtype=bool))
        np.testing.assert_allclose(difference, [[2, -2, -0.2]], atol=1e-7)
        np.testing.assert_array_equal(classes, [[3, 1, 1]])

    def test_excluded_pixels_stay_nodata_and_inputs_are_not_modified(self):
        before = np.array([[np.nan, -9999, 0.2]], dtype=np.float32)
        after = np.array([[np.inf, -9999, 0.5]], dtype=np.float32)
        common = np.array([[False, False, True]])
        original = [array.copy() for array in (before, after, common)]
        with np.errstate(all="raise"):
            difference, classes = calculate_change(before, after, common)
        np.testing.assert_allclose(difference, [[-9999, -9999, 0.3]], atol=1e-7)
        np.testing.assert_array_equal(classes, [[0, 0, 3]])
        for current, saved in zip((before, after, common), original):
            np.testing.assert_array_equal(current, saved)

    def test_integer_inputs_do_not_underflow(self):
        difference, classes = calculate_change(np.array([[1]], dtype=np.uint8),
            np.array([[0]], dtype=np.uint8), np.array([[True]]))
        self.assertEqual(float(difference[0, 0]), -1)
        self.assertEqual(int(classes[0, 0]), 1)

    def test_invalid_shapes_and_nonboolean_masks_are_rejected(self):
        for before, after, common in (
            (np.zeros((2, 2)), np.zeros((1, 2)), np.ones((2, 2), dtype=bool)),
            (np.zeros(2), np.zeros(2), np.ones(2, dtype=bool)),
            (np.zeros((2, 2)), np.zeros((2, 2)), np.ones((1, 2), dtype=bool)),
            (np.zeros((2, 2)), np.zeros((2, 2)), np.ones((2, 2), dtype=np.uint8)),
        ):
            with self.subTest(shape=before.shape), self.assertRaises(ValueError):
                calculate_change(before, after, common)

    def test_invalid_thresholds_and_missing_valid_pixels_are_rejected(self):
        band, common = np.zeros((1, 1)), np.ones((1, 1), dtype=bool)
        for threshold in (0, -0.05, np.nan, np.inf, 2.1, True):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                calculate_change(band, band, common, threshold=threshold)
        with self.assertRaisesRegex(ValueError, "valid"):
            calculate_change(band, band, ~common)

    def test_invalid_ndvi_on_a_common_pixel_is_rejected(self):
        for invalid in (np.nan, np.inf, -9999, -1.01, 1.01):
            with self.subTest(value=invalid), self.assertRaisesRegex(ValueError, "NDVI"):
                calculate_change(np.array([[invalid]]), np.zeros((1, 1)), np.array([[True]]))


class NdviChangeWriterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = self.root / "ndvi"
        self.inputs.mkdir()
        self.output = self.root / "change"
        grid = {"crs": "EPSG:32629", "transform_gdal": [556270, 10, 0, 3617770, 0, -10],
                "width_px": 4, "height_px": 1}
        manifest = json.dumps({"grid": grid}).encode()
        (self.root / "manifest.json").write_bytes(manifest)
        self.summary = {"input_manifest_sha256": sha256(manifest).hexdigest(), "grid": grid,
            "common_valid_pixels": 3, "excluded_pixels": 1,
            "scenes": [{"date": "2024-02-20", "file": "before.tif"}, {"date": "2025-02-14", "file": "after.tif"}], "sha256": {}}
        for filename, values, dtype, nodata in (
            ("common_valid_mask.tif", [[1, 1, 1, 0]], "uint8", 0),
            ("before.tif", [[0, 0, 0, -9999]], "float32", -9999),
            ("after.tif", [[-0.1, 0.02, 0.1, -9999]], "float32", -9999),
        ):
            with rasterio.open(self.inputs / filename, "w", driver="GTiff", width=4, height=1,
                    count=1, crs=grid["crs"], transform=Affine.from_gdal(*grid["transform_gdal"]),
                    dtype=dtype, nodata=nodata) as target:
                target.write(np.array(values, dtype=dtype), 1)
            self.refresh_checksum(filename)
        patcher = patch.multiple(change, DATA=self.root, INPUT=self.inputs, OUTPUT=self.output)
        patcher.start()
        self.addCleanup(patcher.stop)

    def refresh_checksum(self, filename):
        self.summary["sha256"][filename] = sha256((self.inputs / filename).read_bytes()).hexdigest()
        (self.inputs / "summary.json").write_text(json.dumps(self.summary))

    def test_offline_run_saves_differences_classes_and_area_without_counting_nodata(self):
        with patch("builtins.print"):
            change.main()
        summary = json.loads((self.output / "summary.json").read_text())
        with rasterio.open(self.output / summary["difference"]["file"]) as source:
            np.testing.assert_allclose(source.read()[0], [[-0.1, 0.02, 0.1, -9999]], atol=1e-7)
            self.assertEqual(source.crs.to_epsg(), 32629)
            self.assertEqual(source.nodata, -9999)
        with rasterio.open(self.output / summary["classification"]["file"]) as source:
            np.testing.assert_array_equal(source.read()[0], [[1, 2, 3, 0]])
            self.assertEqual(source.dtypes, ("uint8",))
            self.assertEqual(source.nodata, 0)
        self.assertEqual(summary["common_valid_pixels"], 3)
        self.assertEqual(summary["excluded_pixels"], 1)
        self.assertEqual(summary["pixel_area_m2"], 100)
        self.assertEqual(summary["valid_area_ha"], 0.03)
        for row in summary["classes"]:
            self.assertEqual(row["pixel_count"], 1)
            self.assertEqual(row["area_ha"], 0.01)
            self.assertAlmostEqual(row["percentage_of_valid"], 100 / 3)
        self.assertEqual(summary["input_ndvi_summary_sha256"], sha256((self.inputs / "summary.json").read_bytes()).hexdigest())
        for filename, digest in summary["sha256"].items():
            self.assertEqual(sha256((self.output / filename).read_bytes()).hexdigest(), digest)

    def test_existing_output_is_not_replaced(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("keep")
        with self.assertRaisesRegex(SystemExit, "already exists"):
            change.main()
        self.assertEqual(marker.read_text(), "keep")

    def test_changed_input_is_rejected_before_publishing(self):
        path = self.inputs / "after.tif"
        path.write_bytes(path.read_bytes() + b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            change.main()
        self.assertFalse(self.output.exists())

    def test_grid_mismatch_is_rejected_even_when_file_checksum_matches(self):
        with rasterio.open(self.inputs / "after.tif", "r+") as source:
            source.transform = Affine.from_gdal(556280, 10, 0, 3617770, 0, -10)
        self.refresh_checksum("after.tif")
        with self.assertRaisesRegex(ValueError, "grid"):
            change.main()
        self.assertFalse(self.output.exists())

    def test_invalid_mask_values_are_not_silently_treated_as_valid(self):
        with rasterio.open(self.inputs / "common_valid_mask.tif", "r+") as source:
            source.write(np.array([[2, 1, 1, 0]], dtype=np.uint8), 1)
        self.refresh_checksum("common_valid_mask.tif")
        with self.assertRaisesRegex(ValueError, "mask"):
            change.main()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
