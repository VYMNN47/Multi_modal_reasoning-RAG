# Moroccan agriculture RAG demo

A learning project that will combine Moroccan crop imagery, agricultural
documents, and Gemini. **Current stage: step 2**, a local upload form that sends
an image, question, and optional field context to `gemini-3.5-flash-lite` and
displays its answer.

The app loads the existing server-side API key. Document retrieval, embeddings,
citations, and streaming are not connected yet.

## Run the existing environment

From the project directory, on Linux/macOS:

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

Open <http://127.0.0.1:8501>. The app listens on this computer's loopback address.
Stop it with **Ctrl+C** in the terminal. Previewing/validating inputs needs no
key; selecting **Ask Gemini** needs the key and network access.

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
be used for the selected vision model and future embedding calls.

The key is passed explicitly to the Gemini Developer API client and is never
included in the prompt or session state. No Google Cloud/enterprise project or
extra key is required. `.env` remains Git-ignored.

## Try it

1. Upload one of these PNGs from `demo_data/sentinel2/`:
   - `doukkala_2025-02-14_rgb_10m.png`
   - `tadla_2025-02-14_rgb_10m.png`
   - `gharb_2025-02-14_rgb_10m.png`
2. Enter a question such as “Why are some field patches lighter?”
3. Optionally add the crop, region, acquisition date, growth stage, and target
   field. Mark invented context as synthetic.
4. Click **Ask Gemini**. The form validates the inputs, sends them to Google,
   shows a loading indicator, then renders the complete response or an actionable
   error. Each deliberate valid submit makes a new request.

PNG/JPEG files must be no larger than 10 MiB (shown as 10 MB in the UI), contain
at most 16 million pixels, and have one frame. Questions allow 2,000 characters;
optional context allows 4,000. Invalid inputs keep the form editable.
The prepared RGB PNG must also fit within 10 MiB. JPEGs are oriented for display;
embedded image metadata is removed before sending.

Uploads remain in the running Streamlit session; the application writes no
uploaded files to disk. Browser refreshes/new sessions are not durable storage.
The current answer is stored only in that session and ordinary reruns do not
repeat the API call. Changed inputs or a failed new submit clear the previous
answer so it is not presented under the wrong image/question.
RGB images do not supply NDVI or establish soil chemistry or nutrient deficiency.

## Learn and verify

- [Step 1 walkthrough](docs/step1.md): environment, Python modules, image bytes,
  validation, and Streamlit forms/reruns.
- [Step 2 walkthrough](docs/step2.md): API keys, the SDK, multimodal requests,
  prompts, response handling, and session state.
- [Step 2 verification](docs/step2_verification.md): automated checks and the
  real image-to-answer result.
- [Project checklist](tasks/todo.md): ordered tasks and learning goals.
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

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Image validation, the form, and session-scoped answer display |
| `model.py` | Credential loading, Gemini request, prompt, and response/error checks |
| `requirements.txt` | Direct Python dependency versions |
| `.python-version` | Python version requested by uv |
| `.streamlit/config.toml` | Local server, telemetry, and theme settings |
| `tests/test_app.py` | Image and form behavior checks |
| `tests/test_model.py` | Credentials, SDK payloads, and simulated API failures |
| `.env` | Private server credentials; never commit |
| `demo_data/` | Downloaded images, source documents, and provenance |

Satellite imagery: **Contains modified Copernicus Sentinel data 2025**.
See [image provenance](demo_data/sentinel2/README.md) and
[document provenance/reuse notes](demo_data/rag_documents/README.md).
