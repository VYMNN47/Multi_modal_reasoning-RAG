# /// script
# requires-python = ">=3.11"
# dependencies = ["rasterio==1.4.4", "Pillow==13.0.0"]
# ///
"""Download the two pinned Doukkala scenes: uv run prepare_doukkala.py."""

from datetime import UTC, date, datetime
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "demo_data/doukkala_change"
COLLECTION = "sentinel-2-c1-l2a"
CATALOG = "https://earth-search.aws.element84.com/v1/collections/" + COLLECTION + "/items/"
ASSET_PREFIX = "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/sentinel-2-c1-l2a/29/S/NS/"
SCENES = ("S2B_T29SNS_20240220T111943_L2A", "S2B_T29SNS_20250214T111323_L2A")
FILENAMES = {"red": "B04_10m.tif", "nir": "B08_10m.tif", "scl": "SCL_10m.tif", "visual": "rgb.png"}


def crop_asset(asset, key, path, grid):
    if not asset["href"].startswith(ASSET_PREFIX):
        raise ValueError("Unexpected source asset URL.")
    with rasterio.open(asset["href"]) as source:
        if source.crs != grid["crs"]:
            raise ValueError("The source is outside the expected UTM grid.")
        if key != "scl":
            window = source.window(*rasterio.transform.array_bounds(grid["height"], grid["width"], grid["transform"]))
            if source.res != (10, 10) or any(abs(value - round(value)) > 1e-6 for value in window.flatten()):
                raise ValueError("The 10 m source pixels do not align with the existing crop.")
        # SCL has 20 m cells; nearest-neighbour alignment preserves its class labels.
        with WarpedVRT(source, **grid, resampling=Resampling.nearest) as aligned:
            pixels = aligned.read()
        if key == "visual":
            Image.fromarray(np.moveaxis(pixels, 0, -1)).save(path)
        else:
            metadata = asset["raster:bands"][0]
            with rasterio.open(path, "w", driver="GTiff", **grid, count=1, dtype=pixels.dtype,
                               nodata=metadata["nodata"], compress="deflate") as output:
                output.write(pixels)
                output.scales = (metadata.get("scale", 1),)
                output.offsets = (metadata.get("offset", 0),)
        return pixels


def main():
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT} already exists. Move it aside before preparing a replacement.")
    tiles = json.loads((ROOT / "demo_data/sentinel2/manifest.json").read_text())["tiles"]
    original = next(tile for tile in tiles if tile["name"] == "doukkala")
    with rasterio.open(ROOT / "demo_data/sentinel2" / original["geotiff_file"]) as reference:
        grid = {"crs": reference.crs, "transform": reference.transform, "width": reference.width, "height": reference.height}
        manifest = {
            "region": "Doukkala / Sidi Bennour vicinity, Morocco",
            "collection": COLLECTION,
            "downloaded_at_utc": datetime.now(UTC).isoformat(),
            "grid": {"crs": str(reference.crs), "transform_gdal": list(reference.transform.to_gdal()),
                     "width_px": reference.width, "height_px": reference.height,
                     "bounds_utm_west_south_east_north": list(reference.bounds),
                     "bbox_wgs84_west_south_east_north": original["bbox_wgs84_west_south_east_north"]},
            "selection_reason": "Same Sentinel-2B satellite, tile 29SNS and relative orbit R137; comparable February dates. The 2024-02-20 scene has low scene cloud cover and no crop SCL cloud/shadow/cirrus flags.",
            "storage_note": "B04 and B08 retain uint16 source digital numbers. Apply each stored scale and offset once to valid pixels before NDVI; zero is nodata. RGB is for display only.",
            "scl_note": "Native 20 m SCL aligned to the reference 10 m grid with nearest-neighbour sampling; this does not add spatial detail. No class masking has been applied to the spectral bands.",
            "attribution": "Contains modified Copernicus Sentinel data 2024 and 2025",
            "scenes": [],
        }

    # Publish only after both complete scenes have downloaded and passed checks.
    with TemporaryDirectory(prefix="doukkala-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary)
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_TIMEOUT=30):
            for scene_id in SCENES:
                with urlopen(CATALOG + scene_id, timeout=30) as response:
                    item = json.load(response)
                if item["id"] != scene_id or item["collection"] != COLLECTION:
                    raise ValueError("Unexpected catalog scene.")
                properties = item["properties"]
                acquired = date.fromisoformat(properties["datetime"][:10]).isoformat()
                if properties["platform"] != "sentinel-2b" or acquired.replace("-", "") != scene_id.split("_")[2][:8]:
                    raise ValueError("Unexpected acquisition date or satellite.")
                folder = staging / acquired
                folder.mkdir()
                (folder / "source.stac.json").write_text(json.dumps(item, indent=2) + "\n")
                metadata_url = item["assets"]["product_metadata"]["href"]
                if not metadata_url.startswith(ASSET_PREFIX):
                    raise ValueError("Unexpected calibration metadata URL.")
                with urlopen(metadata_url, timeout=30) as response:
                    xml = response.read()
                (folder / "product_metadata.xml").write_bytes(xml)
                elements = list(ET.fromstring(xml).iter())
                quantification = float(next(e.text for e in elements if e.tag.rsplit("}", 1)[-1] == "BOA_QUANTIFICATION_VALUE"))
                offsets = {int(e.attrib["band_id"]): float(e.text) for e in elements if e.tag.rsplit("}", 1)[-1] == "BOA_ADD_OFFSET"}
                for key, band_id in (("red", 3), ("nir", 7)):
                    calibration = item["assets"][key]["raster:bands"][0]
                    if (calibration["scale"], calibration["offset"]) != (1 / quantification, offsets[band_id] / quantification):
                        raise ValueError("STAC and product XML disagree on reflectance calibration.")
                scene = {"date": acquired, "acquired_utc": properties["datetime"], "source_scene_id": scene_id,
                         "source_catalog_item": CATALOG + scene_id, "platform": properties["platform"],
                         "source_product_uri": properties["s2:product_uri"], "processing_baseline": properties["s2:processing_baseline"],
                         "source_stac_file": acquired + "/source.stac.json", "product_metadata_file": acquired + "/product_metadata.xml",
                         "whole_source_scene_cloud_cover_percent": properties["eo:cloud_cover"], "assets": {}}
                for key, filename in FILENAMES.items():
                    asset = item["assets"][key]
                    print(f"{acquired}: downloading {key}", flush=True)
                    pixels = crop_asset(asset, key, folder / filename, grid)
                    details = {"file": acquired + "/" + filename, "source_url": asset["href"], "source_resolution_m": 20 if key == "scl" else 10}
                    if key in ("red", "nir"):
                        details.update({name: asset["raster:bands"][0][name] for name in ("scale", "offset", "nodata", "data_type")})
                        if pixels.dtype != np.uint16 or pixels.shape != (1, 512, 512):
                            raise ValueError("Unexpected analytical band format.")
                    if key == "scl":
                        labels, counts = np.unique(pixels, return_counts=True)
                        scene["scl_class_counts_10m"] = {str(int(label)): int(count) for label, count in zip(labels, counts)}
                        scene["crop_cloud_shadow_cirrus_percent"] = float(np.isin(pixels, [3, 8, 9, 10]).mean() * 100)
                    scene["assets"]["rgb" if key == "visual" else key] = details
                manifest["scenes"].append(scene)

        manifest["interval_days"] = (date.fromisoformat(manifest["scenes"][1]["date"]) - date.fromisoformat(manifest["scenes"][0]["date"])).days
        manifest["sha256"] = {path.relative_to(staging).as_posix(): sha256(path.read_bytes()).hexdigest()
                              for path in sorted(staging.rglob("*")) if path.is_file()}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        staging.rename(OUTPUT)
    print(f"Saved the two-date data package to {OUTPUT}")


if __name__ == "__main__":
    main()
