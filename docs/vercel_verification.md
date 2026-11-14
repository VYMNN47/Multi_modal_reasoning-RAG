# Vercel preparation verification

Historical local-preparation record. The app has since been deployed and the
access-code gate removed; see [current deployment verification](vercel_deployment.md).

Checked on 13 November 2026. Scope: selectable demo examples, the requested
contour pattern, an ASGI deployment entry point, hosted input/access boundaries,
and deployment/learning documentation. **No Vercel project was created or
published, and no Vercel build or hosted session test has run.**

## Automated and packaging checks

- **83 offline tests passed**, including all 73 prior checks and ten new checks.
  Existing upload tests now explicitly select upload mode before exercising
  their unchanged image, validation, state, failure, and citation assertions.
- New AppTest checks cover all three real image/question/context combinations,
  zero API calls during selection, editable/cleared questions, stale-answer
  removal, upload-mode reset, hosted missing/wrong codes, and a correct code.
  The model receives each example's original RGB pixels despite thumbnail display.
- A hosted missing-key test checks the visitor-facing error without constructing
  a client. The four-MiB upload boundary rejects oversized files before decoding.
- The real ASGI wrapper starts in a child process and serves the frontend HTML,
  health route, and an accepted WebSocket connection through an in-memory client.
  That test passed outside the agent's network-restricted sandbox; inside it,
  AnyIO's cross-thread test-client startup stalled before app execution.
- Deployment-ignore patterns keep secrets, original PDFs, and GeoTIFFs out while
  retaining runtime Python, CSS/SVG, prompt, prepared data, and example PNGs.
  An isolated copy of only the thirteen runtime application/data files loaded
  the sixteen saved index records and all three example images without raw
  source documents or `.env`. The application/data assets total about 2.3 MB;
  this excludes Python dependencies and is not a measured Vercel function bundle.
- `vercel.json` validated against Vercel's official JSON schema. The TOML entry
  point resolves to `asgi:app`. The actual cloud dependency build remains untested.
- `uv pip check --python .venv/bin/python` passed for all 52 installed packages.
  No dependency was added or changed. The existing local site-packages directory
  was about 419 MiB, not a hosted bundle measurement.
- DESIGN.md lint reported zero errors/warnings. The strict UI audit reported
  zero findings after excluding installed `.venv` files from its scan. That
  generic scanner does not validate Python Streamlit behavior; AppTest and the
  real-browser checks below provide the relevant UI evidence.

Expected Streamlit bare-mode warnings were not suppressed. No formatter,
typechecker, or separate frontend build is configured in this repository.

## Real browser checks through the ASGI entry point

The local server used `python -m uvicorn asgi:app --host 127.0.0.1 --port 8501`,
not the Streamlit CLI. The following were observed in the browser:

- The Gharb example loaded without an upload. Keyboard navigation selected
  Tadla and replaced its image, question, and synthetic context.
- One deliberate Tadla submission completed real query retrieval and Gemini
  vision generation, showing canonical NPK source/page links and cited panels.
  No additional live generation was made for layout changes.
- The existing evidence limits remain relevant: that answer attached a citation
  to a next-check sentence even though the prompt asks to keep generic checks
  uncited. A valid source label does not establish claim entailment or agronomic
  correctness. The prompt/index were not retuned for this UI/deployment task.
- Switching to upload mode removed the previous assessment and cleared example
  text. Empty submission displayed the image/question correction messages.
- A real Gharb PNG upload completed with HTTP 204 through the ASGI upload route
  and displayed the preview. Browser-tool file transfer was slow (about 76 s);
  this is not a measured app latency or a performance guarantee.
- Ctrl+Enter submitted an exact-NDVI request using the upload and displayed the
  local input-limitation notice. Changing to Français cleared the prior notice;
  keyboard submission then produced the French notice. Neither requires a
  retrieval or generation request.
- At 1280 × 800 the form and primary action were visible together with the
  selected image. At 320 × 900 the columns stacked, the open picker remained
  usable, and body/document widths stayed 320 px. No horizontal overflow appeared.
- Native controls and semantics were preserved. The decorative SVG adds no
  motion, and forced-colors CSS removes it. Full screen-reader, theme, touch,
  zoom, and high-contrast certification was not performed.
- No console warning/error was recorded after the final ASGI startup period.
  The temporary viewport override was reset; the page was left on the ready
  Tadla example in English.

Screenshots: [desktop form](screenshots/vercel_examples_desktop.png) and
[narrow picker](screenshots/vercel_examples_narrow.png).

## Integrity and release limits

All eight original PDF checksums match the download manifest. Prepared passages
and the embedding index still match the step-4 report hashes. The actual local
key was checked in memory against project text/data/assets and was absent.
`.env` remains mode 0600 and Git-ignored. No local credential was changed or
sent to Vercel. No Git staging, commit, or push was performed.

The hosted access-code gate is a shared invitation control, not per-user accounts
or a distributed rate limiter. On Vercel it fails closed when the code is unset.
Local development intentionally needs no shared code. Vercel environment values
and the real account/project setup have not been inspected.

Before sharing a URL, run the hosted checks in [the deployment guide](vercel.md),
especially separate uploads/sessions and reconnection after the 300-second
function lifetime. Streamlit's in-memory state and upload routing still need
validation on Vercel's multi-instance runtime. Inline previews do not solve
distributed uploads. Gemini free-tier capacity/quota remains variable.

Streaming remains step 6. No autonomous tool loop, additional embedding model,
vector database, new source material, or private reasoning transcript was added.
