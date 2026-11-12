# Moroccan Multimodal RAG Portfolio: Project Plan

Status: steps 1–5 implemented and verified; streaming is the next step.
Created: 2026-11-10. Task status is tracked in [todo.md](todo.md).

## Goal

Build a small Streamlit demo where a user uploads a satellite RGB image,
adds a question and optional field context, and receives a conditional
agronomic assessment supported by retrieved Moroccan agricultural references.
The interface shows real application progress and a brief evidence summary,
followed by the final answer and source citations.

## What already exists

- Three real Sentinel-2 image crops with provenance, georeferencing, and ZIP:
  `demo_data/sentinel2/`.
- Eight original agricultural PDFs: seven French and one English, 125 pages.
- Extracted/OCR text, source metadata, and 50 recommended starting pages:
  `demo_data/rag_documents/`.
- A versioned grounded system prompt in `prompts/`, loaded by `model.py`.
- A working local upload form and Gemini image-to-answer path, with focused tests
  and step-by-step learning notes.
- 16 reviewed passages from 10 physical PDF pages across eight sources, with
  citations, source scope, stable IDs, and exact embedding-input token checks.
- A saved `gemini-embedding-001` index of those 16 passages and a terminal
  semantic-search command. Seven fixed English/French/context queries retrieved
  an expected passage at rank 1; unrelated queries still return nearest neighbors.

These assets are downloaded and a key is stored in the Git-ignored local `.env`.
Live access checks passed for `gemini-embedding-001` and the vision alternative
`gemini-3.5-flash-lite`. `gemini-3.8-flash` returned HTTP 503 on both attempts.
The user confirmed the key project shows Free tier; independent billing-page
verification was blocked by automatic approval review. See the
[test report](../docs/api_smoke_test.md). Corpus embeddings, semantic search,
and document-grounded image answers are now implemented. The app validates
source/page citations and displays the exact cited excerpts, scope, and original
unverified context. English and Français are explicit answer-language choices.
Recognized unsupported NDVI calculations receive a local input-limit notice.
See [step 5 verification](../docs/step5_verification.md). Streaming remains planned.

## Smallest complete architecture

```text
Prepare once:
Recommended source pages -> reviewed paragraphs -> gemini-embedding-001 API
                         -> vectors saved in a local index with source/page metadata

Each request:
Streamlit upload + question + user context + answer language
  -> validate image and text
  -> handle recognized unsupported band calculations locally
  -> embed question + supplied context with gemini-embedding-001
  -> retrieve relevant passages from the saved local index
  -> send image, context, and passages to one multimodal API call
  -> validate the completed JSON answer (step 5)
     / parse streamed evidence summary and answer (planned step 6)
  -> render answer with validated source/page citations
```

- One Python process and a small, flat set of modules: `app.py`, `rag.py`,
  `model.py`, and, when streaming is added, `streaming.py`.
- Streamlit is the requested UI. `gemini-3.5-flash-lite` is the working vision
  model selected for the first app call: a real image request passed. The originally
  proposed `gemini-3.8-flash` was temporarily unavailable because of high demand
  on two attempts; do not describe it as successfully tested. API access is
  checked, but continued capacity and available quotas are not guaranteed.
- Use the user-selected `gemini-embedding-001` API for document and query
  embeddings. Use `RETRIEVAL_DOCUMENT` for passages and `RETRIEVAL_QUERY`
  for question/context text. Keep the model and output dimensions consistent.
  Respect its 2,048-token input limit and prevent silent truncation.
  Generate document vectors once for unchanged passages/settings, save them
  locally with source metadata, and compare query vectors using cosine
  similarity. Search requires a query embedding API call, even when document
  vectors are cached. No local embedding model is required.
  Sources: [model limits](https://aistudio.google.com/docs/models/gemini-embedding-001),
  [retrieval task types](https://aistudio.google.com/docs/embeddings#supported-task-types).
- Retrieve from text and user-supplied context. The image goes directly to
  the vision model. An image-description retrieval pass is outside version 1.
- Preserve the requested XML envelope: `<response><thought>...</thought>
  <answer>...</answer></response>`. `thought` means a brief user-visible
  evidence summary. It is not a private reasoning transcript or a record of
  tool calls the model never performed. Collapsing a panel is not a privacy
  boundary.
- Read credentials from the server-side environment. Local development uses
  a Git-ignored `.env` and a shareable `.env.example`; the file is loaded by
  `model.py` for the Gemini connection. Keep uploads and request
  state scoped to the current session; avoid unnecessary persistence.

## Ordered checkpoints

1. Steps 1-2: a real image-to-answer path works locally.
2. Steps 3-4: document passages can be found and inspected independently.
3. Steps 5-6: the full RAG interaction streams with source citations.
4. Steps 7-8: failure cases and a small evaluation set are checked.
5. Steps 9-10: the demo is usable, reproducible, and explainable in a portfolio.

The detailed tasks, completion criteria, learning outcomes, and dependencies
are in `todo.md`. Each session targets one requested step. Explain the idea,
make the smallest implementation, verify it, and update the checklist.

## Evidence and agronomy boundaries

- Images contain multiple fields, not delineated parcels. Crop identities,
  irrigation status, soil chemistry, and nutrient conditions are unverified.
  A user-provided target-field description can disambiguate the image.
- Display RGB is not quantitative reflectance and cannot yield NDVI.
- Distinguish visible patterns, user reports, document guidance, and hypotheses.
  Label invented demo context as synthetic.
- Historical fertilizer guidance must retain its date, crop, geographic scope,
  laboratory method, and units. Numerical tables and OCR need checking.
- The 250 m national soil-mapping paper is contextual evidence, not a field test.
- Provide qualitative next checks and conditional management options in v1;
  do not prescribe fertilizer rates from these images and reference snippets.
- Retrieved documents and model output are untrusted inputs. Validate citation
  IDs and page references; do not follow instructions embedded in reference text.

## Initial demonstration cases

1. Wheat reported by the user: compare lighter field patches with possible
   nitrogen limitation and identify what to inspect or measure next.
2. A user-supplied report says the soil is alkaline/calcareous: retrieve
   phosphorus-availability guidance without inferring soil pH from the image.
3. An irrigated field reported by the user has uneven growth: explain what
   soil, moisture, and management evidence is needed before changing fertilizer.

These are scenarios for testing, not verified labels for the downloaded land.

## Main unknowns to resolve during implementation

- Ongoing embedding/generation quotas, capacity, and output-format reliability.
  Basic access passed and the user confirmed Free tier; no quota or billing
  dashboard was independently inspected. Embedding requests must handle quota
  and network errors; cached document vectors do not make query embedding work
  offline. The one-off smoke-check latency is not a performance benchmark.
- Retrieval quality across French sources and English/French questions.
- OCR quality of the actual paragraphs we select, especially numerical tables.
- Appropriate handling of low-relevance retrieval, established with examples
  rather than an arbitrary universal similarity cutoff.

## Deferred scope

No model training, separate API server, paid vector database, agent framework,
live satellite download pipeline, NDVI computation, automated prescriptions,
authentication system, or automatic web research in version 1. Public hosting
and publication of the corpus are separate decisions; reuse metadata is already
recorded with the downloaded documents.
