# Agronomic prompt history

Runtime prompt: **`agronomy_rag_v6.txt`**, version `agronomy-rag-v6` in `model.py`.
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

Rollback point: the step 4 application with image-only answers and independent
retrieval. Reverting requires the matching model, app, and test changes along
with the prompt snapshot, while preserving the shared client used by retrieval.
Swapping only the prompt breaks the response contract.
