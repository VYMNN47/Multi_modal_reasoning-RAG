# GeoScan — Moroccan agriculture RAG demo

[Open GeoScan](https://geoscan-morocco.vercel.app/).

Upload one or two satellite images, add field context and a question, and receive
an assessment grounded in Moroccan agricultural references. The interface uses
HTML, CSS, and JavaScript; a Python ASGI API runs on Vercel. There is no Streamlit
runtime or upload session. The original topographic contour pattern is preserved.

The app includes Gharb, Tadla, and Doukkala Sentinel-2 examples, a dated
Casablanca NASA MODIS comparison, and **Doukkala: NDVI, 2024–2025** with saved
measurements. Crop and soil details in the three editable
field scenarios are synthetic. The NASA case includes its report and acquisition
dates; regional imagery is not a parcel measurement.

## Run locally

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
python -m uvicorn asgi:app --reload --host 127.0.0.1 --port 8501
```

For a new environment, run `uv venv --python 3.14 .venv` first. No frontend build
or npm dependency installation is required.

Put the existing Google key in the private project `.env`:

```dotenv
GEMINI_API_KEY=your-key-here
```

The same server-side key authorizes `gemini-embedding-001` query embeddings and
`gemini-3.5-flash-lite` image answers. On Vercel the existing server Secret supplies
this value. The browser never receives it. Hosting does not increase Gemini's
quota or guarantee provider availability.

## Try it

1. Select a ready-made field example, or choose **Upload my own images**.
2. Choose one or two PNG/JPEG files together. **Add an image** retains the first;
   each file has its own **Remove** control. Both previews appear side by side
   on desktop and stack on narrow screens.
3. Choose English or Français. Enter a question and optional crop, location,
   acquisition dates, growth stage, or target-parcel context. Label invented
   context as synthetic. Undated pairs are not automatically treated as before
   and after views of the same place.
4. Click **Ask Gemini**. Only this action sends the images and text to the API.
   Invalid inputs show a correction message; failed requests keep the form and
   images available for another attempt. Changing inputs clears an old answer.
5. Expand **References cited** to inspect the actual excerpts and source links.

For **Doukkala: NDVI, 2024–2025**, selecting the example shows both acquisition
dates and a measured-NDVI table. **Ask Gemini** sends the verified saved means,
medians, ranges, shared mask counts, and method information with the RGB previews.
Gemini explains those precomputed results. The NDVI method reference supports
definitions; it is not the source of this app's measured values. No spectral
calculation or download runs when opening the page or submitting the question.

Images must total at most **4 MiB**, shown as 4 MB, per assessment. Each image must
be a complete, single-frame PNG/JPEG with at most 16 million pixels. Orientation
is applied and metadata removed before Gemini receives RGB PNGs; their combined
prepared size must fit within 10 MiB. Questions allow 2,000 characters; optional
context allows 4,000. Selecting or previewing images never calls Gemini.

The browser holds the selected files until refresh or closing the page. Each
assessment is an independent request containing all of its inputs. There is no
upload database or persistent image store. The multipart parser may use temporary
files while handling a request; its resources are closed afterward.

## How it works

```text
Browser: examples or 1–2 files + question + context + language
  → one multipart POST /api/analyze
  → validate inputs and prepare both RGB images
  → NDVI example: verify the saved summary and select its NDVI method excerpt
    Other inputs: embed the query and search the 16 saved document vectors
  → send images, selected excerpts, and any saved measurements to Gemini
  → validate the final JSON and reference labels
  → return the assessment and public source metadata
  → render text and canonical citation links in the browser
```

The existing reviewed passages and vectors are reused. No vector database,
autonomous browsing, private reasoning transcript, or document re-embedding is
introduced. The NASA example pins its case report and retrieves up to two other
excerpts. Other RGB inputs retrieve up to three excerpts. The measured Doukkala
NDVI case instead loads its saved summary and uses only its curated NDVI method
reference; it needs one generation request and no query-embedding request.

| Endpoint | Purpose |
| --- | --- |
| `GET /` | HTML interface |
| `GET /assets/*` | Styles, JavaScript, and original contour artwork |
| `GET /api/health` | Process health |
| `GET /api/examples` | Public examples and the upload limit |
| `GET /api/example-images/{filename}` | Allowlisted example image files |
| `POST /api/analyze` | One independent assessment |

The POST accepts `question`, `context`, `language`, `case`, and up to two `images`
file parts. `case=upload` uses supplied files; a catalog case uses its saved
images and must not be mixed with uploads. Unknown, duplicate, or incorrectly
typed fields are rejected. Application errors return `{"error": "correction message"}`; request-size and hosting errors can return an HTTP error without that JSON envelope.

The API caps request bytes, validates real image contents, rejects cross-origin
browser submissions, and sends a restrictive content security policy. The
frontend renders user context and source excerpts as text; only validated source
citations become links. This is a public demo without visitor authentication,
so anyone with the URL can consume the server's Gemini quota.

## Prepare and search the documents

Document preparation is a separate author workflow, not part of app startup:

```bash
python rag.py
python rag.py embed
python rag.py search "What affects phosphorus availability in calcareous soil?"
```

Review the source transcriptions before rebuilding. The repository already
contains the 16 prepared passages and their embedding index. The source manifest,
review notes, and provenance are in `demo_data/rag_documents/`; the original
imagery metadata is in `demo_data/sentinel2/` and `demo_data/comparison/`.

## Prepare Doukkala vegetation-change data

The first internship-exercise increment adds analytical data for **20 February
2024** and **14 February 2025** over the existing Doukkala/Sidi Bennour footprint.
Both dates have real B04 red and B08 near-infrared GeoTIFFs, an aligned SCL quality
layer, an RGB preview, source metadata, and checksums in
[`demo_data/doukkala_change/`](demo_data/doukkala_change/README.md).

The author-only download command is `uv run prepare_doukkala.py`. Its inline
dependencies use an isolated environment; the web application's requirements do
not change. It refuses to overwrite an existing data package. The saved data can
be validated offline with
`python -m unittest discover -s tests -p test_doukkala_data.py -v`.

Calibrated NDVI is now calculated for both dates on a common valid-land mask.
The offline command is `uv run calculate_doukkala_ndvi.py`; it saves float32
GeoTIFFs, the shared mask, and [summary statistics](demo_data/doukkala_change/ndvi/summary.json).
Mean NDVI is 0.466847 in 2024 and 0.421007 in 2025 over the same 262,140 pixels.
See the [calculation walkthrough](demo_data/doukkala_change/README.md#ndvi-calculation)
for masking, calibration, and verification commands.

Pixelwise NDVI change is now saved with `uv run calculate_doukkala_change.py`.
It subtracts 2024 NDVI from 2025 NDVI and classifies the same valid pixels using
a demo tolerance of ±0.05: 34.15% decreased, 48.63% stable, and 17.22% increased.
The [change summary](demo_data/doukkala_change/change/summary.json) includes counts,
projected-grid areas, thresholds, and checksums. Stable means within the tolerance;
these classes do not establish crop identity, crop loss, or causes. See the
[change calculation walkthrough](demo_data/doukkala_change/README.md#ndvi-change-and-classification).

Displaying the change map, legend, imagery/change switch, and area figures is the
next increment. The NDVI example is already available in the interface and connected to
Ask Gemini using a checksum-verified summary. Editable context cannot replace
those numbers, and client-supplied measurement fields are rejected. Raw bands,
calculated rasters, original STAC/XML files, and the author scripts are excluded
from deployment uploads. Only the two RGB previews, case metadata, summary, and
runtime prompt are required for the NDVI web example.
See the [NDVI example verification](docs/ndvi_example.md) for browser and live-model
checks of this integration.
The new change rasters and summary are author-only outputs; they are not yet
displayed or supplied to Gemini, and are excluded from deployment uploads.

## Verify and deploy

```bash
python -m unittest discover -s tests -v
node --check assets/site.js
uv pip check --python .venv/bin/python
```

Tests run offline, including the actual Google SDK against a simulated HTTP
transport, citation checks, image validation, request limits, examples, and
consecutive one/two-image requests. Browser checks cover selection, removal,
repeat submission, stale results, language, and narrow layouts.

The Vercel function entry point remains `api/index.py`, exporting `asgi.app`.
`vercel.json` routes requests to that app and includes the runtime assets and
prepared index. The existing project is `geoscan-morocco` in `aymnns-projects`.
See [the deployment guide](docs/vercel.md) for the CLI command and acceptance
checks. Local edits require a new deployment; CLI deployment does not commit or
push Git changes.

## What to learn from this version

- Browser state manages selected files and previews; Python validates each request.
- Multipart form data carries both image binaries and text together.
- Stateless endpoints let separate server instances handle consecutive requests.
- The API key and Gemini SDK belong on the server; the browser receives results.
- Retrieval finds candidate evidence; citation validation checks labels, not truth.

Historical learning checkpoints remain in [step 1](docs/step1.md),
[step 2](docs/step2.md), [step 3](docs/step3.md), [step 4](docs/step4.md), and
[step 5](docs/step5.md). Their Streamlit UI instructions describe earlier versions.
See [prompt history](prompts/README.md) for the default v8 and measured NDVI
instructions and their limits.

## Evidence limits

RGB patterns do not establish crop identity, soil chemistry, deficiencies, NDVI,
yield, or the cause of a change. Dates and locations in user context are reports,
not verified observations. The model suggests conditional checks and does not
prescribe fertilizer products or rates. Reference dates, crops, and geography
constrain applicability. A valid citation label is not proof of claim support.

SDK calls keep a 120-second timeout and one automatic retry for selected temporary
failures. Vercel's function limit remains 300 seconds; slow provider retries can
still exceed it. The full ten-case live prompt baseline has not been rerun for
v8. The NDVI case uses its own versioned prompt, leaving the v8 instruction for
the existing examples unchanged. Streaming/evidence summaries remain future work.
