# Step 4 verification

Checked on 12 November 2026. Scope: document embeddings, the local index,
independent semantic search, and learning documentation. Streamlit and the
vision-model request were not changed.

## Configuration and persisted data

- Embedding model: `gemini-embedding-001`.
- Dimensions: 3,072 for both documents and queries.
- Document task: `RETRIEVAL_DOCUMENT`; query task: `RETRIEVAL_QUERY`.
- Corpus: 16 previously reviewed passages from 10 physical PDF pages across
  eight sources. Exact embedding inputs total 1,953 verified tokens; largest 218.
- Index: `demo_data/rag_documents/embedding_index.json`, 721,969 bytes. Each
  vector has 3,072 finite numbers and a norm approximately equal to 1. Source
  text, citations, dates, geographic scope, review notes, and reuse metadata
  match `passages.jsonl` exactly.
- Existing credentials, client settings, SDK, and Python dependencies are reused.
  No new package, vector database, or model training was needed.

## Automated checks

```bash
.venv/bin/python -m unittest discover -s tests -v
```

**53 tests passed**, including all 35 previous checks and 18 new retrieval checks.
They cover the actual SDK serialization through a simulated HTTP transport,
correct retrieval task types, exact inputs, query token limits, incomplete or
truncated responses, wrong-size/zero/nonfinite vectors, credential/quota/server
errors, timeouts, and connection failures. Provider details are not exposed and
automatic API retries are disabled by the shared client.

Temporary indexes exercise new-vector creation, unchanged reuse, selective
re-embedding after text changes, metadata-only refreshes, settings invalidation,
missing/stale/corrupt index rejection, source preservation, and cosine ranking.
A simulated failure preserves the existing index bytes. The real saved index
loads offline. The retrieval-metric calculation is checked with known ranks.

Streamlit's expected bare-mode `missing ScriptRunContext` notices appeared
during AppTest initialization; tests passed without suppressing warnings.

## Live API checks

```bash
.venv/bin/python rag.py embed
.venv/bin/python -m tests.evaluate_search
```

The first command successfully created **16 new document vectors in one batch
HTTP request**. The second made ten search calls: six existing scenario
questions (English/French), one question with separate synthetic field context,
and three unrelated probes. Each query used one token-count request and one
query-embedding request. Total successful live calls in step 4: **11 embedding
HTTP requests, including the document batch, and 10 token-count requests**.
No vision-generation request was made.

The complete questions, top-five passage IDs/text/scores/metadata, timings,
configuration, and input/index hashes are in
[step4_retrieval_test.json](step4_retrieval_test.json). Expected scenario IDs
were taken from the existing fixture before running retrieval.

| Relevant queries | Hit@3 | Mean expected-passage recall@3 | MRR@3 |
| --- | --- | --- | --- |
| Six English/French scenario questions + separate-context query | 7/7 | 0.810 | 1.000 |

An expected passage was rank 1 for every relevant query. Wheat and phosphorus
queries returned all their expected passages in the first three. The two full
Doukkala questions each returned two of three expected passages; the cereal
irrigation passage was absent from the top five. The separate-context question
returned one of three in the first three, with a second Doukkala passage at rank
4. This is incomplete evidence coverage, despite successful first-result hits.

The unrelated football, Python-list, and French travel questions still returned
nearest agricultural passages. Their highest scores were 0.529, 0.481, and 0.508;
the seven relevant-query top scores ranged from 0.707 to 0.767. No threshold
was fitted from these examples. Search output explicitly describes results as
nearest passages, not proof of relevance or diagnostic confidence.

Observed query times in this one run ranged from 0.499 to 0.754 seconds,
including token counting, embedding, index loading, and ranking. These observations
are not a latency guarantee or a performance benchmark. API success does not
independently establish billing tier, future capacity, or remaining quota.

## Offline reuse and integrity

An unchanged `python rag.py embed` run returned:

```json
{"passage_count": 16, "new_vectors": 0, "reused_vectors": 16, "embedding_requests": 0}
```

Loading/rebuilding the real index with `create_client` mocked also proved no
client was constructed. Its file hash stayed unchanged and matched the live
report; the report's corpus hash matched the current prepared passages.

All eight original PDF checksums still match the original manifest. Source PDFs,
extraction text, original manifest, and page records were not changed by step 4.
The passage review report now points to the separate index for embedding state;
its pending-page, OCR, and numerical-table review flags remain unchanged.

The actual local key was checked in memory against project source, learning
notes, tests, and generated text/JSON data; it was absent. `.env` remains mode
0600 and Git-ignored. No secret, uploaded image, or real user-session query was
added to the index or evaluation report.

## Practical limits

This small fixed demo set does not establish agronomic accuracy, compare models
or chunkers, measure a held-out retrieval benchmark, or calibrate abstention.
Forty recommended pages and numerical fertilizer tables still await review.
Semantic search must not be used to infer nutrient deficiency from RGB imagery.

The current ranker has no relevance filter, and supporting evidence can be
missed. Step 5 must check source scope and evidence sufficiency, disclose gaps,
and validate citations when integrating retrieval with generated answers.
Step 4 adds no RAG answer, streaming, UI change, or new browser/vision smoke test;
the unchanged application path remains covered by the automated checks.
