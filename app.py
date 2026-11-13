from io import BytesIO
import base64
import hashlib
import json
import os
from pathlib import Path
import warnings

from PIL import Image, ImageOps
import streamlit as st

import model
import rag


ROOT = Path(__file__).resolve().parent
ON_VERCEL = os.environ.get("VERCEL") == "1"
MAX_UPLOAD_MB = 4 if ON_VERCEL else 10
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


def select_example():
    example = EXAMPLES.get(st.session_state["image_source"], {})
    st.session_state["question"] = example.get("question", "")
    st.session_state["context"] = example.get("context", "")
    st.session_state.pop("answer", None)


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


def preview_image(data: bytes, caption: str = "") -> bytes:
    with load_image(data) as image:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        # Inline media avoids a later image GET reaching a different Vercel instance.
        with image.copy() as thumbnail:
            thumbnail.thumbnail((1024, 1024))
            preview_buffer = BytesIO()
            thumbnail.save(preview_buffer, format="JPEG", quality=90)
        preview = "data:image/jpeg;base64," + base64.b64encode(preview_buffer.getvalue()).decode("ascii")
        st.image(preview, caption=caption or f"{image.width} × {image.height} pixels · RGB preview", width="stretch")
        return buffer.getvalue()


def main():
    st.set_page_config(page_title="GeoScan | Morocco", page_icon="🌾", layout="wide")
    pattern = base64.b64encode((ROOT / "assets/topography.svg").read_bytes()).decode("ascii")
    css = (ROOT / "assets/app.css").read_text().replace("TOPOGRAPHY_BASE64", pattern)
    st.html(f"<style>{css}</style>")
    st.caption("Moroccan agriculture demo")
    st.title("GeoScan")
    st.write("Moroccan crop and land analysis")
    if "image_source" not in st.session_state:
        st.session_state["image_source"] = next(iter(EXAMPLES))
        select_example()
    picker, locale = st.columns([2, 1], gap="large")
    with picker:
        source = st.selectbox(
            "Start with a field example, or upload your own",
            [*EXAMPLES, "Upload my own image"],
            key="image_source", on_change=select_example,
        )
    with locale:
        language = st.radio("Answer language", model.ANSWER_LANGUAGES, horizontal=True, key="language")
    comparison = EXAMPLES.get(source) if source == "Casablanca: Drought, 2023–2024" else None
    media, editor = (st.container(), st.container()) if comparison else st.columns([1, 1.1], gap="large")
    image_pngs, data = [], None
    with media:
        image_feedback = st.empty()
        if comparison:
            st.subheader(comparison["title"])
            try:
                for column, item in zip(st.columns(2, gap="medium"), comparison["images"]):
                    with column:
                        data = (ROOT / "demo_data/comparison" / item["file"]).read_bytes()
                        image_pngs.append(preview_image(data, f"{item['date']} · {item['platform']} / {item['instrument']}"))
            except (OSError, ValueError):
                image_pngs.clear()
                image_feedback.error("The comparison could not be loaded. Choose another example or try again later.")
            st.caption("372 days apart · Same Casablanca-region area · Regional RGB views, not individual parcel measurements.")
            st.caption(comparison["attribution"])
            with st.expander("About this comparison and its source"):
                st.write(comparison["reference"]["text"])
                st.write(comparison["reference"]["use_note"])
                st.markdown(f"[Read the NASA report]({comparison['source_url']})")
                st.caption("This report is included for this selected example, alongside up to two semantically retrieved agricultural excerpts.")
        elif source in EXAMPLES:
            st.subheader("The field")
            try:
                data = (ROOT / "demo_data/sentinel2" / EXAMPLES[source]["image"]).read_bytes()
            except OSError:
                image_feedback.error("This example image could not be loaded. Choose another example or upload an image.")
        else:
            uploaded = st.file_uploader(
                "Satellite image", type=["png", "jpg", "jpeg"],
                max_upload_size=MAX_UPLOAD_MB, key="image",
                help=f"PNG or JPEG. Up to {MAX_UPLOAD_MB} MB and 16 million pixels.",
            )
            data = uploaded.getvalue() if uploaded is not None else None
        if data is not None and not comparison:
            try:
                image_pngs.append(preview_image(data))
            except ValueError as exc:
                image_feedback.error(str(exc))
        elif data is None and not comparison:
            st.info("Choose a PNG or JPEG to preview the field.")
        if source in EXAMPLES and not comparison:
            st.caption("Real Sentinel-2 imagery, acquired 14 February 2025. Crop and soil details in the editable scenario are synthetic.")
        if not comparison:
            st.caption("Contains modified Copernicus Sentinel data 2025.")

    with editor:
        with st.form("field_question", clear_on_submit=False):
            st.header("Ask about the field")
            question = st.text_area(
                "Your question", key="question", height=100, max_chars=2000,
                placeholder="Why are some patches lighter than the surrounding fields?",
            )
            question_feedback = st.empty()
            context = st.text_area(
                "Field context (optional)", key="context", height=100, max_chars=4000,
                placeholder="Crop, region, image date, growth stage, and which field to look at.",
                help="Add what you know. Label invented demo details as synthetic.",
            )
            context_feedback = st.empty()
            st.caption("Image assessments send your image, question, context, and selected reference excerpts to Google Gemini.")
            submitted = st.form_submit_button("Ask Gemini", type="primary", width="stretch")

    request_signature = (
        tuple(hashlib.sha256(image).hexdigest() for image in image_pngs),
        hashlib.sha256(json.dumps(comparison, sort_keys=True).encode()).hexdigest() if comparison else None,
        question.strip(),
        context.strip(),
        language,
        model.PROMPT_VERSION,
    )
    if st.session_state.get("answer", {}).get("inputs") != request_signature:
        st.session_state.pop("answer", None)

    if submitted:
        st.session_state.pop("answer", None)
        if data is None and not comparison:
            image_feedback.error("Choose a field example or upload a PNG or JPEG satellite image.")
        question_valid = bool(question.strip()) and len(question) <= 2000
        if not question_valid:
            question_feedback.error("Enter a question using 1–2,000 characters, not just spaces.")
        context_valid = len(context) <= 4000
        if not context_valid:
            context_feedback.error("Shorten the field context to 4,000 characters or fewer.")
        if len(image_pngs) == (2 if comparison else 1) and question_valid and context_valid:
            try:
                answer = model.input_limit_notice(question, language)
                if answer is None:
                    with st.spinner("Finding agricultural references…", show_time=True):
                        if comparison:
                            passages = [comparison["reference"], *rag.semantic_search(question.strip(), context.strip(), top_k=2)[:2]]
                        else:
                            passages = rag.semantic_search(question.strip(), context.strip())
                    with st.spinner("Gemini is reviewing your images…" if comparison else "Gemini is reviewing your image…", show_time=True):
                        if comparison:
                            answer = model.answer_image(
                                image_pngs[0], question.strip(), context.strip(), passages, language=language,
                                comparison_image_png=image_pngs[1],
                                image_dates=tuple(item["date"] for item in comparison["images"]),
                            )
                        else:
                            answer = model.answer_image(image_pngs[0], question.strip(), context.strip(), passages, language=language)
                st.session_state["answer"] = {"inputs": request_signature, "field_context": context.strip(), **answer}
                if answer.get("kind") != "input_limit":
                    st.success("Gemini response ready.")
            except model.GeminiError as exc:
                st.error(str(exc))

    if "answer" in st.session_state:
        answer = st.session_state["answer"]
        st.header("Input limitation" if answer.get("kind") == "input_limit" else "Gemini response")
        if answer["evidence_status"] == "insufficient":
            st.info("No reference excerpt was cited. Review the assessment's stated evidence limits.")
        elif answer["evidence_status"] == "out_of_scope":
            st.info("This demo handles agricultural imagery, soils, crop nutrition, water, and field checks.")
        else:
            st.caption("Reported field context is unverified. References are background guidance; check their date, crops, and geographic scope.")
        if answer.get("kind") != "input_limit":
            reported_context = answer.get("field_context", context.strip())
            st.caption("Context supplied by you (unverified)")
            st.text(reported_context or "No field context supplied.", width="stretch")
        st.markdown(answer["text"])
        if answer["sources"]:
            st.subheader("References cited")
            for source in answer["sources"]:
                with st.expander(f"{source['citation']} · {source['section']}"):
                    st.write(source["title"])
                    year = source["publication_year"] if source["publication_year"] is not None else "unverified"
                    is_web = source.get("source_format") == "web"
                    st.caption(f"Published: {source['publication_date']}" if is_web else f"Publication year: {year} · Physical PDF page: {source['pdf_page']}")
                    st.caption("Crops covered: " + ", ".join(source["crops"]))
                    st.write(source["geographic_scope"])
                    st.write(source["use_note"])
                    st.markdown(f"[{'Open original report' if is_web else 'Open original PDF'}]({source['url']})")
                    st.caption("Excerpt supplied to Gemini")
                    st.write(source["text"])

    st.caption("RGB imagery shows visible patterns. Soil and nutrient conditions need field evidence.")


if __name__ == "__main__":
    main()
