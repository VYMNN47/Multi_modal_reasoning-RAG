# A dated satellite comparison

Choose **Casablanca: Drought, 2023–2024** in the example picker. The left image
was acquired on 12 February 2023 by Aqua/MODIS; the right image on 19 February
2024 by Terra/MODIS. They cover the same regional area, 372 days apart, during
the winter rainy season. The original JPEGs and checksums are in
[the case metadata](../demo_data/comparison/case.json).

NASA's [Drought Parches Morocco](https://science.nasa.gov/earth/earth-observatory/drought-parches-morocco-152467/)
reports that drought already present in 2023 worsened in 2024, with rainfall
deficits, unusual warmth, browner vegetation, depleted reservoirs, and reduced
planting and irrigation. That report supplies the historical explanation;
two pictures alone cannot establish the cause or reconstruct every event
between their dates.

## 1. Keep dates and provenance with the images

`demo_data/comparison/case.json` holds the filenames, ordered acquisition dates,
satellites, instrument, source URLs, dimensions, checksums, suggested question,
context, and a short paraphrase of the NASA report. These are curated application
metadata, separate from editable user context. The originals are unchanged.

**Learn:** A useful comparison is an evidence package: images plus dates,
location, sensor information, and an independent account of what happened.

## 2. Send two images, not a screenshot of the page

The UI previews both images in native columns. `preview_image()` reuses the
same validation, RGB conversion, metadata removal, and inline thumbnail path
as single-image examples. The model receives the two full RGB PNGs in date
order as separate SDK image parts, followed by JSON containing both dates,
the question, context, and reference excerpts. Combined PNG size is limited
to 10 MiB. Missing, invalid, equal, or reversed dates are rejected before a
model call.

**Learn:** The browser layout and the model payload are different. Multimodal
APIs can receive multiple image parts, with text telling the model what each
part represents.

## 3. Include the document that actually explains this event

The chosen NASA excerpt is included explicitly for this case, alongside up
to two ordinary cosine-search results. It is not a new embedded document and
is not claimed to have been discovered by semantic search. The existing
16-passage, 3,072-dimensional index stays unchanged. Other examples keep their
normal top-three retrieval path.

The NASA source has `source_format: "web"` and no PDF page. Python validates
the model's citation label and creates the saved article link. PDF citations
keep their existing page links. The references panel shows the appropriate
source type, publication date, scope, and exact excerpt supplied to Gemini.

**Learn:** Retrieval selects evidence; generation interprets it. A directly
selected case source is useful when demonstrating a known historical event,
but must be distinguished from an embedding-search result.

## 4. Explain change conservatively

Prompt v7 asks for dated visual differences, document-supported explanations,
and missing evidence. Different satellites, overpasses, display processing,
clouds, and land management can affect appearance. The 2023 scene is already
drought-affected. These regional RGB views cannot establish parcel crop
identity, exact crop losses, NDVI, or fertilizer needs. There is no pixelwise
change algorithm, field segmentation, or scientifically verified image
registration in this example.

**Learn:** A temporal comparison supports observation. Causal attribution
requires independent evidence, and field decisions still require field data.

The answer cache includes both image hashes and the entire curated case,
including dates and the evidence excerpt, as well as the existing text,
language, and prompt version. An answer therefore clears when either image
or its evidence changes.

No deployment is performed by adding this example. The case JSON and both
JPEGs are included in Vercel's runtime asset configuration. Verification
results and remaining limits are recorded below.

## Verification

On 13 November 2026, all **96 offline tests** passed, including the ASGI
HTTP/WebSocket smoke test, both-image payload ordering and exact pixel checks,
date and size rejection, case evidence selection, image/evidence cache
invalidation, failed-image loading, existing examples, and mixed web/PDF links.
The installed dependency check also passed. Original bytes, SHA-256 hashes,
dimensions, and the 372-day interval were verified.

Two focused live generation requests completed: the dated pair and one existing
single-image question, using saved excerpts. Their output is preserved in
[the live report](comparison_live_check.json). A separate real browser submission
completed live embedding retrieval and two-image generation, displayed NASA
citations, and showed the article publication date and original-report link
without a PDF page. The browser comparison described greenness loss and
attributed the drought explanation to NASA. Desktop screenshots are saved in
`docs/screenshots/comparison_desktop.jpg` and `comparison_result.jpg`.

These are integration checks, not a full prompt quality pass. Manual review
found unnecessary fertilizer background in comparison answers. The single-image
probe attached document citations to a visual observation and omitted the
requested synthetic-context label in its prose (the app still shows the
original context separately). These are observed model instruction failures,
not established v7 regressions. The completed ten-case v6 live evaluation is
preserved and has not been repeated for v7. Prompt lint remained 81.5, with
zero heuristic diff risks; those numbers do not measure answer accuracy.

The parser validates citation membership and URLs, not whether every sentence
is entailed by an excerpt. Inspect claims against the visible source text.
No Vercel deployment or scientific image-registration check was performed.
