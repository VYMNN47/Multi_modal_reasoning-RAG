"""Calculation checks requiring the separate Rasterio data environment."""

import unittest

import numpy as np

from calculate_doukkala_ndvi import calculate_ndvi


CALIBRATION = {"red_scale": 0.0001, "red_offset": -0.1,
               "nir_scale": 0.0001, "nir_offset": -0.1}


class NdviCalculationTests(unittest.TestCase):
    def test_calibrated_ndvi_preserves_negative_zero_and_positive_results(self):
        red = np.array([[2000, 6000, 2000, 1000, 2000]], dtype=np.uint16)
        nir = np.array([[6000, 2000, 2000, 2000, 1000]], dtype=np.uint16)
        result = calculate_ndvi(red, nir, np.full(red.shape, 4), **CALIBRATION)
        np.testing.assert_allclose(result, [[2 / 3, -2 / 3, 0, 1, -1]], atol=1e-7)
        self.assertEqual(result.dtype, np.float32)

    def test_only_vegetation_and_nonvegetated_land_are_eligible(self):
        scl = np.arange(12).reshape(2, 6)
        result = calculate_ndvi(np.full(scl.shape, 2000), np.full(scl.shape, 6000), scl, **CALIBRATION)
        np.testing.assert_array_equal(np.isfinite(result), np.isin(scl, [4, 5]))

    def test_nodata_negative_reflectance_zero_denominator_and_nonfinite_values_are_masked(self):
        red = np.array([[0, 2000, 500, 1000, np.nan, 2000, 2000]])
        nir = np.array([[6000, 0, 6000, 1000, 6000, np.inf, 500]])
        with np.errstate(all="raise"):
            result = calculate_ndvi(red, nir, np.full(red.shape, 4), **CALIBRATION)
        self.assertTrue(np.isnan(result).all())

    def test_misaligned_or_non_image_arrays_are_rejected(self):
        for red, nir, scl in ((np.ones((2, 2)), np.ones((1, 2)), np.ones((2, 2))),
                              (np.ones(2), np.ones(2), np.ones(2))):
            with self.subTest(shape=red.shape), self.assertRaisesRegex(ValueError, "same two-dimensional shape"):
                calculate_ndvi(red, nir, scl, **CALIBRATION)

    def test_invalid_calibration_is_rejected(self):
        band = np.full((1, 1), 2000)
        for field, value in (("red_scale", 0), ("nir_scale", -1), ("red_offset", np.nan), ("nir_offset", np.inf)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "calibration"):
                calculate_ndvi(band, band, np.full((1, 1), 4), **{**CALIBRATION, field: value})


if __name__ == "__main__":
    unittest.main()
