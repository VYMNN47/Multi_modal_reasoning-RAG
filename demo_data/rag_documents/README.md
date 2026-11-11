# Moroccan agriculture reference collection for RAG

Eight real source PDFs, 125 physical PDF pages, accessed on 10 November 2026.
Seven documents are French; one research paper is English. This is reference
data only: no application code, embedding model, vector database, or index
has been created or changed.

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
future text chunk. Split recommended pages into short coherent paragraphs
within the selected embedding model's token limit, then evaluate retrieval
with French and English questions. Embeddings have not yet been generated.

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
