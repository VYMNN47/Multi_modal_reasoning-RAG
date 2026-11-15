# Agronomic prompt history

Default runtime prompt: **`agronomy_rag_v8.txt`**, version `agronomy-rag-v8` in `model.py`.
The measured Doukkala example uses **`doukkala_ndvi_v9.txt`**, version
`doukkala-ndvi-v9`; other examples keep the default prompt.
Restart/rerun after editing the loaded prompt and update its version when
promoting a behavioral change so session answers are invalidated.

The original [image-only instruction](step2_image_only.txt) is a historical
checkpoint. It has no retrieval/citation contract and is not a compatible
drop-in replacement for the current model, app, and tests.

## Candidate record

| Candidate | Result and reason for the next change |
| --- | --- |
| [v1](agronomy_rag_v1.txt) | Added reference labels and a model-reported evidence-use status. Seven accepted outputs preceded a rejected NDVI/status contradiction; manual review found misplaced citations and scope overstatements. [Report](../docs/step5_answers_v1.json). |
| [v2](agronomy_rag_v2.txt) | Tightened claim placement and crop/date/region limits. Nine accepted outputs, but another status contradiction and a French question answered in English. [Report](../docs/step5_answers_v2.json). |
| [v3](agronomy_rag_v3.txt) | Simplified the envelope to subject scope plus answer; Python derives citation use. Language drift and an output-format rejection remained. [Report](../docs/step5_answers_v3.json). |
| [v4](agronomy_rag_v4.txt) | Kept the question last in the request and checked English as well as French prose. One English scenario was still answered in French. Citation parsing also corrected a false rejection of a citation followed by a parenthetical year. [Report](../docs/step5_answers_v4.json). |
| [v5](agronomy_rag_v5.txt) | Added an explicit validated language choice and a trusted system suffix. Language probes passed; exact-NDVI requests still attracted irrelevant nutrition citations. [Report](../docs/step5_answers_v5.json). |
| [v6](agronomy_rag_v6.txt) | The app handles recognized unsupported NDVI calculations before retrieval/model calls, labeled as local input limitations. Nine real vision answers plus one local notice passed the ten-case check set. [Current report](../docs/step5_answers_test.json). |
| [v7](agronomy_rag_v7.txt) | Adds conditional dated-pair instructions and real web article citations. Both lint scores are 81.5; diff reports no heuristic risks. Two focused live generation checks and one real browser comparison completed. Manual review found unnecessary fertilizer background in comparison answers and an incorrectly cited visual observation in the single-image probe. The full v6 live suite has not been repeated; no equal-or-better quality score is claimed. [Focused report](../docs/comparison_live_check.json). |
| [v8](agronomy_rag_v8.txt) | Allows two custom uploads without inventing acquisition dates, a shared footprint, or before/after order. Existing dated-comparison, evidence, citation, and output rules are preserved. Lint remains 81.5; the v7→v8 diff reports no heuristic risks. SDK tests verify ordered image bytes and absent dates for an undated pair. A real browser assessment of two custom uploads preserved the image labels and unknown-date/footprint limits; some generic claims still attracted weakly placed citations. [Focused pair check](../docs/two_image_live_check.json). The full ten-case live suite has not been repeated; no equal-or-better quality score is claimed. |

The fixed questions, source expectations, and user-facing review goals were
written before live generation. Explicit answer-language settings were added
to preserve the intended language, not to change the questions or expected
sources. Failed candidates and provider attempts remain recorded.

The current prompt keeps visible observations, user reports, reference claims,
and hypotheses separate. It requires qualitative next checks, source scope,
inline labels, and no invented measurements or fertilizer doses. The app also
shows the original unverified user context verbatim; a model paraphrase cannot
hide the synthetic label from the interface.

## Evaluation and rollback

Prompt lint and diffs are recorded under `docs/step5_prompt_*`. The score artifact
checks the seven recorded Boolean probes for each fixed case. It is a contract
and behavior baseline, **not factual or agronomic accuracy**. Source-label
validation does not establish claim entailment; manual review still matters.
See [verification and remaining limits](../docs/step5_verification.md).
The old image-only prompt has no comparable RAG score, so no percentage
improvement over it is claimed.
The v6 report remains the completed single-image baseline; it does not validate
v7 or v8. The comparison walkthrough records v7's focused checks and remaining
grounding limits. A valid source label still cannot establish claim support.

Rollback point: the step 4 application with image-only answers and independent
retrieval. Reverting requires the matching model, app, and test changes along
with the prompt snapshot, while preserving the shared client used by retrieval.
Swapping only the prompt breaks the response contract.

## Saved Doukkala NDVI results

The NDVI prompt interprets two checksum-verified application summaries alongside two
dated RGB previews. It does not calculate NDVI or accept measurements from editable
context. This case supplies only its NDVI method excerpt; it does not embed a
query or retrieve unrelated fertilizer passages.

| Candidate | Result |
| --- | --- |
| [NDVI v1](doukkala_ndvi_v1.txt) | The first browser probe preserved the numbers, but ran section labels together and cited unrelated retrieved fertilizer passages. The case was restricted to its method reference. |
| [NDVI v2](doukkala_ndvi_v2.txt) | The initial numeric/scope probes passed. Manual review found a French heading in an English answer; adding that contract check gives 9/10. [Recorded answers](../docs/ndvi_answers_v2.json). |
| [NDVI v3](doukkala_ndvi_v3.txt) | The trusted system suffix now supplies only the selected language's headings. All ten live numeric, scope, heading, and citation-placement probes pass. Lint remains 80/100; the v2→v3 text diff reports no heuristic risks. [Recorded answers](../docs/ndvi_answers_v3.json), [verification](../docs/ndvi_example.md). |
| [NDVI v4](doukkala_ndvi_v4.txt) through [v7](doukkala_ndvi_v7.txt) | Added the saved classification contract. Live and manual review exposed citation placement, rounding, total-area transcription and class-label language issues. Candidate outputs remain in `docs/ndvi_answers_v4.json` through `docs/ndvi_answers_v7.json`. Total-area and French-label checks were strengthened after manual review. |
| [NDVI v8](doukkala_ndvi_v8.txt) | Added an application-formatted display packet and language-specific class labels. Nine of ten live cases passed; a conflicting language request was incorrectly declined. [Recorded answers](../docs/ndvi_answers_v8.json). |
| [NDVI v9](doukkala_ndvi_v9.txt) | Separates topic scope from answer-language selection. All ten final live cases pass, including saved class areas/percentages, reported hectare totals, French labels and conflicting context/language. One temporary provider 503 was retried; the attempt is retained. The text-contract score is 1.0 versus 0.965 for the integrated v3 baseline under the current probes; this is not agronomic accuracy. [Recorded answers](../docs/ndvi_answers_v9.json), [verification](../docs/ndvi_change_gemini.md). |

The questions were fixed before generation. The heading check was strengthened
after the v2 manual failure and applied to both versions. The scorer checks text
contracts, not agronomic accuracy. Manual review still found some uncited method
definitions in v3; source-label validation cannot guarantee citation completeness
or entailment. The unchanged v8 live suite was not repeated.

The per-date-only checkpoint is v3 with its matching loader/instruction assembly;
it does not explain change-class measurements. Preserve the saved data and
measurement validation when rolling back this integration. Earlier candidate
snapshots retain their documented limitations.
