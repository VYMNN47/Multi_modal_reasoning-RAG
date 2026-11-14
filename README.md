# GeoScan — Moroccan agriculture RAG demo

A learning project that will combine Moroccan crop imagery, agricultural
documents, and Gemini. **Current stage: step 5, document-grounded image answers.**
The Streamlit form retrieves from 16 reviewed passages, then sends the image,
question, field context, and selected excerpts to `gemini-3.5-flash-lite`.

The app validates citation labels, builds source/page links from saved metadata,
and displays the cited excerpts with their dates and scope. The same server-side
key is used for embeddings and generation. Streaming remains step 6.

Three editable field examples and one dated before/after comparison load directly in the app, alongside an
original topographic contour background. The project has a Vercel ASGI entry
point and deployment configuration. **The interface is live at
[GeoScan](https://geoscan-morocco.vercel.app), with the Gemini key configured on the server.**
Public health, controls, image previews, a sample upload, and a real hosted
comparison assessment have been checked. See the [deployment walkthrough](docs/vercel.md) and
[deployment verification](docs/vercel_deployment.md).

## Prepare the document passages

```bash
source .venv/bin/activate
python rag.py
```

This rebuilds `demo_data/rag_documents/passages.jsonl` from reviewed source
excerpts and checks source integrity. Unchanged data reuses its token counts
offline. New/changed embedding text is checked with the `gemini-embedding-001`
tokenizer using the existing key; it does not generate embeddings. See the
[step 3 walkthrough](docs/step3.md).

## Embed and search the passages

```bash
source .venv/bin/activate
python rag.py embed
python rag.py search "What affects phosphorus availability in calcareous soils?"
python rag.py search "What should I check before changing fertilizer?" --context "Synthetic demo context: an irrigated field in Doukkala has uneven growth."
```

`embed` sends new/changed `embedding_text` inputs to `gemini-embedding-001` using
`RETRIEVAL_DOCUMENT`, saving 3,072-dimensional vectors and source metadata in
`demo_data/rag_documents/embedding_index.json`. Unchanged inputs/settings reuse
their saved vectors without an API call. No extra database or dependency is needed.

`search` counts the exact question/context tokens, embeds them with
`RETRIEVAL_QUERY`, and ranks the saved document vectors by cosine similarity.
It returns three passages by default (`--top-k 5` requests five), including their
text, scores, source/page citations, dates, and geographic scope. Search needs
the key and network access: one token-count request and one embedding request
per search. It does not send an image or call the vision model.

Scores are similarity, not diagnostic confidence. There is no calibrated
relevance filter yet; unrelated questions also return nearest passages. Our
seven fixed agronomic queries each retrieved an expected passage at rank 1;
some supporting Doukkala passages missed the top three. See the
[step 4 walkthrough](docs/step4.md) and [verification](docs/step4_verification.md).

## Run the existing environment

From the project directory, on Linux/macOS:

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

Open <http://127.0.0.1:8501>. The app listens on this computer's loopback address.
Stop it with **Ctrl+C** in the terminal. Previewing/validating inputs needs no
key; document-backed assessments need the key and network access.

## Create a new environment

Use Python 3.14 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
This project was checked with Python 3.14.4 and uv 0.13.1.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
python -m streamlit run app.py
```

`requirements.txt` pins Streamlit, Pillow, Google's Gen AI SDK, python-dotenv,
and the SDK's HTTP transport used for network-error handling.
Their transitive dependencies are resolved during installation; this is not a
complete dependency lockfile. The local environment and bytecode are Git-ignored.

If updating the existing environment, stop the running server, run
`uv pip install --python .venv/bin/python -r requirements.txt`, then restart it.
The watcher excludes `.venv/` and `.git/` to avoid treating package/Git changes as
application changes.

## Configure Gemini

The existing `.env` already contains the project's key. For a fresh checkout,
copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` locally. The app reads
this exact project file with python-dotenv. Existing server environment values
take precedence; restart the app after changing a loaded key. The same key can
be used for the selected vision model and embedding calls.

The key is passed explicitly to the Gemini Developer API client and is never
included in the prompt or session state. No Google Cloud/enterprise project or
extra key is required. `.env` remains Git-ignored.

## Try it

1. Choose a ready-made Gharb, Tadla, or Doukkala example. Its real image and
   synthetic question/context load automatically. Alternatively choose
   **Upload my own image** and upload one of these PNGs from `demo_data/sentinel2/`:
   - `doukkala_2025-02-14_rgb_10m.png`
   - `tadla_2025-02-14_rgb_10m.png`
   - `gharb_2025-02-14_rgb_10m.png`
   Choose **Casablanca: Drought, 2023–2024** for two regional NASA MODIS views
   from 12 February 2023 and 19 February 2024, shown side by side. The dates,
   satellites, and report are preserved in [comparison provenance](demo_data/comparison/README.md).
2. Choose English or Français for the answer, then enter a question such as
   “Why are some field patches lighter?”
3. Optionally add the crop, region, acquisition date, growth stage, and target
   field. Mark invented context as synthetic.
4. Click **Ask Gemini**. The form validates the inputs, sends them to Google,
   retrieves relevant text, then generates and checks a complete answer. Expand
   **References cited** to inspect the exact excerpts, dates, crops, scope, and
   original-PDF links. Each deliberate valid submit makes a new request.

Search uses the question/context; the image goes to the vision model. Only cited
excerpts appear under the answer. Missing evidence is disclosed, and unrelated
questions receive a brief scope refusal. A valid source/page link does not prove
that every claim is supported: inspect the cited text. Historical guidance and
national soil maps do not establish a diagnosis for the uploaded parcel.

PNG/JPEG files must be no larger than 10 MiB (shown as 10 MB in the UI), contain
at most 16 million pixels, and have one frame. Questions allow 2,000 characters;
optional context allows 4,000. Invalid inputs keep the form editable.
On Vercel, uploads are capped at 4 MiB. The author chose a public demo with no
access code: visitors can submit assessments using the server's Gemini quota.
Example selection itself never calls Gemini.
The prepared RGB PNGs must fit within 10 MiB combined. JPEGs are oriented for display;
embedded image metadata is removed before sending.

Uploads remain in the running Streamlit session; the application writes no
uploaded files to disk. Browser refreshes/new sessions are not durable storage.
The current answer is stored only in that session and ordinary reruns do not
repeat the API call. Changed inputs or a failed new submit clear the previous
answer and sources so they are not presented under the wrong image/question.
Changing the prompt version also clears the cached response.
For the comparison, changes to either image, date, or report metadata also clear
the answer. Both dated images go to Gemini as separate image parts. The selected
NASA report is explicitly included with up to two semantic-search results; it
has not been added to or embedded in the existing 16-passage index. Its citations
link to the article without inventing a PDF page. See [how the comparison works](docs/comparison.md).
RGB images do not supply NDVI or establish soil chemistry or nutrient deficiency.
The Gemini client uses a 120-second network timeout and at most two attempts per
API call: the initial attempt and one automatic retry for a timeout, connection
failure, or selected temporary server error. The retry waits 1–2 seconds.
A timeout does not establish that an image is oversized; service latency or the
connection can vary, so an identical request may succeed later. This is a network
operation timeout, not a strict deadline for the entire RAG workflow. Wait briefly
before submitting again after both attempts fail. Quota/rate-limit failures stop
without an automatic retry. See [the retry walkthrough](docs/gemini_reliability.md)
for eligible errors, quota implications, verification, and Vercel's separate limit.
Explicit English/French NDVI-calculation requests receive a local **Input
limitation** notice without API calls. Original field context remains visible
as unverified plain text alongside generated assessments.

## Learn and verify

- [Step 1 walkthrough](docs/step1.md): environment, Python modules, image bytes,
  validation, and Streamlit forms/reruns.
- [Step 2 walkthrough](docs/step2.md): API keys, the SDK, multimodal requests,
  prompts, response handling, and session state.
- [Step 2 verification](docs/step2_verification.md): automated checks and the
  real image-to-answer result.
- [Step 3 walkthrough](docs/step3.md): source review, paragraph passages,
  provenance, stable IDs, and exact embedding-input token checks.
- [Step 4 walkthrough](docs/step4.md): document/query embeddings, cached vectors,
  local cosine search, and multilingual retrieval results.
- [Step 5 walkthrough](docs/step5.md): reference context, grounded generation,
  citation validation, evidence gaps, source inspection, and session behavior.
- [Prompt history](prompts/README.md): preserved candidates and the current instruction.
- [Project checklist](tasks/todo.md): ordered tasks and learning goals.
- [Vercel preparation](docs/vercel.md): examples, contour assets, the ASGI entry
  point, secrets, deployment limits, and hosted acceptance checks.
- [Architecture plan](tasks/plan.md).

Run the automated checks from the project root:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
uv pip check --python .venv/bin/python
```

The tests check real image decoding, the Streamlit form through `AppTest`, and
actual SDK request serialization through a simulated HTTP transport. They need
no external service or real credentials. Streamlit may emit
its “missing ScriptRunContext” notice when initializing AppTest outside a server;
test results still determine pass/fail.

To deliberately repeat the **live** retrieval check (uses API quota):

```bash
python -m tests.evaluate_search
```

This checks six scenario questions, one separate-context query, and three
unrelated probes, then records results in `docs/step4_retrieval_test.json`.
The regular unit-test command stays offline.

For the explicit live image + retrieval + answer checks:

```bash
python -m tests.evaluate_answers
```

This uses the ten fixed cases in `tests/answer_cases.json` and saves
`docs/step5_answers_test.json`. Unchanged successful cases resume from the report;
new API calls are needed for pending cases or changed prompts/inputs. A partial
run has `complete: false`. The checks are narrow behavioral probes, not an
agronomic accuracy score. The completed step 5 run passed 70 checks across nine
actual vision responses and one local input-limit notice. See
[verification](docs/step5_verification.md).

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Image validation, the form, and session-scoped answer display |
| `model.py` | Gemini client, reference context, response checks, and citation rendering |
| `prompts/` | Current grounded instruction and previous prompt candidates |
| `rag.py` | Passage preparation, token checks, embedding cache, and semantic search |
| `requirements.txt` | Direct Python dependency versions |
| `.python-version` | Python version requested by uv |
| `.streamlit/config.toml` | Local server, telemetry, and theme settings |
| `tests/test_app.py` | Image and form behavior checks |
| `tests/test_model.py` | Credentials, SDK payloads, and simulated API failures |
| `tests/test_rag.py` | Passage integrity, cached counts, and scenario coverage |
| `tests/test_search.py` | Embedding requests, vector validation, caching, and ranking |
| `tests/evaluate_search.py` | Explicit live retrieval checks with the fixed demo queries |
| `tests/test_grounding.py` | Citation integrity, output contracts, and evaluation recovery |
| `tests/evaluate_answers.py` | Explicit live image/retrieval/answer checks |
| `.env` | Private server credentials; never commit |
| `demo_data/` | Downloaded images, source documents, and provenance |

Satellite imagery: **Contains modified Copernicus Sentinel data 2025**.
See [image provenance](demo_data/sentinel2/README.md) and
[document provenance/reuse notes](demo_data/rag_documents/README.md).
