from io import BytesIO
from hashlib import sha256
import json
from pathlib import Path
import warnings

from PIL import Image, ImageOps

import model
import rag

ROOT = Path(__file__).resolve().parent
MAX_UPLOAD_MB = 4
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000

EXAMPLES = {
    "Gharb: Wheat and nitrogen": {
        "image": "gharb_2025-02-14_rgb_10m.png",
        "question": "What field observations and nitrogen or soil evidence should we check before attributing lighter wheat patches to nitrogen deficiency?",
        "context": "Synthetic demo context: the user reports wheat in the central field in Gharb. Crop identity, growth stage, and soil conditions are unverified.",
    },
    "Tadla: Soil and phosphorus": {
        "image": "tadla_2025-02-14_rgb_10m.png",
        "question": "What could affect phosphorus availability in calcareous soil, and what soil-test context is needed before changing fertilizer?",
        "context": "Synthetic demo context: a user-provided soil report describes the central field in Tadla as calcareous. We have no actual laboratory results.",
    },
    "Doukkala: Water and uneven growth": {
        "image": "doukkala_2025-02-14_rgb_10m.png",
        "question": "What soil, irrigation, and management evidence should we check before changing fertilizer in an irrigated field with uneven growth in Doukkala?",
        "context": "Synthetic demo context: the user reports an irrigated wheat field in the center of the Doukkala image with uneven growth. Crop identity and irrigation status are unverified.",
    },
}
COMPARISON = json.loads((ROOT / "demo_data/comparison/case.json").read_text(encoding="utf-8"))
EXAMPLES["Casablanca: Drought, 2023–2024"] = COMPARISON
NDVI_EXAMPLE = json.loads((ROOT / "demo_data/doukkala_change/case.json").read_text(encoding="utf-8"))
EXAMPLES["Doukkala: NDVI, 2024–2025"] = NDVI_EXAMPLE


def load_ndvi_results(example: dict) -> dict:
    try:
        contents = (ROOT / example["ndvi_summary_file"]).read_bytes()
        if sha256(contents).hexdigest() != example["ndvi_summary_sha256"]:
            raise ValueError("NDVI summary checksum mismatch")
        dates = tuple(item["date"] for item in example["images"])
        return model.ndvi_context(json.loads(contents), dates)
    except (OSError, KeyError, TypeError, ValueError):
        raise model.GeminiError("The saved NDVI results could not be verified. Contact the project author.") from None


def load_image(data: bytes) -> Image.Image:
    """Validate uploaded contents and return a decoded RGB preview in memory."""
    if not data:
        raise ValueError("The image file is empty. Choose a PNG or JPEG image.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"The image is too large. Choose a file of {MAX_UPLOAD_MB} MB or less.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data), formats=("PNG", "JPEG")) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("The image exceeds 16 million pixels. Export a smaller crop.")
                if getattr(image, "is_animated", False):
                    raise ValueError("Choose a single-frame PNG or JPEG image.")
                image.verify()

            # verify() checks structure; reopening and decoding catches incomplete pixel data.
            with Image.open(BytesIO(data), formats=("PNG", "JPEG")) as image:
                preview = ImageOps.exif_transpose(image).convert("RGB")
                preview.info.clear()
                return preview
    except (OSError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError("This file could not be read. Export a complete PNG or JPEG image and try again.") from exc


EXAMPLE_FILES = {}
for example in EXAMPLES.values():
    if "images" in example:
        for item in example["images"]:
            EXAMPLE_FILES[item["file"]] = ROOT / item["path"] if "path" in item else ROOT / "demo_data/comparison" / item["file"]
    else:
        EXAMPLE_FILES[example["image"]] = ROOT / "demo_data/sentinel2" / example["image"]


def example_catalog() -> list[dict]:
    result = []
    for label, example in EXAMPLES.items():
        paired = "images" in example
        images = example["images"] if paired else [{"file": example["image"]}]
        result.append({
            "id": label, "label": label, "question": example["question"], "context": example["context"],
            "images": [{"url": "/api/example-images/" + item["file"],
                        "caption": f"{item['date']} · {item['platform']} / {item['instrument']}" if paired else "Sentinel-2 · 14 February 2025"}
                       for item in images],
            "attribution": example["attribution"] if paired else "Contains modified Copernicus Sentinel data 2025. Crop and soil scenario details are synthetic.",
            "description": example["reference"]["use_note"] if paired else "Real satellite imagery with editable, synthetic demo context.",
            "source_url": example.get("source_url"),
        })
        if "ndvi_summary_file" in example:
            result[-1]["ndvi_results"] = load_ndvi_results(example)
    return result


def prepare_images(images: list[bytes]) -> list[bytes]:
    if not 1 <= len(images) <= 2:
        raise ValueError("Choose one or two PNG/JPEG images.")
    if sum(len(data) for data in images) > MAX_UPLOAD_BYTES:
        raise ValueError("Choose images totaling 4 MB or less.")
    prepared = []
    for data in images:
        with load_image(data) as image:
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            prepared.append(buffer.getvalue())
    if sum(map(len, prepared)) > model.MAX_IMAGE_BYTES:
        raise ValueError("The images are too large after preparation. Export smaller crops and try again.")
    return prepared


def assess(question: str, context: str, language: str, case: str, uploads: list[bytes]) -> dict:
    if not question.strip() or len(question) > 2000 or len(context) > 4000:
        raise ValueError("Enter a question of 1–2,000 characters and context of at most 4,000 characters.")
    if language not in model.ANSWER_LANGUAGES:
        raise ValueError("Choose English or Français as the answer language.")
    if case != "upload" and case not in EXAMPLES:
        raise ValueError("Choose an available example or upload your own images.")
    example = EXAMPLES.get(case)
    if example and uploads:
        raise ValueError("Choose an example or your own uploads for this assessment.")
    if example:
        items = example["images"] if "images" in example else [{"file": example["image"]}]
        images = [EXAMPLE_FILES[item["file"]].read_bytes() for item in items]
    else:
        images = uploads
    prepared = prepare_images(images)
    question, context = question.strip(), context.strip()
    ndvi_results = load_ndvi_results(example) if example and "ndvi_summary_file" in example else None
    answer = model.input_limit_notice(question, language) if ndvi_results is None else None
    if answer is None:
        dated = example is not None and "images" in example
        if ndvi_results is not None:
            passages = [example["reference"]]
        elif dated:
            passages = [example["reference"], *rag.semantic_search(question, context, top_k=2)[:2]]
        else:
            passages = rag.semantic_search(question, context)
        options = {"language": language}
        if len(prepared) == 2:
            options["comparison_image_png"] = prepared[1]
        if dated:
            options["image_dates"] = tuple(item["date"] for item in example["images"])
        if ndvi_results is not None:
            options["ndvi_results"] = ndvi_results
        answer = model.answer_image(prepared[0], question, context, passages, **options)
    fields = ("citation", "title", "section", "url", "text", "publication_year", "publication_date",
              "source_format", "pdf_page", "crops", "geographic_scope", "use_note")
    result = {**answer, "field_context": context,
              "sources": [{key: source.get(key) for key in fields} for source in answer["sources"]]}
    if ndvi_results is not None:
        result["ndvi_results"] = ndvi_results
    return result
