# Gemini timeout and one automatic retry

Added on 13 November 2026. This policy uses the existing Google SDK; no package,
model, prompt, API key, or embedding dimensions changed.

## What changed and why

`model.create_client()` now sets a **120,000 ms network timeout**, up from
60,000 ms. A slow request has more time before the transport reports a timeout.
The SDK applies this value to network operations and sends a server-timeout
header. It is not a strict two-minute deadline for the entire assessment.

The same client configures `HttpRetryOptions` with **`attempts=2`**. Attempts
include the initial request, so this permits exactly **one automatic retry**.
There is no additional retry loop in Streamlit, retrieval, or answer generation.
Layering a second loop on the SDK would multiply requests rather than preserve
this limit.

The retry pauses **1–2 seconds**, using an initial delay of 1, maximum delay of
2, and jitter of 1. The randomized pause helps avoid synchronized retries.
With only one retry there is only one pause, not a series of growing waits.
This follows [Google's bounded-retry guidance](https://aistudio.google.com/docs/troubleshooting#retry-strategy).

## Which failures are eligible

| Failure | Automatic behavior |
| --- | --- |
| Network connect/read/write/pool timeout | Retry once |
| Connection establishment failure (`ConnectError`) | Retry once |
| HTTP 408, 500, 502, 503, 504 | Retry once |
| HTTP 400, 401, 403, 404, 429, or other unlisted status | Stop immediately |
| Other transport errors outside the SDK's eligible classes | Stop immediately |
| A completed response with invalid citations/JSON, blocked or truncated output | Stop after validation; no generation retry |

The HTTP list is explicit because the SDK's defaults also retry 429. This demo
leaves quota/rate-limit errors visible rather than immediately spending another
attempt against a possibly exhausted allowance. A key, permission, input, or
model-access failure also needs correction rather than repetition.

When both timeout attempts fail, the displayed message says the automatic retry
was already attempted. HTTP 408 is handled as a temporary service failure,
rather than an input/key rejection. Existing validation and safe error messages
remain in place.

## How this affects RAG

The shared client is used for query token counting, query/document embeddings,
and vision generation. **The failed API call is retried**, not the entire form
or retrieval pipeline. For example, if token counting succeeds and embedding
times out, only embedding is repeated. The SDK resends the same request payload.

A normal image assessment makes three HTTP calls: count tokens, embed the query,
then generate the answer. If each call needs its retry and eventually succeeds,
the total can reach six attempts. These can consume additional quota. A timeout
does not prove Google stopped processing the original request.

Ordinary Streamlit reruns still reuse a completed answer. Citation checks still
run before success is shown; retrying does not relax evidence requirements.

## Hosting limit and verification

Vercel's configured function lifetime remains **300 seconds**. Several slow
calls with retries can exceed that limit, and operation timeouts are not a hard
wall-clock budget. This change improves recovery opportunities; it does not
guarantee hosted completion or solve in-memory session reconnection. Run the
hosted checks in [the deployment guide](vercel.md) before sharing a URL.

Offline tests use the real pinned SDK and a simulated HTTP transport. They
exercise a temporary failure followed by success, repeated failures stopping
after two attempts, excluded errors stopping after one, the 1–2 second retry
pause, identical retried payloads, and the actual 120-second transport options
and server header. Embedding tests also verify that a successful earlier query
phase is not repeated. Tests record SDK waits instead of sleeping.
The complete offline suite passed **86 tests** after this change; `git diff
--check` and the edited documentation's local-link checks also passed.

No live Gemini API call or outage was induced to test retries. Earlier live
reports used the previous policy and remain historical evidence, not a new
measurement of service reliability, quota, billing, or agronomic accuracy.
The live evaluator can reuse successful saved cases; move its report aside
before running it if you deliberately want fresh API calls under this policy.
