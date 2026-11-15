# /// script
# requires-python = ">=3.11"
# dependencies = ["Pillow==13.0.0"]
# ///
"""Render the saved class raster: uv run prepare_doukkala_change_view.py."""

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageColor


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "demo_data/doukkala_change"
OUTPUT = ROOT / "assets/doukkala-change"
CLASS_STYLES = {
    3: {"label": "Increased NDVI", "color": "#236440"},
    2: {"label": "Stable NDVI", "color": "#d9ded8"},
    1: {"label": "Decreased NDVI", "color": "#b15b3a"},
    0: {"label": "Excluded", "color": "#00000000"},
}


def colour_classes(source):
    if source.mode != "L":
        raise ValueError("The classification must be a single-band uint8 image.")
    codes = source.get_flattened_data()
    if set(codes) - CLASS_STYLES.keys():
        raise ValueError("The classification contains an unknown class code.")
    palette = {code: ImageColor.getcolor(style["color"], "RGBA") for code, style in CLASS_STYLES.items()}
    image = Image.new("RGBA", source.size)
    # Preserve the source pixel order without resampling: https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.putdata
    image.putdata([palette[code] for code in codes])
    return image


def main():
    if OUTPUT.exists():
        raise SystemExit(f"{OUTPUT} already exists. Move it aside before rendering a replacement.")
    case = json.loads((DATA / "case.json").read_text())
    summary_bytes = (DATA / "change/summary.json").read_bytes()
    summary = json.loads(summary_bytes)
    ndvi_digest = sha256((DATA / "ndvi/summary.json").read_bytes()).hexdigest()
    if (ndvi_digest != case["ndvi_summary_sha256"] or ndvi_digest != summary["input_ndvi_summary_sha256"]
            or [summary["before_date"], summary["after_date"]] != [row["date"] for row in case["images"]]):
        raise ValueError("The saved change results do not match the Doukkala NDVI case.")
    threshold = summary["threshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 < threshold <= 2:
        raise ValueError("The saved change threshold is invalid.")
    source_path = (DATA / "change" / summary["classification"]["file"]).resolve()
    if not source_path.is_relative_to((DATA / "change").resolve()):
        raise ValueError("The classification path must stay inside the change directory.")
    digest = sha256(source_path.read_bytes()).hexdigest()
    if digest != summary["sha256"][summary["classification"]["file"]]:
        raise ValueError("The saved classification checksum does not match.")
    with Image.open(source_path) as source:
        grid = summary["grid"]
        if source.size != (grid["width_px"], grid["height_px"]) or float(source.tag_v2[42113].strip("\x00")) != 0:
            raise ValueError("The classification dimensions or no-data code do not match.")
        counts = Counter(source.get_flattened_data())
        if (counts[0] != summary["excluded_pixels"]
                or sum(counts[code] for code in (1, 2, 3)) != summary["common_valid_pixels"]
                or any(counts[row["code"]] != row["pixel_count"] for row in summary["classes"])):
            raise ValueError("The classification counts do not match the saved summary.")
        image = colour_classes(source)
    rules = {3: f"Above +{threshold:g}", 2: f"−{threshold:g} to +{threshold:g}, inclusive",
             1: f"Below −{threshold:g}", 0: "Outside the shared valid sample"}
    metrics = {row["code"]: {key: row[key] for key in ("pixel_count", "area_ha", "percentage_of_valid")}
               for row in summary["classes"]}
    metrics[0] = {"pixel_count": summary["excluded_pixels"], "area_ha": summary["excluded_area_ha"]}
    metadata = {
        "url": "/assets/doukkala-change/change.png", "width": image.width, "height": image.height,
        "before_date": summary["before_date"], "after_date": summary["after_date"], "threshold": threshold,
        "common_valid_pixels": summary["common_valid_pixels"], "valid_area_ha": summary["valid_area_ha"],
        "legend": [{"code": code, **style, "rule": rules[code], **metrics[code]} for code, style in CLASS_STYLES.items()],
        "source_summary_sha256": sha256(summary_bytes).hexdigest(),
        "source_classification_sha256": digest, "source_ndvi_summary_sha256": ndvi_digest,
    }
    with TemporaryDirectory(prefix="doukkala-view-", dir=OUTPUT.parent) as temporary:
        staging = Path(temporary)
        image.save(staging / "change.png")
        metadata["image_sha256"] = sha256((staging / "change.png").read_bytes()).hexdigest()
        (staging / "view.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        staging.rename(OUTPUT)
    print(f"Saved the {image.width} × {image.height} colour view and legend to {OUTPUT}")


if __name__ == "__main__":
    main()
