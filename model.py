import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlsplit, urlunsplit

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
import httpx2


ENV_FILE = Path(__file__).with_name(".env")
MODEL_NAME = "gemini-3.5-flash-lite"
PROMPT_VERSION = "agronomy-rag-v6"
SYSTEM_PROMPT = (Path(__file__).parent / "prompts/agronomy_rag_v6.txt").read_text(encoding="utf-8")
ANSWER_LANGUAGES = ("English", "Français")
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "scope": {"type": "string", "enum": ["agricultural", "out_of_scope"]},
        "answer": {"type": "string", "description": "Final assessment in the application's explicitly configured answer language, including headings.", "minLength": 1, "maxLength": 8000},
    },
    "required": ["scope", "answer"],
    "additionalProperties": False,
}


class GeminiError(RuntimeError):
    """A safe, actionable message that the interface can display."""


def input_limit_notice(question: str, language: str) -> dict | None:
    if language not in ANSWER_LANGUAGES:
        raise GeminiError("Choose English or Français as the answer language.")
    # shortcut: recognizes explicit English/French NDVI calculations; add typed band inputs before supporting spectral analyses.
    if not re.search(r"^(?:please\s+)?(?:(?:can|could) you\s+|peux[- ]tu\s+|pouvez[- ]vous\s+)?(?:calculate|compute|calcule[rz]?)\b.*\bNDVI\b", question.strip(), re.IGNORECASE | re.DOTALL):
        return None
    text = (
        "This form receives RGB imagery, without identified red and near-infrared measurement bands. "
        "An exact NDVI cannot be calculated from this upload. No index was computed.\n\n"
        "Use an appropriate multispectral product and identify the target parcel before attempting that calculation."
        if language == "English" else
        "Cette interface reçoit une image RVB, sans bandes de mesure rouge et proche infrarouge identifiées. "
        "Il est impossible de calculer un NDVI exact à partir de cet envoi. Aucun indice n'a été calculé.\n\n"
        "Utilisez un produit multispectral adapté et identifiez la parcelle cible avant de tenter ce calcul."
    )
    return {"text": text, "evidence_status": "insufficient", "sources": [], "kind": "input_limit"}


def reference_context(passages: list[dict]) -> list[dict]:
    """Give the model bounded excerpts and provenance, without vectors or scores."""
    if len(passages) > 3:
        raise GeminiError("Provide at most three retrieved passages for this demo.")
    fields = ("source_id", "pdf_page", "title", "section", "text", "publication_year",
              "publication_date", "crops", "geographic_scope", "use_note", "numerical_tables_approved")
    try:
        return [{"reference": f"S{index}", **{field: passage[field] for field in fields}}
                for index, passage in enumerate(passages, 1)]
    except (KeyError, TypeError):
        raise GeminiError("Retrieved source metadata is incomplete. Rebuild the passages and index.") from None


def parse_grounded_answer(raw: str, passages: list[dict]) -> dict:
    try:
        data = json.loads(raw)
        if (not isinstance(data, dict) or set(data) != {"scope", "answer"}
                or data["scope"] not in ("agricultural", "out_of_scope")
                or not isinstance(data["answer"], str) or not 0 < len(data["answer"].strip()) <= 8000):
            raise ValueError("Invalid answer shape")
    except (ValueError, TypeError):
        raise GeminiError("Gemini returned an invalid evidence response. Try again with a clearer question.") from None
    answer = data["answer"].strip()
    if re.search(r"[a-z][a-z0-9+.-]*://|mailto:|www\.|!\[|\]\(|<[A-Za-z/!][^>]*>|```", answer, re.IGNORECASE):
        raise GeminiError("Gemini returned an unsupported link or output format. No answer was shown; try again.")
    labels = re.findall(r"\[[^\[\]\n]*\]", answer)
    allowed = {f"[S{index}]": passage for index, passage in enumerate(passages, 1)}
    remainder = re.sub(r"\[[^\[\]\n]*\]", "", answer)
    if (any(label not in allowed for label in labels) or "[" in remainder or "]" in remainder
            or re.search(r"\bMA_[A-Z0-9_]+\b", remainder)):
        raise GeminiError("Gemini cited a reference that was not supplied in the required format. No answer was shown; try again.")
    if data["scope"] == "out_of_scope" and labels:
        raise GeminiError("Gemini attached agricultural citations to an unrelated question. No answer was shown; try again.")
    sources, links = [], {}
    for label in dict.fromkeys(labels):
        passage = allowed[label]
        try:
            source_id, page = passage["source_id"], passage["pdf_page"]
            url = urlsplit(passage["source_url"])
            if (not re.fullmatch(r"MA_[A-Z0-9_]+", source_id)
                    or type(page) is not int or page <= 0 or url.scheme != "https" or not url.hostname):
                raise ValueError("Invalid citation metadata")
            citation = f"[{source_id}, PDF p. {page}]"
            target = quote(urlunsplit(url._replace(fragment=f"page={page}")), safe=":/?&=%#@+-._~")
        except (KeyError, TypeError, ValueError):
            raise GeminiError("Retrieved citation metadata is invalid. Rebuild the passages and index.") from None
        sources.append({**passage, "citation": citation, "url": target})
        links[label] = f"{citation}({target})"
    for label, link in links.items():
        answer = answer.replace(label, link)
    status = "out_of_scope" if data["scope"] == "out_of_scope" else ("used" if sources else "insufficient")
    return {"text": answer, "evidence_status": status, "sources": sources}


def get_api_key() -> str:
    # Load only this project's file; existing server environment variables take precedence.
    load_dotenv(ENV_FILE, override=False)
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError("Set GEMINI_API_KEY in the project's .env file, then restart the app.")
    return key


def create_client() -> genai.Client:
    return genai.Client(
        enterprise=False,
        api_key=get_api_key(),
        http_options=types.HttpOptions(
            base_url="https://generativelanguage.googleapis.com",
            api_version="v1beta",
            timeout=60_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def answer_image(image_png: bytes, question: str, context: str = "", passages: list[dict] | None = None, language: str = "English") -> dict:
    """Send an RGB PNG and selected excerpts; return a citation-checked assessment."""
    if not image_png or len(image_png) > 10 * 1024 * 1024:
        raise GeminiError("Image is too large after preparation. Export a smaller crop and try again.")
    question, context = question.strip(), context.strip()
    if not question or len(question) > 2000 or len(context) > 4000:
        raise GeminiError("Provide a question of 1–2,000 characters and field context of at most 4,000 characters.")
    notice = input_limit_notice(question, language)
    if notice is not None:
        return notice
    passages = passages or []
    references = reference_context(passages)

    # SDK image parts and client lifetime: https://googleapis.github.io/python-genai/
    try:
        with create_client() as client:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=types.Content(role="user", parts=[
                    types.Part.from_bytes(data=image_png, mime_type="image/png"),
                    types.Part.from_text(text=json.dumps({
                        "references": references,
                        "field_context": context,
                        "answer_language": language,
                        "question": question,
                    }, ensure_ascii=False)),
                ]),
                config=types.GenerateContentConfig(
                    system_instruction=f"{SYSTEM_PROMPT}\nConfigured answer language: {language}. Write every sentence and heading in {language}.",
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                    response_json_schema=ANSWER_SCHEMA,
                ),
            )
    except errors.APIError as exc:
        if exc.code in (401, 403):
            message = "Gemini could not accept the API key. Check the key and project access."
        elif exc.code == 404:
            message = f"The model {MODEL_NAME} is unavailable for this project. Check model access."
        elif exc.code == 429:
            message = "Gemini's quota or rate limit was reached. Wait before trying again."
        elif exc.code and exc.code >= 500:
            message = f"Gemini is temporarily unavailable (HTTP {exc.code}). Try again later."
        else:
            message = "Gemini rejected the request. Check the API key and try a smaller image or shorter question."
        raise GeminiError(message) from None
    except httpx2.TimeoutException:
        raise GeminiError("The Gemini request timed out. Try again or use a smaller image.") from None
    except httpx2.TransportError:
        raise GeminiError("Could not connect to Gemini. Check your connection and try again.") from None

    if not response.candidates or response.candidates[0].finish_reason != types.FinishReason.STOP:
        raise GeminiError("Gemini did not return a complete answer. Try a shorter or clearer question.")
    content = response.candidates[0].content
    parts = content.parts if content and content.parts else []
    answer = "".join(part.text for part in parts if part.text and not part.thought).strip()
    if not answer:
        raise GeminiError("Gemini returned no answer. Try again with a clearer question.")
    return parse_grounded_answer(answer, passages)
