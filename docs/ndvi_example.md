# Doukkala NDVI example verification

Initially checked locally on 14 November 2026. The complete NDVI workflow was
subsequently deployed on 15 November; see [production verification](ndvi_vercel_verification.md).

## Flow

Selecting **Doukkala: NDVI, 2024–2025** shows the Sentinel-2B previews for
20 February 2024 and 14 February 2025. The fixed table displays saved means
0.4668 and 0.4210, medians 0.4031 and 0.2924, and 262,140 common valid land pixels
with four excluded pixels. These cover a landscape containing nonvegetated land,
not a verified crop or individual parcel.

`GET /api/examples` reads and validates the saved summary without calling Gemini.
**Ask Gemini** reads it again, checks its pinned SHA-256 and dates, and sends the
bounded measurements with the two RGB images and a curated method excerpt.
There is one generation request, no query embedding, download, or raster
calculation. The author-only preparation/calculation scripts stay separate.
Client-supplied measurement fields are rejected; editable context cannot replace
the saved numeric packet.

## Checks

- All **104 offline tests pass**, covering catalog previews, the measured payload,
  checksum failures, SDK requests, language instructions, client-field rejection,
  deployment exclusions, and existing examples/uploads.
- `node --check assets/site.js` and `git diff --check` pass. The strict frontend
  audit reports zero findings. No runtime dependencies were added.
- Ten real Gemini cases using `doukkala-ndvi-v3` pass the focused numeric, scope,
  heading-language, and citation-placement probes. The cases include French,
  conflicting context, unavailable parcel/change-area statistics, causal claims,
  an unrelated question, and an attempted language override. The recorded outputs
  are in [ndvi_answers_v3.json](ndvi_answers_v3.json).
- A real local-browser submission completed with the correct values, three English
  sections, a method citation, and appropriate crop/cause limits. The source panel
  displays missing publication dates as “not stated” and crop scope as
  “not crop-specific.” The browser reported no warnings or errors.
- Switching to the original Doukkala RGB example hid the table; asking to calculate
  NDVI still returned the local input limitation. Switching back cleared that
  response. A whitespace question focused the question field and showed a correction
  message without sending a request. At a 360-pixel viewport, previews stacked, the table stayed within
  the page width, and date cells retained row-header attributes. The viewport
  override was reset afterward.

Screenshots: [saved measurements](screenshots/doukkala_ndvi_example.jpg) and
[completed explanation](screenshots/doukkala_ndvi_response.jpg).

## Limits

The focused prompt score is not an agronomic accuracy benchmark. Manual review
found uncited general method definitions in some live responses; the numeric
table remains independent application output. Model explanations still need
review, and citation membership does not prove claim support. The v8 prompt used
by the other examples was not changed or rerun through its full live suite.

Pixelwise NDVI change classification and area statistics have since been saved
offline; see the [calculation walkthrough](../demo_data/doukkala_change/README.md#ndvi-change-and-classification).
The coloured change view and display controls were added on 15 November 2026;
see the [change-view verification](ndvi_change_view.md). Class counts, hectares,
and valid-pixel percentages now appear in its legend. Integrating those statistics
with Gemini is now implemented; see the [change-statistics integration](ndvi_change_gemini.md).
Gemini receives the RGB previews and both saved summaries; raw bands, calculated rasters, source metadata, and author scripts remain
excluded from deployment uploads. Runtime packaging and the complete NDVI workflow
have now passed the [hosted checks](ndvi_vercel_verification.md).
