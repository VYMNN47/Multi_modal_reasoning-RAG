# /// script
# requires-python = ">=3.11"
# dependencies = ["rasterio==1.4.4"]
# ///
"""Classify saved Doukkala NDVI offline: uv run calculate_doukkala_change.py."""

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from rasterio.transform import Affine


NODATA = -9999.0
# shortcut: this is a demo tolerance; validate it against reference observations before operational use.
CHANGE_THRESHOLD = 0.05
DATA = Path(__file__).resolve().parent / "demo_data/doukkala_change"
INPUT = DATA / "ndvi"
OUTPUT = DATA / "change"


def calculate_change(before, after, common, *, threshold=CHANGE_THRESHOLD):
    if (before.ndim != 2 or before.shape != after.shape or before.shape != common.shape
            or common.dtype != np.bool_):
        raise ValueError("NDVI arrays and a boolean mask must have the same two-dimensional shape.")
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float, np.floating))
            or not np.isfinite(threshold) or not 0 < threshold <= 2):
        raise ValueError("The change threshold must be finite and between 0 (exclusive) and 2.")
    if not common.any():
        raise ValueError("There are no common valid pixels to classify.")
    for values in (before[common], after[common]):
        if not np.all(np.isfinite(values) & (values >= -1) & (values <= 1)):
            raise ValueError("Common pixels must contain finite NDVI values in [-1, 1].")
    difference = np.full(before.shape, NODATA, dtype=np.float32)
    difference[common] = after[common].astype(np.float64) - before[common].astype(np.float64)
    classes = np.zeros(before.shape, dtype=np.uint8)
    classes[common] = 2
    # Compare stored float32 values so reopening the raster reproduces its classes.
    cutoff = np.float32(threshold)
    classes[common & (difference < -cutoff)] = 1
    classes[common & (difference > cutoff)] = 3
    return difference, classes


def main():
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT} already exists. Move it aside before calculating a replacement.")
    manifest_bytes = (DATA / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    ndvi_bytes = (INPUT / "summary.json").read_bytes()
    ndvi_summary = json.loads(ndvi_bytes)
    if ndvi_summary["input_manifest_sha256"] != sha256(manifest_bytes).hexdigest():
        raise ValueError("The NDVI source-manifest checksum does not match the current data package.")
    scenes = ndvi_summary["scenes"]
    if len(scenes) != 2 or date.fromisoformat(scenes[0]["date"]) >= date.fromisoformat(scenes[1]["date"]):
        raise ValueError("The NDVI inputs must contain two chronological dates.")
    saved_grid = manifest["grid"]
    if ndvi_summary["grid"] != saved_grid:
        raise ValueError("The NDVI summary grid differs from the source grid.")
    grid = {"crs": rasterio.crs.CRS.from_string(saved_grid["crs"]),
            "transform": Affine.from_gdal(*saved_grid["transform_gdal"]),
            "width": saved_grid["width_px"], "height": saved_grid["height_px"]}
    if not grid["crs"].is_projected or grid["crs"].linear_units != "metre":
        raise ValueError("Area calculation requires a projected grid in metres.")
    transform = grid["transform"]
    pixel_area = abs(transform.a * transform.e - transform.b * transform.d)
    if not np.isfinite(pixel_area) or pixel_area <= 0:
        raise ValueError("The pixel area must be finite and positive.")
    arrays, valid_masks = [], []
    # Rasterio read/write/mask conventions: https://rasterio.readthedocs.io/en/stable/topics/masks.html
    for name in ("common_valid_mask.tif", *(scene["file"] for scene in scenes)):
        path = (INPUT / name).resolve()
        if not path.is_relative_to(INPUT.resolve()):
            raise ValueError("Input paths must stay inside the NDVI directory.")
        if sha256(path.read_bytes()).hexdigest() != ndvi_summary["sha256"][name]:
            raise ValueError(f"NDVI input checksum mismatch: {name}")
        is_mask = name == "common_valid_mask.tif"
        with rasterio.open(path) as source:
            if (source.count != 1 or source.crs != grid["crs"] or source.transform != transform
                    or source.shape != (grid["height"], grid["width"])
                    or source.dtypes[0] != ("uint8" if is_mask else "float32")
                    or source.nodata != (0 if is_mask else NODATA)):
                raise ValueError(f"Input grid or raster format mismatch: {name}")
            # Reading all (one) bands avoids Rasterio's deprecated NumPy 2.5 shape setter.
            arrays.append(source.read()[0])
            valid_masks.append(source.read_masks()[0] > 0)
    if not np.isin(arrays[0], [0, 1]).all():
        raise ValueError("The common valid mask must contain only 0 and 1.")
    common = arrays[0] == 1
    count = int(common.sum())
    if (count != ndvi_summary["common_valid_pixels"]
            or int(common.size - count) != ndvi_summary["excluded_pixels"]
            or any(not np.array_equal(common, mask) for mask in valid_masks)):
        raise ValueError("The NDVI masks or valid-pixel counts do not match the saved common mask.")
    difference, classes = calculate_change(arrays[1], arrays[2], common)
    values = difference[common].astype(np.float64)
    summary = {
        "before_date": scenes[0]["date"], "after_date": scenes[1]["date"],
        "formula": "NDVI change = after NDVI - before NDVI",
        "threshold": CHANGE_THRESHOLD, "comparison_dtype": "float32",
        "classification_rule": "Decreased < -threshold; stable includes both boundaries; increased > threshold. Comparisons use the saved float32 differences and a float32 threshold.",
        "scope_note": "Demonstration tolerance, not a validated crop-change threshold. Shared valid land includes nonvegetated surfaces. Stable means within the tolerance, not proof of unchanged land or crops. SCL is automated at native 20 m resolution; two dates do not identify crop types or causes.",
        "input_manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "input_ndvi_summary_sha256": sha256(ndvi_bytes).hexdigest(),
        "grid": saved_grid, "pixel_area_m2": pixel_area,
        "common_valid_pixels": count, "excluded_pixels": int(common.size - count),
        "valid_area_ha": count * pixel_area / 10000,
        "excluded_area_ha": int(common.size - count) * pixel_area / 10000,
        "difference": {"file": "ndvi_change_10m.tif", "nodata": NODATA,
                       "mean": float(values.mean()), "median": float(np.median(values)),
                       "min": float(values.min()), "max": float(values.max())},
        "classification": {"file": "ndvi_change_classes_10m.tif", "nodata": 0},
        "classes": [],
    }
    for code, label in ((1, "decreased"), (2, "stable"), (3, "increased")):
        pixels = int(np.count_nonzero(classes == code))
        summary["classes"].append({"code": code, "label": label, "pixel_count": pixels,
                                   "percentage_of_valid": pixels / count * 100,
                                   "area_ha": pixels * pixel_area / 10000})
    with TemporaryDirectory(prefix="change-", dir=DATA) as temporary:
        staging = Path(temporary)
        for key, array, dtype, description in (
            ("difference", difference, "float32", "NDVI change: after minus before"),
            ("classification", classes, "uint8", "NDVI change class: 1 decreased, 2 stable, 3 increased"),
        ):
            asset = summary[key]
            with rasterio.open(staging / asset["file"], "w", driver="GTiff", **grid,
                    count=1, dtype=dtype, nodata=asset["nodata"], compress="deflate") as target:
                target.write(array, 1)
                target.set_band_description(1, description)
        summary["sha256"] = {path.name: sha256(path.read_bytes()).hexdigest() for path in sorted(staging.glob("*.tif"))}
        (staging / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        staging.rename(OUTPUT)
    print(f"Saved NDVI change for {count:,} common valid pixels to {OUTPUT}")
    for row in summary["classes"]:
        print(f"{row['label']}: {row['pixel_count']:,} pixels, {row['percentage_of_valid']:.2f}%, {row['area_ha']:.2f} ha")


if __name__ == "__main__":
    main()
