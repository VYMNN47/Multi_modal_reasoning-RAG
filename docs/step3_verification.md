# Step 3 verification

Checked 12 November 2026. No new packages were required.

## Prepared data

- 16 passages from selected prose on 10 physical PDF pages, covering eight sources.
- Visual PDF checks: cereal pages 14/20; legume page 12; olive page 17; soil-analysis
  bulletin 93 page 1; NPK bulletin 155 pages 2/4; wheat-N bulletin 62 page 1;
  Doukkala bulletin 70 page 1; national soil-map paper page 1.
- Source URLs, dates (including the unknown legume year), crop/geography, source
  and page hashes, licenses, and limitations are retained in generated records.
- All eight original PDFs matched the existing manifest's SHA-256 hashes.
- Original PDFs, extracted text, page records, and source manifest were unchanged.

## Token checks

The selected model's tokenizer was checked with one short synthetic sentence,
then 16 `count_tokens` requests checked the exact prepared embedding inputs.
The largest was 218 tokens against the 2,048-token limit. No embedding vectors
were requested. See the saved counts in `passages.jsonl` and the generated report.

A second `python rag.py` run completed without network escalation and reported
zero token-count requests. The saved corpus also rebuilt identically in the
offline regression test with client creation blocked.

## Automated checks

`python -m unittest discover -s tests -v`: **35 tests passed**.

Checks include paragraph boundaries and oversized-paragraph rejection, stable
IDs, provenance/unknown-date retention, missing or changed source pages,
duplicates, exact counter input, changed-input count invalidation, invalid or
excessive counts, offline reproduction, the three demo cases' source/page
coverage, pending review flags, and preserving an existing output after token
verification fails. Existing image, form, and Gemini transport/error tests also
passed after extracting the shared client helper.

The report preserves 40 unreviewed recommended pages and three low-OCR page
flags. Numerical tables and rate examples are not approved or ingested into the
current passage set. No test was skipped or disabled.

## Limits

This is selected-prose source comparison, not a full review of all 125 pages or
expert validation of historical recommendations. Three English/French scenario
records check content coverage; retrieval quality has not been measured.
The original download ZIP remains an archival snapshot and does not include the
new prepared files. License metadata is preserved; public redistribution is not
part of this step.

No corpus embeddings, vector search, RAG answer generation, streaming, or new
vision API calls were performed. The Streamlit screen was not changed; existing
AppTest and transport checks cover the shared-client refactor.
