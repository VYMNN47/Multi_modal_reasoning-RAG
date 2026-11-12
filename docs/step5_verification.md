# Step 5 verification

Checked on 12 November 2026. The app now retrieves reference text before a
multimodal answer and validates citations before rendering it. The current
configuration is `gemini-3.5-flash-lite`, prompt `agronomy-rag-v6`, top three
passages, and `gemini-embedding-001` at **3,072 dimensions**. No dependency,
credential, vector database, or embedding-index change was required.

## Automated checks

```bash
.venv/bin/python -m unittest discover -s tests -v
```

**73 tests passed** in the final run, including all previous image, preparation,
and semantic-search coverage. New checks exercise the actual SDK request shape
through a simulated transport, bounded reference context, explicit language,
structured-output validation, citation aliases, source/page URLs, and malformed
or invented references. A citation followed by a space and parenthetical year
is accepted as prose; a model-written Markdown link is rejected.

Streamlit AppTest verifies retrieval before generation, no vision call after
retrieval failure, paired answer/source state, no duplicate calls on ordinary
reruns, stale-result invalidation, and preservation of inputs on errors. It also
checks unverified context display and the local NDVI notice without either API
operation. Expected bare-mode ScriptRunContext warnings were not suppressed.
The live evaluator's recovery/cache logic is tested with failures and changed
inputs, and its narrow answer checks are tested against negative examples.

## Actual model and capability checks

The ten questions and expected sources in [answer_cases.json](../tests/answer_cases.json)
were fixed before live generation: wheat/nitrogen, calcareous-soil phosphorus,
and Doukkala irrigation scenarios in English/French, plus missing context,
an exact-NDVI request, unrelated Python, and injected instructions.

[The completed current report](step5_answers_test.json) contains **nine actual
vision-model answers and one local input-limit notice**. All ten cases passed
their seven narrow checks, for **70 passing Boolean checks**. These check expected
evidence state, an expected source where applicable, supplied citation/page
membership, absence of an injected marker, absence of a numerical fertilizer
rate in the tested syntax, and simple English/French prose probes. Inapplicable
language/source checks are vacuously true; this is not 70 independent agronomic
judgments or a factual-accuracy score.

Four HTTP 503 generation attempts occurred for this candidate before completion.
They remain in `stopped_attempts`; no automatic API retries were enabled.
Successful unchanged cases were resumed while pending cases were retried in
later explicit evaluator runs. Earlier prompt candidates and their observed
failures remain in [the prompt history](../prompts/README.md) and the v1–v5
report snapshots. No failed answer check was silently promoted.

The NDVI fixture takes the program-owned `input_limit` path. It states that no
index was computed and sends no retrieval or vision request. The recognition
pattern covers explicit English/French calculation requests, not all possible
wording. Other questions still rely on the evidence-limited model behavior.

Each report records inputs, prepared-image hash, model/prompt/index identifiers,
supplied excerpts, displayed answer, cited passage IDs, and elapsed time. Resume
keys cover prompt, model, index, fixtures, and image bytes. Move/delete the report
to force fresh calls after unversioned request-code changes or provider drift.
Observed timings and successful access do not establish future quota or capacity.

## Manual review and remaining limits

The final outputs were read against their supplied excerpts. They separate
visible patterns from reports and hypotheses, suggest qualitative checks, and
do not establish a field diagnosis or prescribe a fertilizer dose. The unrelated
task was declined without agricultural citations; tested injected instructions
did not produce their marker, invented source, or URL.

There are still grounding limits. A model can attach a real reference to a
generic check, omit a synthetic label in a paraphrase, or use a regional/crop
study as background without sufficiently emphasizing its narrower applicability.
For example, the French wheat case references Doukkala evidence while the user
context names Gharb. Citation validation proves membership, **not entailment or
local applicability**. Original context is therefore shown verbatim as unverified
plain text; cited panels expose year, crops, geography, use notes, and exact text.
These controls aid review; they do not make the model an agronomic authority.
The small word-set language probes are also not language certification.

## Browser verification

The real local app was exercised with the public Tadla PNG and synthetic context:

- Empty submission displayed image/question errors.
- An explicit French NDVI request showed a French **Input limitation** notice,
  with no model-success alert or cited sources.
- Changing the answer language cleared that result.
- A phosphorus question in English completed real retrieval and vision generation,
  citing two NPK page-4 excerpts and the 2025 soil-map paper's page-1 excerpt.
- The original synthetic context remained visible, and an expanded source showed
  its 2007 date, general crop scope, geographic note, PDF link, and exact excerpt.
- Ctrl+Enter submitted the form. Native source disclosures were operable.
- At 320 × 900, document/body width stayed 320 px and the main region's
  scrollWidth/clientWidth were both 310 px. Answer links and source text wrapped.
  The temporary viewport override was reset afterward.

Screenshots: [desktop answer/sources](screenshots/step5_rag_sources.png),
[narrow answer](screenshots/step5_rag_narrow.png), and
[narrow source panel](screenshots/step5_rag_narrow_sources.png).
Recorded console warnings/errors relate to deliberate earlier server stops and
restarts. None were recorded after 21:01 UTC in the final browser run.
Original PDF destinations/viewer page-fragment behavior were not reopened.

The generic UI static audit returned zero findings after excluding installed
`.venv` packages from its scan. It scans web source formats, not this Python
Streamlit interface, so that result is not UI certification. DESIGN.md lint
reported zero errors/warnings. Real browser and AppTest checks supply the
relevant interface evidence. Prompt lint/diffs are recorded under
`step5_prompt_*`; the exact-match score artifact compares the existing narrow
Boolean checks and does not evaluate agronomic correctness.

## Integrity and scope

All eight original PDF hashes match the download manifest. Prepared passages and
the saved embedding index match the step-4 live report hashes; the current prompt
hash matches the step-5 report. `.env` remains mode 0600 and Git-ignored, and an
in-memory scan found no actual credential in project text/data artifacts.
`git diff --check` passed. Existing uncommitted step-3/4 work was preserved;
no staging or commit was performed.

No streaming, private reasoning transcript, automatic web research, model
training, source-table approval, public deployment, or new dependency was added.
Forty recommended PDF pages and numerical tables still await review. Step 6 is
the next requested slice: a streamed evidence summary and cited final answer.
