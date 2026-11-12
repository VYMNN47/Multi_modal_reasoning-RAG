# Step 5: Give Gemini retrieved evidence and validate its citations

The Streamlit form now runs the complete nonstreaming RAG path: retrieve
passages, send their text with the image and question, validate the response,
and show source/page links with the exact cited excerpts. The embedding model
and local index remain at **3,072 dimensions**. No dependency or API key changed.

## 1. What changed in the request

Previously, the vision model received an image, a question, and optional field
context. It now receives those inputs plus three selected reference excerpts
and their provenance. The vectors stay in our Python retrieval code; **we send
readable reference text to the vision model, not embedding vectors**.

The path is:

```text
Validate image/text and select English or Français
  → check whether an explicit NDVI calculation needs unavailable bands
    (show a local input-limit notice and stop if so)
  → rag.semantic_search(question, context)
  → model.reference_context(passages)
  → model.answer_image(image_png, question, context, passages, language)
  → validate the completed response and citations
  → keep answer and cited sources together in the session
  → show the assessment and expandable references
```

The application controls this sequence. Gemini does not independently open PDFs,
browse the web, inspect a vector database, or call a search tool. This is a fixed
RAG workflow, not an autonomous tool-selection loop.

**Learn:** Retrieval supplies useful context; generation uses that context to
answer the question. These are separate operations with separate failure modes.

## 2. Retrieve before generating

In `app.py`, an ordinary valid submission calls the existing `rag.semantic_search()` first.
It embeds the question/context with `gemini-embedding-001`, then compares that
vector with the 16 saved document vectors. The three highest-ranked passages
are selected. Existing passage embeddings are reused; there is no re-indexing.

The UI uses two native loading messages: finding references, then reviewing the
image. They describe actual work. A retrieval/key/quota/index failure stops the
request before the vision call; it does not silently produce an uncited fallback.

There is still no calibrated similarity cutoff. A high-ranking excerpt can be
irrelevant. The grounding prompt instructs Gemini to assess each excerpt's
applicability and disclose missing evidence instead of forcing a citation.

**Learn:** Top-k means the nearest candidates, not k confirmed supporting sources.

Before either API operation, `input_limit_notice()` recognizes explicit English
or French requests to calculate NDVI. This RGB-only form has no identified red
and near-infrared measurement bands. The app displays **Input limitation**, says
that no index was computed, and makes zero retrieval/generation calls. It is a
program-owned notice, not a Gemini answer or an agricultural citation. The small
recognition pattern is not a general intent classifier; other wording still
goes through the normal evidence-limited model path. Band requirements are
explained in [NASA's vegetation-index guide](https://science.nasa.gov/earth/earth-observatory/measuring-vegetation-ndvi-evi/).

## 3. Build reference context

`model.reference_context()` assigns short labels `S1`, `S2`, and `S3` to the
selected passages. It includes the source ID, physical PDF page, title, section,
reviewed text, original publication date/year, crops, geography, use notes, and
the flag showing numerical tables are not approved.

It leaves out vectors, similarity scores, input hashes, and duplicate embedding
text. Those fields help retrieval or caching; they are not supporting agronomic
evidence. The image remains a PNG part. Question, field context, and references
are serialized together as JSON in a text part of the same multimodal request.

The system instruction is separate from that data. Instructions appearing in
an image, user field context, or reference excerpt cannot legitimately change
the assistant's mission or output contract. This boundary is reinforced by
tests, not treated as a guarantee against every possible injection.

**Learn:** Good RAG context contains both the useful passage and the limits on
where it applies. A soil guide's publication year is not the satellite image date.

## 4. Give the model a grounded mission

The current instruction file is
[`agronomy_rag_v6.txt`](../prompts/agronomy_rag_v6.txt), loaded by `model.py`.
It asks for:

- Visible observations separated from reports, reference evidence, and hypotheses.
- Explicit uncertainty about crop identity, nutrients, soil chemistry, irrigation,
  and any ambiguous target field. Synthetic context stays labeled synthetic.
- Document-supported statements with inline reference labels such as `[S1]`.
- Respect for historical, regional, crop, and irrigated/rainfed scope.
- Qualitative next checks; no fertilizer products/rates or invented measurements.
- A clear evidence gap when excerpts do not help; a brief refusal for unrelated tasks.
- The selected answer language and a concise assessment with observations, evidence,
  and next checks. There is no private reasoning transcript in the output.

The prompt is versioned because changing these instructions can change behavior.
The original image-only instruction and the first RAG candidate are preserved for
comparison. See [the prompt history](../prompts/README.md).

The native **Answer language** control explicitly selects English or Français.
Python accepts only those two values and adds the selected language to the
trusted system instruction and request data. This avoids relying on inference
from the question's language, which drifted during live tests. It adds no API
call. The original user context is also displayed verbatim as plain text under
**Context supplied by you (unverified)**, keeping synthetic labels visible even
if a generated paraphrase omits them.

**Learn:** A system prompt directs behavior, but it does not itself prove factual
correctness, relevance, or resistance to all malicious inputs.

## 5. Separate the response contract from the visible answer

For this complete-response step, the API is asked for a small JSON envelope:

```json
{
  "scope": "agricultural",
  "answer": "A document-supported statement. [S1]"
}
```

`answer` contains the user-facing Markdown. `scope` is `agricultural` or
`out_of_scope`; it describes the task's subject, including agricultural questions
that cannot be fully answered from the supplied data. After checking the citations,
Python derives the evidence-use state shown by the UI:

| Status | Meaning | Citation requirement |
| --- | --- | --- |
| `used` | At least one selected excerpt is actually used | At least one supplied label |
| `insufficient` | No supplied excerpt was cited | No forced document citations |
| `out_of_scope` | The question is unrelated to this agricultural demo | No agricultural citations |

The model reports subject scope; Python computes citation use. Neither is a
calibrated confidence score. A valid citation does not establish that the entire
question has been answered or that a diagnosis is possible.
Structured output stabilizes syntax; Python still validates the values and
relationships. [Google's structured-output guidance](https://aistudio.google.com/docs/structured-output).

Only complete responses with a `STOP` finish reason are processed. Private
thought parts, if present, are ignored. Blocked, empty, truncated, malformed,
or inconsistent output raises a safe error and is not displayed as success.

Step 6 will introduce the planned XML streaming envelope and incremental parser.
This step deliberately handles a completed response first; the evidence rules,
reference registry, and citation-validation approach carry forward.

## 6. Make citations verifiable

`parse_grounded_answer()` checks the JSON object and its two fields. It then
checks every square-bracket reference against the labels supplied for this request.
Unknown/malformed labels, citations attached to an out-of-scope response, and model-written links, images,
HTML, or code blocks are rejected. It does not quietly strip an invalid citation.

For a valid `[S1]`, Python looks up its real passage and builds a link such as:

```text
[MA_PNTTA_NPK_155, PDF p. 2](https://www.agrimaroc.net/bulletins/btta_155.pdf#page=2)
```

The model does not choose that URL or invent its page number. The link comes
from the saved source metadata. Physical PDF pages can differ from printed page
numbers; the UI states which numbering system is used. PDF-viewer handling of
the `#page=` fragment can vary, so the page number remains visible in the label.

Only cited passages appear under **References cited**. Each panel includes its
title, year, crop coverage, geography, use note, original-PDF link, and the exact
excerpt supplied to Gemini. Two passages can share a source/page while showing
different reviewed sections.

**Important limit:** Validating a citation proves that it identifies supplied
evidence. It does not prove that the cited sentence is entailed by that evidence.
A real source can be attached to an unsupported claim. That is why we also read
the generated claims against their excerpts during evaluation.

## 7. Preserve session behavior and handle errors

The answer and its cited sources are saved together under the existing session
answer entry. A signature includes image hash, stripped question/context, answer
language, and prompt version. Ordinary reruns keep the same result without repeating retrieval
or generation. Changed inputs/prompt version clear it. Each deliberate valid
submission starts a fresh request, and a failed new submission clears old results.

The form retains the upload and text on failures. Credentials stay server-side
in the existing environment configuration. Uploads and ordinary user questions
are not written to disk. The evaluation report persists only our fixed public
images' identifiers and synthetic test inputs/outputs.

A valid submit normally makes one query token-count call, one query-embedding
call, and one vision-generation call. There are no hidden automatic retries.
Cached document vectors do not remove these per-question API calls.

**Learn:** Persisting a completed response in session state is different from
caching document embeddings. They save different work and have different lifetimes.

## 8. Try the end-to-end demo

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

Open <http://127.0.0.1:8501>. Upload the Doukkala PNG, ask what nitrogen/soil
evidence to check before attributing lighter wheat patches to a deficiency, and
label the wheat context synthetic. Click **Ask Gemini**, or use Ctrl+Enter in
the form. Read the answer, follow a citation, and expand its source panel.

Also try an exact-NDVI request from RGB or an unrelated programming question.
The former shows the local input-limit notice; the latter should decline the
unrelated task without agricultural citations. Provider capacity is variable;
a temporary service error is a failed request, not an agronomic finding.

## 9. Verify and understand the limits

```bash
python -m unittest discover -s tests -v
python -m tests.evaluate_answers
```

The first command is offline. The second deliberately uses API quota for the
ten cases fixed in `tests/answer_cases.json`: six scenario/language cases, missing
context, missing NDVI evidence, an unrelated task, and untrusted instructions.
The completed run contains nine actual vision responses and one local NDVI
notice. All 70 narrow checks passed; this is not a factual-accuracy percentage.
It saves completed cases and resumes unchanged successful cases after failures.
Reuse requires matching model/prompt, corpus index, fixtures, and image bytes.
Delete or move the report to force new API calls when checking provider drift,
unversioned validation changes, or request-setting changes.

The report records the actual excerpts, output, citation IDs, timings, and narrow
automated checks. Human review still checks claim support, image interpretation,
scope, language, and uncertainty. This is not an agronomic accuracy benchmark.

See [verification notes](step5_verification.md) for the final results and observed
failures. Try explaining why a citation can pass the ID/page check and still be
the wrong support for a particular sentence.
