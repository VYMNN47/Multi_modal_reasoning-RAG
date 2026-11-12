# Step 3: Prepare agricultural passages

We now have a small, reviewed text corpus for the next step: **16 passages from
selected prose on 10 physical PDF pages across eight documents**. No embeddings,
search index, document-backed answers, or UI changes were added here.

This page describes the step 3 checkpoint. [Step 4](step4.md) now adds the
embeddings and independent search; the preparation process below still applies.

## 1. Start with extracted pages, then check the source

The original collection contains eight PDFs, 125 extracted/OCRed pages, and 50
recommended pages. A recommended page is a candidate for review, not an approved
embedding input. We selected prose relevant to the three demonstration scenarios
and compared it with rendered PDF pages.

This matters because extraction can produce believable but incorrect text. In
the Doukkala bulletin, parts of the two-column layout were interleaved. The
reviewed excerpt restores the reading order after comparison with the PDF.
Wrapped words and spacing were corrected in separate reviewed text; the source
PDFs, full OCR, and original page records were preserved.

`demo_data/rag_documents/reviewed_sections.json` records those selected excerpts,
their source/page, editorial section labels, review notes, and the SHA-256 hash
of the extracted page used during review. Changed extracted text is rejected
until that review is revisited. The preparation command also checks all eight
PDF hashes against the original download manifest.

**Learn:** Extraction and review are separate jobs. A confident OCR result is not
proof that reading order, numbers, units, or agricultural claims are correct.

## 2. Make each passage a coherent unit

`split_paragraphs()` in `rag.py` joins ordinary line wrapping, preserves paragraph
boundaries, and groups adjacent paragraphs up to 1,400 characters. It rejects an
individual paragraph that exceeds that boundary, asking us to divide it at a
meaningful point. It never cuts off the end of a paragraph.

For this first set, the reviewed sections are already short: each becomes one
passage, with no overlap. We deliberately selected complete sentences and
related paragraphs rather than slicing entire noisy pages into fixed windows.
Larger or automatically extracted collections may need a different strategy;
we have not measured retrieval quality yet.

**Learn:** A chunk is the unit we will search and pass to the model as evidence.
An entire PDF can mix many topics and exceed the embedding input limit; a tiny
fragment can lose qualifications and context.

## 3. Keep provenance attached

Every generated passage carries:

- A stable `passage_id`, `source_id`, document title, and physical `pdf_page`.
- Publication date/year, language, crop and geographic scope.
- Source URL, local PDF path, original PDF hash, license metadata, and use limits.
- The reviewed text, review date/note, and a source-page hash.
- The exact `embedding_text`, its hash, model-specific token count, and token model.

Physical PDF pages can differ from printed labels. For example, cereal PDF page
14 is printed page 11. Citations use physical pages, such as
`[MA_INRA_CEREALS, PDF p. 14]`, so they can be checked consistently.

The legume guide's publication year remains `null`; its filename is not evidence
of a date. Doukkala's historical regional scope and the national soil-map paper's
limitations remain attached. No field-specific soil measurement has been created.

**Learn:** Text without its source, date, and scope is easy to misuse. Source
comparison verifies the excerpt's wording, not its current agronomic validity.

## 4. Distinguish IDs, tokens, and embeddings

A passage ID uses its source, page, and a short content hash. Adding another
passage does not renumber the existing ones. This will help reuse unchanged
vectors later. Hashing identifies exact content; it does not measure meaning.

`embedding_text` combines the document title, editorial section heading, and
passage text. This adds context to otherwise generic paragraphs. Its hash
changes if any part of that embedding input changes.

A token is a piece of text used by a model's tokenizer. Character count is only
a passage-boundary control. We called `count_tokens` with `gemini-embedding-001`
on every exact embedding input: the largest measured input was **218 tokens**,
below the model's **2,048-token** limit. A bad or excessive count aborts preparation
instead of silently truncating content.

Unchanged counts are saved with the input hash/text and model ID, so rebuilding
the current corpus needs no API call. **Step 4 must embed `embedding_text`
unchanged.** A new prefix, title, or text requires a new token check.

**Learn:** Counting tokens uses the tokenizer. Creating an embedding produces a
semantic vector. We have done the former, not the latter.

## 5. Keep unreviewed material visible

`passage_review_report.json` covers all 50 recommended pages. Ten have selected
prose reviewed; 40 have no approved passages yet. Three recommended cereal pages
(PDF 7, 11, 12) retain low-OCR flags. The other 75 non-recommended pages are also
outside this first passage set.

Numerical tables, fertilizer-rate examples, and calculation formulas were
excluded. The numerical-table flag means such material is not approved for use;
it is not an automatic detector claiming every page contains a table. Elemental
nutrients, oxide notation, and kilograms of product must not be conflated.

## 6. Check coverage before retrieval exists

`tests/rag_review_cases.json` links the three agreed scenarios to reviewed
passages and physical source pages:

| Scenario | Prepared evidence |
| --- | --- |
| Reported wheat with lighter patches | Historical field symptoms, soil tests, nitrogen budgets, regional references |
| User-reported calcareous soil | Phosphorus availability and soil-test interpretation context |
| Uneven growth in irrigated Doukkala | Water-management context and the regional study's scope |

Each case includes an English and French question. Tests verify that the expected
passages and references exist. These are coverage checks, not measured semantic
retrieval scores; searching and evaluating those results come in step 4.

## 7. Run and inspect it

From the project directory:

```bash
source .venv/bin/activate
python rag.py
python -m unittest discover -s tests -v
```

The first command rebuilds `passages.jsonl` and `passage_review_report.json`.
For the checked-in, unchanged data it reuses the verified counts and reports
`token_count_requests_this_run: 0`. New/changed inputs require the existing
server-side Gemini key and network access for token counting. No embedding call
or image-generation call is made by this command.

All token checks finish before output files are replaced. A failed check keeps
the existing corpus. The build uses the shared `create_client()` helper from
`model.py`; the vision call retains the same client configuration and behavior.

To inspect a complete record:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("demo_data/rag_documents/passages.jsonl")
passage = json.loads(path.read_text().splitlines()[0])
print(json.dumps(passage, ensure_ascii=False, indent=2))
PY
```

**Teach-back:** Why keep both reviewed text and the original extraction? Why does
every passage need a physical page reference? What is the difference between a
character limit, a token count, a hash, and an embedding?

## Sources and verification

- [Embedding model and input limit](https://aistudio.google.com/docs/models/gemini-embedding-001)
- [Token-counting API](https://aistudio.google.com/api-reference/tokens)
- [SDK token counting](https://googleapis.github.io/python-genai/#count-tokens-and-compute-tokens)
- [Source collection and reuse notes](../demo_data/rag_documents/README.md)
- [Step 3 verification](step3_verification.md)

Next: step 4 creates passage vectors with `gemini-embedding-001` and searches
them with embedded questions. The app still answers directly from image/text
until the retrieval-to-generation connection is added in step 5.
