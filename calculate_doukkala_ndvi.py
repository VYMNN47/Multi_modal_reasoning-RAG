# /// script
# requires-python = ">=3.11"
# dependencies = ["rasterio==1.4.4"]
# ///
"""Calculate the saved Doukkala pair offline: uv run calculate_doukkala_ndvi.py."""

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from rasterio.transform import Affine


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "demo_data/doukkala_change"
OUTPUT = DATA / "ndvi"
NODATA = -9999.0


def calculate_ndvi(red, nir, scl, *, red_scale, red_offset, nir_scale, nir_offset):
    if red.ndim != 2 or red.shape != nir.shape or red.shape != scl.shape:
        raise ValueError("Red, NIR and SCL must have the same two-dimensional shape.")
    if not np.isfinite([red_scale, red_offset, nir_scale, nir_offset]).all() or red_scale <= 0 or nir_scale <= 0:
        raise ValueError("Reflectance calibration must be finite with positive scales.")
    valid = np.isin(scl, [4, 5]) & (red != 0) & (nir != 0) & np.isfinite(red) & np.isfinite(nir)
    red_reflectance = np.where(valid, red, 0).astype(np.float64) * red_scale + red_offset
    nir_reflectance = np.where(valid, nir, 0).astype(np.float64) * nir_scale + nir_offset
    denominator = nir_reflectance + red_reflectance
    valid &= (red_reflectance >= 0) & (nir_reflectance >= 0) & np.isfinite(denominator) & (denominator > 0)
    result = np.full(red.shape, np.nan, dtype=np.float32)
    result[valid] = (nir_reflectance[valid] - red_reflectance[valid]) / denominator[valid]
    return result


def main():
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT} already exists. Move it aside before calculating a replacement.")
    manifest_bytes = (DATA / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    scenes = manifest["scenes"]
    if len(scenes) != 2 or date.fromisoformat(scenes[0]["date"]) >= date.fromisoformat(scenes[1]["date"]):
        raise ValueError("The dataset must contain two chronological scenes.")
    saved_grid = manifest["grid"]
    grid = {"crs": rasterio.crs.CRS.from_string(saved_grid["crs"]),
            "transform": Affine.from_gdal(*saved_grid["transform_gdal"]),
            "width": saved_grid["width_px"], "height": saved_grid["height_px"]}
    indices = []
    for scene in scenes:
        bands, calibration = {}, {}
        data_valid = np.ones((grid["height"], grid["width"]), dtype=bool)
        for name in ("red", "nir", "scl"):
            asset = scene["assets"][name]
            path = (DATA / asset["file"]).resolve()
            if not path.is_relative_to(DATA.resolve()):
                raise ValueError("Input band paths must stay inside the Doukkala data directory.")
            if sha256(path.read_bytes()).hexdigest() != manifest["sha256"][asset["file"]]:
                raise ValueError(f"Source checksum mismatch: {asset['file']}")
            with rasterio.open(path) as source:
                if (source.count != 1 or source.crs != grid["crs"] or source.transform != grid["transform"]
                        or source.shape != data_valid.shape or source.nodata != 0
                        or source.dtypes[0] != ("uint8" if name == "scl" else "uint16")):
                    raise ValueError(f"Input grid or band format mismatch: {asset['file']}")
                if name != "scl":
                    if (source.scales[0], source.offsets[0]) != (asset["scale"], asset["offset"]):
                        raise ValueError(f"Calibration metadata mismatch: {asset['file']}")
                    calibration[name + "_scale"] = source.scales[0]
                    calibration[name + "_offset"] = source.offsets[0]
                bands[name] = source.read(1)
                data_valid &= source.read_masks(1) > 0
        ndvi = calculate_ndvi(bands["red"], bands["nir"], bands["scl"], **calibration)
        ndvi[~data_valid] = np.nan
        indices.append(ndvi)

    # Use the intersection so both dates describe the same land pixels.
    common = np.isfinite(indices[0]) & np.isfinite(indices[1])
    valid_count = int(common.sum())
    if valid_count == 0:
        raise ValueError("There are no common valid land pixels for the two dates.")
    summary = {
        "formula": "NDVI = (NIR reflectance - red reflectance) / (NIR reflectance + red reflectance)",
        "mask_policy": "Keep SCL 4 (vegetation) and 5 (not vegetated) on both dates; require valid red/NIR/SCL masks, nonzero raw DNs, nonnegative calibrated reflectance, and a finite positive denominator.",
        "scope_note": "Common valid land in the fixed landscape crop, including nonvegetated surfaces; this is not a parcel or crop-type mask.",
        "input_manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "grid": saved_grid, "nodata": NODATA,
        "common_valid_pixels": valid_count, "excluded_pixels": int(common.size - valid_count),
        "scenes": [],
    }
    with TemporaryDirectory(prefix="ndvi-", dir=DATA) as temporary:
        staging = Path(temporary)
        with rasterio.open(staging / "common_valid_mask.tif", "w", driver="GTiff", **grid,
                           count=1, dtype="uint8", nodata=0, compress="deflate") as output:
            output.write(common.astype(np.uint8), 1)
        for scene, ndvi in zip(scenes, indices):
            values = ndvi[common].astype(np.float64)
            filename = scene["date"] + "_ndvi_10m.tif"
            summary["scenes"].append({"date": scene["date"], "file": filename,
                                      "valid_pixels_before_common_mask": int(np.isfinite(ndvi).sum()),
                                      "mean": float(values.mean()), "median": float(np.median(values)),
                                      "min": float(values.min()), "max": float(values.max())})
            ndvi[~common] = NODATA
            with rasterio.open(staging / filename, "w", driver="GTiff", **grid,
                               count=1, dtype="float32", nodata=NODATA, compress="deflate") as output:
                output.write(ndvi, 1)
                output.set_band_description(1, "NDVI")
        summary["sha256"] = {path.name: sha256(path.read_bytes()).hexdigest() for path in sorted(staging.glob("*.tif"))}
        (staging / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        staging.rename(OUTPUT)
    for scene in summary["scenes"]:
        print(f"{scene['date']}: mean NDVI {scene['mean']:.6f}, median {scene['median']:.6f}")
    print(f"Saved {valid_count:,} common valid pixels per date to {OUTPUT}")


if __name__ == "__main__":
    main()
