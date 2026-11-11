from io import BytesIO
import hashlib
import warnings

from PIL import Image, ImageOps
import streamlit as st

import model


MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


def load_image(data: bytes) -> Image.Image:
    """Validate uploaded contents and return a decoded RGB preview in memory."""
    if not data:
        raise ValueError("The image file is empty. Choose a PNG or JPEG image.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("The image is too large. Choose a file of 10 MB or less.")

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


def main():
    st.set_page_config(page_title="Field notes | Morocco", page_icon="🌾", layout="centered")
    st.caption("MOROCCO · CROP IMAGERY DEMO")
    st.title("Field notes")
    st.write("Ask about the visible fields and what to check next.")
    st.caption("Preview assessment from your image and context. Agricultural document search comes later.")

    # The uploader reruns immediately so the preview does not wait for form submission.
    uploaded = st.file_uploader(
        "Satellite image",
        type=["png", "jpg", "jpeg"],
        max_upload_size=MAX_UPLOAD_MB,
        key="image",
        help="PNG or JPEG · Up to 10 MB and 16 million pixels. Use the PNGs in demo_data/sentinel2.",
    )
    image_feedback = st.empty()
    image_png = None
    if uploaded is not None:
        try:
            with load_image(uploaded.getvalue()) as image:
                st.image(image, caption=f"{image.width} × {image.height} pixels · RGB preview", width="stretch")
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_png = buffer.getvalue()
        except ValueError as exc:
            image_feedback.error(str(exc))
    else:
        st.info("Choose an image to see its preview here.")

    with st.form("field_question", clear_on_submit=False):
        st.header("Ask about the field")
        question = st.text_area(
            "Your question",
            key="question",
            height=100,
            max_chars=2000,
            placeholder="Why are some patches lighter than the surrounding fields?",
        )
        question_feedback = st.empty()
        context = st.text_area(
            "Field context (optional)",
            key="context",
            height=100,
            max_chars=4000,
            placeholder="Crop, region, image date, growth stage, and which field to look at.",
            help="Add what you know. Label invented demo details as synthetic.",
        )
        context_feedback = st.empty()
        st.caption("Selecting Ask Gemini sends your image, question, and context to Google Gemini.")
        submitted = st.form_submit_button("Ask Gemini", type="primary", width="stretch")

    request_signature = (
        hashlib.sha256(image_png).hexdigest() if image_png else None,
        question.strip(),
        context.strip(),
    )
    if st.session_state.get("answer", {}).get("inputs") != request_signature:
        st.session_state.pop("answer", None)

    if submitted:
        st.session_state.pop("answer", None)
        if uploaded is None:
            image_feedback.error("Choose a PNG or JPEG satellite image above.")
        question_valid = bool(question.strip()) and len(question) <= 2000
        if not question_valid:
            question_feedback.error("Enter a question using 1–2,000 characters, not just spaces.")
        context_valid = len(context) <= 4000
        if not context_valid:
            context_feedback.error("Shorten the field context to 4,000 characters or fewer.")
        if image_png is not None and question_valid and context_valid:
            try:
                with st.spinner("Gemini is reviewing your image…", show_time=True):
                    answer = model.answer_image(image_png, question.strip(), context.strip())
                st.session_state["answer"] = {"inputs": request_signature, "text": answer}
                st.success("Gemini response ready.")
            except model.GeminiError as exc:
                st.error(str(exc))

    if "answer" in st.session_state:
        st.header("Gemini response")
        st.caption("Based on your submitted image and context. Agricultural references have not been searched.")
        st.markdown(st.session_state["answer"]["text"])

    st.caption("RGB imagery shows visible patterns. Soil and nutrient conditions need field evidence.")


if __name__ == "__main__":
    main()
