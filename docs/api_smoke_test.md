# Gemini API access checks

Checked on 10 November 2026 using the existing local key. No credentials are
included in these reports. This was a temporary smoke test, not app implementation.

| Model | Result | Evidence |
|---|---|---|
| gemini-embedding-001 | Passed | HTTP 200; 3,072 finite numerical values; vector norm 1.0. |
| gemini-3.8-flash | Temporarily unavailable | HTTP 503 UNAVAILABLE, high demand, on both attempts. Vision generation was not verified for this model. |
| gemini-3.5-flash-lite | Passed as a vision alternative | HTTP 200; normal STOP; image tokens explicitly reported in usage metadata. |

## Test inputs and observed output

- Embeddings: one short, synthetic sentence about soil testing and wheat nutrition,
  with RETRIEVAL_DOCUMENT task type. The agricultural reference corpus was not uploaded
  or embedded, and query/document retrieval quality has not been tested.
- Vision: the existing 512 x 512 Doukkala RGB PNG, with a prompt asking for two visible
  field patterns in at most 35 words, without nutrient diagnoses or prescriptions.
- Four inference requests were attempted: two to 3.8 Flash, one embedding request,
  and one request to 3.5 Flash-Lite. A separate model-catalog GET confirmed availability.

Observed 3.5 Flash-Lite answer:

> The satellite image shows two visible agricultural field patterns: rectangular grids of small, uniformly sized plots arranged in dense checkerboard blocks, and larger, elongated rectangular strips oriented parallel to each other.

The successful vision request reported 1,123 input tokens (1,089 image and 34 text),
37 output tokens, and 1,160 total tokens. It took approximately 1.94 seconds.
The embedding request took approximately 0.52 seconds. These single observations
are not a performance benchmark or a guarantee of future availability.

## Free-tier status

The user explicitly confirmed that the project for this key shows **Free tier**
in AI Studio. Google documents a standard free tier for both gemini-embedding-001
and gemini-3.5-flash-lite:

- https://aistudio.google.com/docs/pricing#gemini-embedding
- https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite

Independent billing-page verification was blocked by automatic approval review:
AI Studio redirected to accounts.google.com, and broader Google account access
had not been authorized. That restriction was not bypassed. Billing status is
therefore based on the user's confirmation, not an independently observed account
screen. A serviceTier value of standard in inference metadata does not establish
whether the project uses free or paid billing. No billing settings were changed.

## Scope and next step

- The key works for embeddings and for the tested vision alternative.
- 3.8 Flash remains unverified for image-input analysis because of provider capacity.
- No full RAG flow, streaming parser, retrieval evaluation, or agronomic accuracy test ran.
- No application code or project dependencies were added.
- Keep gemini-embedding-001 for embeddings and use 3.5 Flash-Lite as the verified
  vision candidate when implementing the first app call; 3.8 Flash can be retested later.

Raw redacted results: [api_smoke_test.json](api_smoke_test.json).
Available model metadata: [api_available_models.json](api_available_models.json).
