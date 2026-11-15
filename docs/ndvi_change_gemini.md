# Doukkala change statistics in Ask Gemini

Implemented and deployed on 15 November 2026. The production Doukkala workflow
and real English/French responses passed the [hosted checks](ndvi_vercel_verification.md).

Selecting **Doukkala: NDVI, 2024–2025** loads the saved measurements without a
Gemini call. **Ask Gemini** reads both summaries again and sends the two dated
RGB previews, the verified NDVI and change measurements, editable user context,
and the existing NDVI method excerpt in one generation request. There is no
band download, raster calculation, query embedding or unrelated soil retrieval.
The updated default question asks for increased, decreased and stable hectares,
percentages and interpretation limits. Either display mode uses this same flow.

## Data and validation

`case.json` now pins `change/summary.json` as well as the per-date NDVI summary.
The loader verifies both SHA-256 checksums and the change summary's reference to
the original NDVI summary. `model.ndvi_context` validates the nested change object:
dates and shared mask counts must match, all numbers must be finite, the three
class codes/labels must be unique and valid, counts must cover the valid sample,
and hectares/percentages must agree with counts and projected pixel area.

The model receives only bounded method, coverage and class fields under
`ndvi_results.change`. Raw filenames, grids and provenance hashes are removed.
`ndvi_change_display` supplies formatted coverage totals, class counts, hectares
and rounded percentages with class labels for the configured answer language.
This avoids asking Gemini to perform the rounding or area arithmetic itself.
The server rejects client-supplied measurement fields. Conflicting editable
context does not replace the saved packet.

The only data-file edit is to case metadata: summary pointers/checksums and the
default question/context. Source bands, masks, rasters, both analytical summaries,
and the existing change display assets are unchanged. Deployment packaging now
includes the change JSON summary; TIFFs, raw source metadata, author commands and
secrets remain excluded. The model request does not include the coloured PNG.

## Prompt and checks

The measured case uses `doukkala-ndvi-v9`; other examples retain
`agronomy-rag-v8`. Application measurements are distinct from method citations.
Class percentages describe the shared valid land sample, not verified crop area.
The ±0.05 value is a demo tolerance in NDVI units; stable includes both boundaries
and does not prove unchanged crops or land use. Crop identity, yield loss and
causes are not established by these two snapshots.

The fixed live questions cover both languages, the three class figures,
denominator, excluded pixels, calculation requests, conflicting user numbers,
crop identity, parcel boundaries, causal claims, topic scope and language override.
Manual review strengthened the checks for wrong hectare totals and untranslated
class labels. Earlier candidate outputs remain recorded under `docs/ndvi_answers_v4.json`
through `docs/ndvi_answers_v8.json`; the original comparison is in
`docs/ndvi_change_answers_baseline.json`. These are behavioral probes, not an
agronomic accuracy benchmark. The final input packet also includes formatted
display strings, so this is an integrated-feature comparison, not a prompt-only experiment.

Offline verification covers SDK payloads, invalid statistics, changed/missing
summaries, input linkage, client-field rejection, other-example isolation, runtime
packaging and the area checker itself. Run:

```bash
.venv/bin/python -m unittest discover -s tests -q
node --check assets/site.js
# Explicit live check; uses Gemini quota and reuses unchanged passing results:
.venv/bin/python -m tests.evaluate_ndvi_answers
```

Changing this integration requires its matching loader, case metadata, prompt and
tests. Keep the source data and integrity checks intact. The previous per-date-only
v3 prompt has no contract for explaining classified change areas.

## Verification

Final verification: **118 offline tests passed** and **10/10 live cases passed**.
One final case was interrupted by a temporary Gemini 503; the unchanged retry
passed and the provider attempt remains in the report. The toolkit's text-contract
score is 1.0 (integrated v3 baseline: 0.965); the additional area, language, scope
and citation-placement probes also pass. The stronger expectations were applied
to both sets of recorded outputs for the text-score comparison.
Prompt lint is 80/100. The diff heuristic flags an extra output-format signal,
but the JSON envelope remains exactly `scope` and `answer`, covered by parser
and integration tests. The prompt estimate increased by 538 tokens; no model,
output-token limit or additional generation request was added.

The real Ask Gemini button completed with the expected three areas/percentages,
2,621.40 ha valid coverage and 0.04 ha excluded coverage. Loading disabled inputs
and completion restored them. See the [real browser response](screenshots/doukkala_ndvi_change_response.jpg).
The 1280 × 1000 and 360 × 800 layouts were checked; the narrow document had no
horizontal overflow. Native arrow-key view changes preserved the answer. The
viewport override was reset and the console showed no warnings or errors.

## Limits

Gemini can still misquote or misinterpret inputs; the independent displayed
measurements remain the factual record. Valid citations do not prove entailment.
The browser response still used a method citation for an uncertainty claim and
described class differences broadly; the legend's stable-within-tolerance rule
remains authoritative. Generated explanations need review.
SCL errors, atmospheric differences, registration uncertainty and the unvalidated
demo tolerance remain. No field validation or crop-area certification was performed.
