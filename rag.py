import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from google.genai import errors, types
import httpx2

from model import GeminiError, create_client


DATA_DIR = Path(__file__).parent / "demo_data" / "rag_documents"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072
INDEX_SETTINGS = {
    "model": EMBEDDING_MODEL,
    "dimensions": EMBEDDING_DIMENSIONS,
    "document_task_type": "RETRIEVAL_DOCUMENT",
}
MAX_INPUT_TOKENS = 2048
MAX_PASSAGE_CHARS = 1400


def split_paragraphs(text: str, max_chars: int = MAX_PASSAGE_CHARS) -> list[str]:
    """Group reviewed paragraphs, preserving their boundaries and complete text."""
    chunks = []
    current = ""
    for raw in text.split("\n\n"):
        paragraph = " ".join(raw.split())
        if not paragraph:
            continue
        if len(paragraph) > max_chars:
            raise ValueError("A reviewed paragraph is too long; split it at a meaningful boundary.")
        combined = f"{current}\n\n{paragraph}" if current else paragraph
        if len(combined) > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = combined
    if current:
        chunks.append(current)
    return chunks


def build_passages(review: dict, pages: list[dict], documents: list[dict]) -> list[dict]:
    page_lookup = {(page["source_id"], page["pdf_page"]): page for page in pages}
    source_lookup = {document["id"]: document for document in documents}
    passages = []
    seen = set()
    for reviewed in review["pages"]:
        key = (reviewed["source_id"], reviewed["pdf_page"])
        if key not in page_lookup or key[0] not in source_lookup:
            raise ValueError(f"Reviewed page is not in the recommended source pages: {key}")
        page, source = page_lookup[key], source_lookup[key[0]]
        page_hash = hashlib.sha256(page["text"].encode()).hexdigest()
        if reviewed["page_text_sha256"] != page_hash:
            raise ValueError(f"Extracted page changed; recheck its reviewed transcription: {key}")
        for section in reviewed["sections"]:
            chunks = split_paragraphs(section["text"])
            if not chunks or not section["heading"].strip():
                raise ValueError(f"Empty reviewed section on {key}")
            for text in chunks:
                digest = hashlib.sha256(text.encode()).hexdigest()
                passage_id = f"{key[0]}-p{key[1]:03d}-{digest[:12]}"
                if passage_id in seen:
                    raise ValueError(f"Duplicate passage: {passage_id}")
                seen.add(passage_id)
                embedding_text = f"{source['title']}\n{section['heading']}\n\n{text}"
                passages.append({
                    "passage_id": passage_id,
                    "source_id": key[0],
                    "pdf_page": key[1],
                    "citation": f"[{key[0]}, PDF p. {key[1]}]",
                    "title": source["title"],
                    "section": section["heading"],
                    "text": text,
                    "text_sha256": digest,
                    "embedding_text": embedding_text,
                    "embedding_sha256": hashlib.sha256(embedding_text.encode()).hexdigest(),
                    **{field: source[field] for field in (
                        "publication_year", "publication_date", "crops", "geographic_scope",
                        "language", "source_url", "pdf_file", "pdf_sha256", "use_note", "license", "license_url",
                    )},
                    "review_status": "selected_prose_verified_against_pdf",
                    "reviewed_on": review["reviewed_on"],
                    "review_note": reviewed["review_note"],
                    "page_text_sha256": page_hash,
                    "mean_ocr_word_confidence": page.get("mean_ocr_word_confidence"),
                    "numerical_tables_approved": False,
                })
    if not passages:
        raise ValueError("No reviewed passages were prepared.")
    return passages


def verify_token_limits(passages: list[dict], cached: list[dict]) -> tuple[list[dict], int]:
    previous = {passage["passage_id"]: passage for passage in cached}
    result = [dict(passage) for passage in passages]
    pending = []
    for passage in result:
        old = previous.get(passage["passage_id"], {})
        count = old.get("token_count")
        if (old.get("embedding_text") == passage["embedding_text"]
                and old.get("embedding_sha256") == passage["embedding_sha256"]
                and old.get("token_model") == EMBEDDING_MODEL
                and type(count) is int and 0 < count <= MAX_INPUT_TOKENS):
            passage.update(token_count=count, token_model=EMBEDDING_MODEL)
        else:
            pending.append(passage)
    if pending:
        # Count the exact future embedding payload; character length is not a token count.
        # https://googleapis.github.io/python-genai/#count-tokens-and-compute-tokens
        with create_client() as client:
            for passage in pending:
                count = client.models.count_tokens(model=EMBEDDING_MODEL, contents=passage["embedding_text"]).total_tokens
                if type(count) is not int or not 0 < count <= MAX_INPUT_TOKENS:
                    raise ValueError(f"Invalid or over-limit token count for {passage['passage_id']}; text was not truncated.")
                passage.update(token_count=count, token_model=EMBEDDING_MODEL)
    return result, len(pending)


def vector_norm(values: list[float]) -> float:
    if (not isinstance(values, list) or len(values) != EMBEDDING_DIMENSIONS
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in values)):
        raise GeminiError("Invalid embedding vector: expected 3,072 finite numbers. Rebuild the index if saved data changed.")
    norm = math.hypot(*values)
    if not math.isfinite(norm) or norm == 0:
        raise GeminiError("Invalid embedding vector: its length must be finite and nonzero.")
    return norm


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    """Embed checked passages, or count and embed one search query."""
    if (not texts or any(not text.strip() for text in texts)
            or task_type not in ("RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY")
            or (task_type == "RETRIEVAL_QUERY" and len(texts) != 1)):
        raise GeminiError("Provide nonempty embedding inputs and a supported retrieval task.")
    try:
        with create_client() as client:
            if task_type == "RETRIEVAL_QUERY":
                count = client.models.count_tokens(model=EMBEDDING_MODEL, contents=texts[0]).total_tokens
                if type(count) is not int or not 0 < count <= MAX_INPUT_TOKENS:
                    raise GeminiError("Search text exceeds the 2,048-token limit or its token count is invalid. Shorten it; no text was truncated.")
            # https://aistudio.google.com/docs/embeddings#supported-task-types
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIMENSIONS),
            )
    except errors.APIError as exc:
        if exc.code in (401, 403):
            message = "Gemini embeddings could not accept the API key. Check the key and project access."
        elif exc.code == 404:
            message = f"The embedding model {EMBEDDING_MODEL} is unavailable for this project."
        elif exc.code == 429:
            message = "Gemini embedding quota or rate limit reached. Wait before trying again."
        elif exc.code and (exc.code == 408 or exc.code >= 500):
            message = "Gemini embeddings are temporarily unavailable. Try again later."
        else:
            message = "Gemini rejected the embedding request. Check model access and input length."
        raise GeminiError(message) from None
    except httpx2.TimeoutException:
        raise GeminiError("The Gemini embedding request timed out after one automatic retry. Try again later.") from None
    except httpx2.TransportError:
        raise GeminiError("Could not connect to Gemini embeddings. Check your connection and try again.") from None

    if not response.embeddings or len(response.embeddings) != len(texts):
        raise GeminiError("Gemini returned an incomplete embedding batch; the index was not replaced.")
    vectors = []
    for embedding in response.embeddings:
        if embedding.statistics and embedding.statistics.truncated:
            raise GeminiError("Gemini reported truncated embedding input; the index was not replaced.")
        vector_norm(embedding.values)
        vectors.append(embedding.values)
    return vectors


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def atomic_write(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def prepared_passages(data_dir: Path) -> list[dict]:
    try:
        passages = read_jsonl(data_dir / "passages.jsonl")
        seen = set()
        for passage in passages:
            text, count = passage["embedding_text"], passage["token_count"]
            if (not text.strip() or hashlib.sha256(text.encode()).hexdigest() != passage["embedding_sha256"]
                    or passage["token_model"] != EMBEDDING_MODEL
                    or type(count) is not int or not 0 < count <= MAX_INPUT_TOKENS
                    or passage["passage_id"] in seen):
                raise ValueError("Invalid prepared passage")
            seen.add(passage["passage_id"])
        if not passages:
            raise ValueError("Empty corpus")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise GeminiError("Prepared passages are missing or invalid. Run python rag.py to rebuild and verify them first.") from None
    return passages


def read_embedding_index(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        index = json.loads(path.read_text())
        records = index["passages"]
        if (not isinstance(index["settings"], dict) or not isinstance(records, list)
                or any(not isinstance(record, dict) or not isinstance(record.get("passage_id"), str) for record in records)
                or len({record["passage_id"] for record in records}) != len(records)):
            raise ValueError("Invalid index format")
    except (OSError, ValueError, KeyError, TypeError):
        raise GeminiError("The saved embedding index is unreadable. Move it aside, then run python rag.py embed to rebuild it.") from None
    return index


def build_index(data_dir: Path = DATA_DIR) -> dict:
    """Reuse unchanged document vectors and replace the index only after success."""
    passages = prepared_passages(data_dir)
    path = data_dir / "embedding_index.json"
    cached = read_embedding_index(path)
    previous = {p["passage_id"]: p for p in cached["passages"]} if cached.get("settings") == INDEX_SETTINGS else {}
    vectors, pending = {}, []
    for passage in passages:
        old = previous.get(passage["passage_id"], {})
        if (old.get("embedding_sha256") == passage["embedding_sha256"]
                and old.get("embedding_text") == passage["embedding_text"]):
            vector_norm(old.get("vector"))
            vectors[passage["passage_id"]] = old["vector"]
        else:
            pending.append(passage)
    if pending:
        new_vectors = embed_texts([p["embedding_text"] for p in pending], "RETRIEVAL_DOCUMENT")
        for passage, values in zip(pending, new_vectors, strict=True):
            vectors[passage["passage_id"]] = values
    index = {"settings": INDEX_SETTINGS, "passages": [{**p, "vector": vectors[p["passage_id"]]} for p in passages]}
    atomic_write(path, json.dumps(index, ensure_ascii=False, allow_nan=False) + "\n")
    return {
        **INDEX_SETTINGS, "passage_count": len(passages), "new_vectors": len(pending),
        "reused_vectors": len(passages) - len(pending), "embedding_requests": int(bool(pending)),
    }


def load_index(data_dir: Path = DATA_DIR) -> list[dict]:
    passages = prepared_passages(data_dir)
    index = read_embedding_index(data_dir / "embedding_index.json")
    if index.get("settings") != INDEX_SETTINGS:
        raise GeminiError("The embedding index is missing or uses different settings. Run python rag.py embed first.")
    records = index["passages"]
    if [{k: v for k, v in record.items() if k != "vector"} for record in records] != passages:
        raise GeminiError("The embedding index is stale. Run python rag.py embed to refresh it before searching.")
    for record in records:
        vector_norm(record.get("vector"))
    return records


def cosine_similarity(left: list[float], right: list[float]) -> float:
    left_norm, right_norm = vector_norm(left), vector_norm(right)
    score = math.fsum((a / left_norm) * (b / right_norm) for a, b in zip(left, right, strict=True))
    return max(-1.0, min(1.0, score))


def semantic_search(question: str, context: str = "", top_k: int = 3, data_dir: Path = DATA_DIR) -> list[dict]:
    question, context = question.strip(), context.strip()
    if not question or len(question) > 2000 or len(context) > 4000:
        raise GeminiError("Provide a question of 1–2,000 characters and optional field context of at most 4,000 characters.")
    if type(top_k) is not int or top_k <= 0:
        raise GeminiError("The number of search results must be a positive integer.")
    records = load_index(data_dir)
    query = question + (f"\n\nField context (user-reported):\n{context}" if context else "")
    query_vector = embed_texts([query], "RETRIEVAL_QUERY")[0]
    # shortcut: rank all passages without a relevance cutoff; calibrate abstention with a broader query set before answer integration.
    results = [{**{k: v for k, v in record.items() if k != "vector"},
                "score": cosine_similarity(query_vector, record["vector"])} for record in records]
    return sorted(results, key=lambda result: (-result["score"], result["passage_id"]))[:top_k]


def prepare_corpus(data_dir: Path = DATA_DIR) -> dict:
    documents = json.loads((data_dir / "manifest.json").read_text())["documents"]
    for source in documents:
        pdf = (data_dir / source["pdf_file"]).resolve()
        if not pdf.is_relative_to((data_dir / "sources").resolve()):
            raise ValueError("Source PDF must stay inside the sources directory.")
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != source["pdf_sha256"]:
            raise ValueError(f"Original source PDF changed: {source['id']}")
    pages = read_jsonl(data_dir / "recommended_pages.jsonl")
    review = json.loads((data_dir / "reviewed_sections.json").read_text())
    passages = build_passages(review, pages, documents)
    output = data_dir / "passages.jsonl"
    cached = read_jsonl(output) if output.exists() else []
    passages, requests = verify_token_limits(passages, cached)
    selected = {(passage["source_id"], passage["pdf_page"]) for passage in passages}
    report = {
        "reviewed_on": review["reviewed_on"],
        "passage_count": len(passages),
        "reviewed_page_count": len(selected),
        "source_count": len({passage["source_id"] for passage in passages}),
        "token_model": EMBEDDING_MODEL,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "largest_passage_tokens": max(passage["token_count"] for passage in passages),
        "embedding_status": "Passage preparation only; see embedding_index.json for index state.",
        "pages": [{
            "source_id": page["source_id"], "pdf_page": page["pdf_page"],
            "status": "selected_prose_reviewed" if (page["source_id"], page["pdf_page"]) in selected else "not_reviewed_for_passages",
            "low_ocr_confidence": page.get("mean_ocr_word_confidence") is not None and page["mean_ocr_word_confidence"] < 85,
            "numerical_tables_require_review": True,
        } for page in pages],
    }
    atomic_write(output, "".join(json.dumps(passage, ensure_ascii=False) + "\n" for passage in passages))
    atomic_write(data_dir / "passage_review_report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {**{key: value for key, value in report.items() if key != "pages"}, "token_count_requests_this_run": requests}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare, embed, and search the reviewed agricultural passages.")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("prepare", help="Rebuild reviewed passages and verify token limits (the default).")
    commands.add_parser("embed", help="Create or refresh the cached document vectors.")
    search = commands.add_parser("search", help="Embed a question and return the closest passages.")
    search.add_argument("question")
    search.add_argument("--context", default="", help="Optional user-reported field context.")
    search.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    try:
        if args.command == "embed":
            output = build_index()
        elif args.command == "search":
            output = {
                "note": "Nearest passages only. Scores are not confidence; unrelated questions can also return results. Inspect source scope.",
                "results": semantic_search(args.question, args.context, args.top_k),
            }
        else:
            output = prepare_corpus()
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except GeminiError as exc:
        raise SystemExit(str(exc)) from None
    except (errors.APIError, httpx2.TransportError):
        raise SystemExit("Gemini token verification failed. Check the key, connection, and quota; existing outputs were not replaced.") from None
    except (OSError, ValueError) as exc:
        raise SystemExit(f"RAG data operation failed: {exc}") from None


if __name__ == "__main__":
    main()
