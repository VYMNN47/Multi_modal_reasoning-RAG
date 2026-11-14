# Project Checklist and Learning Guide

Work through one step per focused session. For each step: understand the concept,
implement a small change, verify it, and explain what happened in your own words.
Mark a task complete only when its completion criteria pass.

## Already completed

- [x] Download three real Moroccan Sentinel-2 image crops and source metadata.
- [x] Download eight agricultural PDFs and preserve their original sources.
- [x] Extract/OCR 125 pages and flag 50 pages to start reviewing for retrieval.
- [x] Record source dates, geographic scope, image limitations, and file checksums.
- [x] Prepare a Git-ignored local `.env` and a shareable `.env.example`;
  the application now loads the key on the server in step 2.
- [x] Select `gemini-embedding-001` for embeddings; step 4 now saves vectors for
  all 16 prepared passages locally and searches them using embedded queries.
- [x] Check API access: embeddings and `gemini-3.5-flash-lite` image input passed;
  `gemini-3.8-flash` returned HTTP 503 twice. The user confirmed the project is on
  Free tier. Details: [access report](../docs/api_smoke_test.md).

Learning from this preparation: provenance, satellite resolution, the difference
between RGB and analytical bands, and why OCR text needs checking before reuse.

## Step 1: Run the upload interface locally

- [x] Complete step 1.

**Build:** A reproducible Python environment and a Streamlit form with image
upload, image preview, question, and optional field-context input.
**Learn:** Virtual environments, dependencies, Python modules, file bytes,
input validation, and Streamlit's rerun/form behavior.
**Done when:**
- [x] A documented command launches the app in a clean environment.
- [x] Each of our three PNGs previews correctly and form values are retained.
- [x] Empty questions and invalid/oversized images get useful validation messages.
**Verify:** Run locally; try three valid images, invalid bytes, and an empty form.
**Explain:** Why do we validate image contents rather than trust the extension?
**Dependencies:** None. **Files:** `app.py`, `tests/test_app.py`, environment/theme
configuration, and learning/setup documentation. No model call yet.
**Evidence:** 11 automated checks passed; the real upload and keyboard submit
worked in the browser, with desktop and 320 px layout checks. See the
[walkthrough](../docs/step1.md) and [verification notes](../docs/step1_verification.md).

## Step 2: Get one real image-to-answer response

- [x] Complete step 2.

**Build:** Connect the form to `gemini-3.5-flash-lite`, the selected image-capable model
that passed the access test, initially without RAG or custom streaming. Load the
private local `.env` into the server-side environment before creating the model
client. Use the smoke-check report for the verified request pattern; ongoing quota
and provider capacity still require normal error handling.
**Learn:** API requests/responses, image payloads, system instructions, model
capabilities, secrets, quotas, and the difference between a model and an agent.
**Done when:**
- [x] A real request sends the image and question and renders a response.
- [x] A changed question/context reaches the request; no secret enters source code.
- [x] A credential or quota failure yields a useful message without leaking data.
**Verify:** One live image request; inspect the request shape and exercise an error.
**Explain:** What can the model observe, and what information is still missing?
**Dependencies:** 1. **Likely files:** `model.py`, `app.py`, `requirements.txt`,
`.env.example`, `tests/test_model.py`.
**Evidence:** 23 automated checks passed, including simulated HTTP failures. One
real Doukkala image/question/context submission returned an answer in the browser.
See [step 2 walkthrough](../docs/step2.md) and
[verification notes](../docs/step2_verification.md).
**Scope:** Model/UI integration, focused tests, dependency/configuration updates,
and learning documentation. No retrieval or streaming yet.

### Checkpoint A: Image-to-answer demo

- [x] A fresh app session can upload an image and obtain a real answer.
- [ ] You can trace the image and question from the form to the API response.

## Step 3: Turn source pages into useful passages

- [x] Complete step 3.

**Build:** Load the recommended pages and split reviewed text into coherent
paragraph passages with source IDs, physical PDF pages, dates, crop, and geography.
Keep original PDFs and extraction files unchanged.
**Learn:** Data preparation, OCR limitations, chunking, token limits, source
provenance, and why source metadata matters as much as the text.
**Done when:**
- [x] Selected passages for the three demo scenarios match their source pages.
- [x] Every passage has a stable ID and source/page metadata, and fits the chosen
  `gemini-embedding-001` model's 2,048-token input limit without silent truncation.
- [x] Unchecked numerical tables and low-quality OCR are flagged for review.
**Verify:** Focused preparation checks plus visual comparison with the source PDFs.
**Explain:** What goes wrong if we embed a whole PDF or lose its page references?
**Dependencies:** None; uses downloaded assets. **Likely files:** `rag.py`,
`tests/test_rag.py`, a generated passage data file.
**Scope:** Small/medium, 2 code files plus data.
**Evidence:** 16 passages from selected prose on 10 PDF pages across eight sources;
largest exact embedding input 218 tokens. All 35 tests pass. Unchanged data rebuilds
offline; 40 recommended pages and unverified numerical tables remain pending.
See [walkthrough](../docs/step3.md) and [verification](../docs/step3_verification.md).

## Step 4: Search the passages with Gemini embeddings

- [x] Complete step 4.

**Build:** Generate passage vectors with the `gemini-embedding-001` API using
`RETRIEVAL_DOCUMENT`, and cache them locally with source metadata. Embed the
question plus supplied field context using the same model and dimensions with
`RETRIEVAL_QUERY`, then search a small local cosine-similarity index. Reuse the
existing Gemini credentials and SDK; a local embedding model is not required.
**Learn:** Embedding APIs, retrieval task types, caching, semantic versus keyword
matching, cosine similarity, multilingual search, and why similarity is not
factual confidence.
**Done when:**
- [x] The three scenario queries retrieve relevant sources in the top results.
- [x] At least one French/English query pair retrieves the intended source.
- [x] The saved index reloads and unchanged passages/settings reuse cached
  vectors; irrelevant-query behavior is checked with examples, and embedding
  quota/network failures produce a useful error.
**Verify:** A small expected-source query set, index/cache checks, and an embedding
failure case; inspect returned text and scores.
**Explain:** Why are the embedding model and vision model doing different jobs?
**Dependencies:** 2, 3. **Files:** `rag.py`, `tests/test_search.py`,
`tests/evaluate_search.py`, the saved index, and learning/verification notes.
The existing Gemini client/credentials are reused without changing `model.py`.
**Scope:** Independent retrieval only; app/vision integration remains step 5.
**Evidence:** 16 real 3,072-dimensional document vectors; unchanged rebuild made
zero API calls. All seven fixed English/French/context queries hit an expected
passage at rank 1. Mean expected-passage recall@3 was 0.810: supporting Doukkala
evidence remains incomplete. Three unrelated probes still returned nearest
neighbors, so there is no automatic relevance/abstention claim. See the
[walkthrough](../docs/step4.md) and [verification](../docs/step4_verification.md).

### Checkpoint B: Evidence can be found

- [x] Relevant passages can be inspected without making a vision-model call.
- [ ] You can explain why a result matched and when it should not be trusted.

## Step 5: Ground the image response in retrieved evidence

- [x] Complete step 5.

**Build:** Assemble the question, user context, image, and retrieved passages in
one multimodal request. Render an answer with source/page citations and links.
**Learn:** Retrieval-augmented generation, context assembly, prompt boundaries,
grounding, citation validation, and observation versus causal inference.
**Done when:**
- [x] The answer cites only source IDs and pages supplied in that request.
- [x] It distinguishes image observations, user reports, document guidance,
  and hypotheses; synthetic demo context is labeled.
- [x] Missing or irrelevant evidence is disclosed, with no fabricated soil test,
  nutrient diagnosis, fertilizer dose, or claimed document-search action.
**Verify:** Run all three scenarios and one unrelated query; inspect citations.
**Explain:** What changed in the model's input when we added RAG?
**Dependencies:** 2, 4. **Files:** `model.py`, `app.py`, versioned prompts,
model/form/citation tests, the fixed live evaluator, and learning notes.
`rag.py`, dimensions, source files, and the saved index are unchanged in this step.
**Evidence:** All 73 automated tests pass. Ten fixed cases passed 70 narrow checks:
nine actual vision responses plus one local NDVI input-limit notice. Three
scenario pairs, missing context, an unrelated task, and untrusted instructions
were checked. Four transient HTTP 503 attempts remain recorded. Desktop and
320 px browser views show checked links and source excerpts. Original context
is displayed verbatim as unverified. Citation membership is enforced; claim
support and crop/region applicability still need review, so this is not an
agronomic accuracy claim. See the [walkthrough](../docs/step5.md) and
[verification](../docs/step5_verification.md).

## Step 6: Stream the evidence summary and final answer

- [ ] Complete step 6.

**Build:** Introduce the agreed XML envelope and an incremental parser. Stream
brief evidence-summary text into a status panel; collapse it when answer text
begins. Mark success only after valid output and successful API completion.
**Learn:** Python generators, streaming events, incremental parsing, buffers,
state machines, and the distinction between a summary and private reasoning.
**Done when:**
- [ ] Tags split across arbitrary chunks parse correctly without leaking XML.
- [ ] Summary and answer render in their intended locations; the panel collapses
  when the answer starts and the request remains running until completion.
- [ ] Malformed XML or an interrupted response is visibly incomplete, not success.
**Verify:** Parser tests with split tags/truncated output, then one live stream.
**Explain:** Why is searching each received chunk for a complete tag unreliable?
**Dependencies:** 5. **Likely files:** `streaming.py`, `model.py`, `app.py`,
`tests/test_streaming.py`.
**Scope:** Medium, up to 4 files.

### Checkpoint C: Full core interaction

- [ ] Upload -> retrieval -> streamed summary -> cited answer works end to end.
- [ ] You can draw the data flow and explain which component owns each state.

## Step 7: Handle failures and session state reliably

- [ ] Complete step 7.

**Build:** Clear handling of timeouts, quota errors, missing evidence, interrupted
streams, and Streamlit reruns. Keep request data isolated to the current session.
**Learn:** Error recovery, API failure modes, session state, request lifecycle,
untrusted reference text, and avoiding accidental duplicate model calls.
**Done when:**
- [ ] Reruns and form edits do not accidentally repeat a completed API request;
  a deliberate new submit starts a fresh result.
- [ ] Quota errors, timeouts, and interrupted streams preserve a useful UI and
  never label a partial response complete.
- [ ] Reference-text instructions cannot change the app's controls or output
  contract; credentials and session data are not exposed to another session.
**Verify:** Simulated API failures, parser failure tests, and a two-session check.
**Explain:** Why can an apparently harmless UI rerun consume API quota?
**Dependencies:** 6. **Likely files:** `app.py`, `model.py`, `streaming.py`,
`tests/test_model.py`, `tests/test_streaming.py`.
**Scope:** Medium, up to 5 files.

## Step 8: Evaluate with a small fixed question set

- [ ] Complete step 8.

**Build:** A compact evaluation sheet with three demo cases, one French query,
one unrelated query, and one missing-context case. Record expected evidence and
acceptable behavior before assessing outputs.
**Learn:** Retrieval hit-at-k, groundedness versus correctness, qualitative
evaluation, reproducibility, latency, and diagnosing retrieval versus model errors.
**Done when:**
- [ ] Each case records expected source IDs and explicit answer checks.
- [ ] Retrieval hits, citation validity, unsupported claims, and observed latency
  are recorded for one identified model/prompt/index configuration.
- [ ] Remaining failures are documented; no unmeasured agronomic accuracy claim
  is made from this small demonstration set.
**Verify:** Run the fixed cases; repeat only failures or cases affected by changes.
**Explain:** How do we tell whether a bad answer came from retrieval or generation?
**Dependencies:** 7. **Likely files:** `tests/eval_cases.json`,
`docs/evaluation.md`, `tests/test_rag.py`.
**Scope:** Medium, up to 3 files; no evaluation framework required.

### Checkpoint D: Reliable core

- [ ] Focused checks pass and evaluation limitations are recorded.
- [ ] You can reproduce one success, one no-evidence case, and one API failure.

## Step 9: Make the dashboard clear and usable

- [ ] Complete step 9.

**Build:** Polish the existing Streamlit flow: visible image/context, readable
answer, evidence panel, source links, and clear idle/running/error/completed states.
**Learn:** Information hierarchy, accessibility, responsive layout, loading/error
states, and communicating uncertainty without overwhelming the reader.
**Done when:**
- [ ] A new user can identify what to upload, submit a question, and find sources.
- [ ] Labels, keyboard access, readable contrast, and narrow-screen layout are checked.
- [ ] Every request state has clear feedback, without treating a collapsed panel
  as private storage or presenting the evidence summary as hidden thoughts.
**Verify:** Manual browser checks at desktop and narrow widths; one full demo run.
**Explain:** Which parts of the screen help someone judge the evidence?
**Dependencies:** 8. **Likely files:** `app.py`.
**Scope:** Small, 1 file; no new UI framework.

## Step 10: Document and rehearse the portfolio demonstration

- [ ] Complete step 10.

**Build:** A concise README with setup/run instructions, architecture, examples,
screenshots, source attribution, evaluation results, and known limitations.
Prepare a short walkthrough explaining your own decisions and tradeoffs.
**Learn:** Reproducible environments, technical writing, architecture explanation,
responsible claims, and presenting engineering evidence in a portfolio.
**Done when:**
- [ ] A clean environment can follow the README and run the demo with its own key.
- [ ] You can explain the full pipeline, demonstrate the three cases, and discuss
  one failure without reading the code line by line.
- [ ] The README states what is real, synthetic, measured, and unverified; source
  attribution and reuse notes are retained and secrets are excluded.
**Verify:** Follow the README from a clean environment and rehearse the walkthrough.
**Explain:** Why did we choose this architecture, and what would justify changing it?
**Dependencies:** 9. **Likely files:** `README.md`, `requirements.txt`,
`.gitignore`, a small number of screenshots under `docs/`.
**Scope:** Medium, up to 5 files. Public deployment/publication is separate.

### Final checkpoint

- [ ] All ten steps meet their completion criteria.
- [ ] You can explain upload, retrieval, generation, streaming, and evaluation.
- [ ] The demonstration is reproducible and its practical limits are explicit.

## Next action

Steps 1–5 are complete. GeoScan is publicly deployed at
[geoscan-morocco.vercel.app](https://geoscan-morocco.vercel.app), with approved
server-side Gemini credentials configured. A hosted assessment without an
access code completed; deployment details are in the [walkthrough](../docs/vercel.md).
Step 6 remains the next core feature: a streamed evidence summary and cited answer.

## First shared demo deployment

- [x] Load three real image examples with editable questions and synthetic context.
- [x] Add the requested subtle topographic pattern while preserving native controls.
- [x] Add an ASGI entry point, runtime asset configuration, and secret exclusions.
- [x] Bound hosted uploads; remove the initial shared-code gate at the author's request.
- [x] Publish the GeoScan production deployment at https://geoscan-morocco.vercel.app.
- [x] Publish the GeoScan interface and verify public health, controls, previews, sample upload, and comparison assets.
- [x] Configure Vercel secrets for Preview and Production with explicit permission; verify names/scopes without exposing values.
- [x] Verify GeoScan branding, removal of the access-code field, and a real hosted assessment without a code.
- [x] Complete hosted live RAG checks for a single image and the dated comparison.
- [ ] Complete longer-running reconnect, multi-instance upload, and load checks before wider sharing.
- [ ] Share the verified URL with reviewers when the author is ready.

**Learn:** UI callbacks and useful defaults, local decorative assets, ASGI versus
a UI script, server-side secrets, platform limits, and local versus hosted proof.
See the [walkthrough](../docs/vercel.md). Deployment does not mark the remaining
learning steps or all hosted reliability checks complete.

### Before deployment: one historical comparison

- [x] Add a same-area NASA MODIS image pair, dated 12 February 2023 and 19 February 2024.
- [x] Preserve originals, dates, checksums, attribution, and a dated NASA evidence excerpt.
- [x] Display both images and pass both with ordered dates to Gemini.
- [x] Include the case report explicitly with up to two semantic results; distinguish web and PDF citations.
- [x] Complete integration verification recorded in [comparison walkthrough](../docs/comparison.md): 96 offline tests and a live browser assessment. Model grounding limitations remain documented.

**Learn:** Multi-image requests, temporal metadata, evidence selection versus semantic retrieval, and why two RGB snapshots do not establish causality.
