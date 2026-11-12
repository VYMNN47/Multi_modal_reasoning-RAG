# Moroccan agriculture reference collection for RAG

Eight real source PDFs, 125 physical PDF pages, accessed on 10 November 2026.
Seven documents are French; one research paper is English. This is reference
data. Step 3 added a reviewed passage set; step 4 embedded those 16 passages
and added a local cosine-search index. The original download ZIP is an archival
snapshot and does not include these prepared/index files.

## Contents

- `sources/`: eight original, unchanged PDFs.
- `text/`: page-separated text for each PDF. Form-feed characters separate pages.
- `pages.jsonl`: 125 page records, including provenance and physical page numbers.
- `recommended_pages.jsonl`: 50 selected soil, nutrition, crop-development, and
  water-management pages to start with. These are pages, not final embedding chunks.
- `manifest.json`: source URLs, original publication dates where verified, crop
  and geographic scope, recommended pages, extraction methods, and file hashes.
- `catalog.md`: a readable inventory and retrieval notes for each document.
- `checksums.sha256`: hashes of the original PDF files.
- `reviewed_sections.json`: selected prose transcriptions checked against 10
  physical PDF pages, with source-page hashes and review notes.
- `passages.jsonl`: 16 prepared passages across eight sources, with provenance,
  exact embedding text, and verified `gemini-embedding-001` token counts.
- `passage_review_report.json`: coverage of all 50 recommended pages, retaining
  pending-page, low-OCR, and unapproved numerical-table flags.
- `embedding_index.json`: `gemini-embedding-001` document vectors (3,072 numbers
  per passage), embedding settings, and the complete passage metadata. It
  contains no API key, uploaded images, or user-session queries.

## Coverage

- INRA wheat/barley guide (2014): crop stages, rotation, soils, nutrition, water.
- INRA lentil/chickpea/faba-bean guide (publication year not verified).
- INRA olive guide (2016 imprint): soil/foliar analysis, organic matter, nutrition.
- PNTTA 93 (June 2002): soil analysis and sampling.
- PNTTA 155 (August 2007): nitrogen, phosphorus, potassium and availability.
- PNTTA 62 (November 1999): wheat nitrogen management in bour and irrigated systems.
- PNTTA 70 (July 2000): soil-test interpretation for irrigated wheat and sugar beet
  in the Bas-Service Doukkala perimeter.
- Bouslihim et al. (2025), Scientific Data, DOI 10.1038/s41597-025-05699-x:
  Moroccan soil P/K mapping at 250 m resolution and its limitations.

## Extraction and verification

The three INRA guides are image-only scans. Their 100 pages were rendered
locally and OCRed with Tesseract 5.5.0, French, automatic page segmentation.
The other 25 pages were extracted with Poppler pdftotext using column-aware
reading-order settings. All page counts and source-file hashes were verified.
All eight title pages, three crop-guide fertilizer pages, and the olive guide's
2016 imprint were visually inspected. This is a spot check, not a full audit.

OCR errors, broken words, and table-reading errors remain possible. OCR word
confidence fields are extraction diagnostics, not confidence in agronomic claims.
Low-confidence covers, scanned pesticide tables, and unrelated sections were
left out of the recommended page subset. Full source PDFs and full extraction
remain available for reference. Numerical tables have not been fully verified.

Use `[source_id, PDF p. N]` for citations: the physical PDF page can differ from
the page number printed on a scanned sheet. Example: INRA cereal PDF page 14
shows printed page 11; legume PDF page 12 shows printed page 10; olive PDF
page 17 shows printed page 18.

## Retrieval scope

Keep source ID, year, crop, geography, page, and use notes attached to every
text chunk. Reviewed passages fit the selected embedding model's token limit;
step 4 now indexes and searches them with English/French questions. This
16-passage corpus is not a comprehensive agricultural knowledge base.

Step 3 prepares selected prose only: 40 recommended pages still await passage
review, and numerical fertilizer tables/rates remain excluded. Run `python rag.py`
from the project root to rebuild the current corpus. Unchanged inputs reuse saved
counts; changed inputs require token counting. The exact embedding payload
is the `embedding_text` field, including its title and section context.

Run `python rag.py embed` to create/refresh the index and
`python rag.py search "your agricultural question"` to inspect results without
the vision model. Unchanged document vectors rebuild offline; each query needs
online token counting and a query embedding. The original download manifest's
embedding status describes that archival preparation stage; current vectors
are in `embedding_index.json`.

All six fixed English/French scenario questions and one separate-context query
retrieved an expected passage at rank 1. Some supporting Doukkala passages
missed the top three. Unrelated probes still returned nearest neighbors; no
calibrated relevance cutoff or agronomic accuracy claim is made. See the
[step 4 verification](../../docs/step4_verification.md).

Step 5 connects those retrieved excerpts to the Streamlit image/question request.
Answers link only through the supplied reference registry; cited excerpts expose
their original dates, crop coverage, and scope. Citation membership is checked
in code; claim support still needs review. See [step 5](../../docs/step5.md).

Use historical guides as context. Their rates are not current blanket advice.
Keep elemental N/P/K, oxide P2O5/K2O, nutrient units, product kilograms,
per-tree doses, per-hectare doses, and laboratory test methods distinct.
The prototype should not prescribe rates from a satellite image.

Doukkala findings apply to their stated irrigated system, not every Moroccan
field. The 2025 national maps are predictions at 250 m; the paper is not a
soil test for any of our Sentinel-2 parcels. Map rasters and the underlying
private Fertimap samples were not downloaded.

## Source attribution and reuse metadata

Keep authors, institutions, original PDF notices, and source links with this
collection. The Scientific Data article states CC BY-NC-ND 4.0; the exact
license link is recorded in the manifest. No blanket open-reuse license was
verified for the INRA/PNTTA guides. Public access is not a blanket license
to republish the PDFs, extracted text, or a commercial corpus. Redistribution
and commercial-use permissions have not been assessed.
