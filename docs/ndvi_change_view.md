# Doukkala NDVI change view

Initially verified locally on 15 November 2026. The subsequent full NDVI release
is now deployed; see [production verification](ndvi_vercel_verification.md).

The measured Doukkala example now offers native Satellite images / NDVI change
radio controls. The change view shows a lossless class image, actual acquisition
dates, after-minus-before direction, and a four-entry legend with the ±0.05 demo
tolerance. Green is increased NDVI, orange decreased, grey stable within tolerance,
and a transparent/hatched key identifies excluded pixels.

Each class now includes its saved pixel count, projected-grid hectares, and share
of valid pixels. The percentage denominator is 262,140 shared valid land pixels,
covering 2,621.40 ha; the four excluded pixels (0.04 ha) have no class percentage.
The sample includes nonvegetated surfaces, so these are not verified crop areas.

| Class | Pixels | Area | Share of valid pixels |
| --- | ---: | ---: | ---: |
| Increased NDVI | 45,129 | 451.29 ha | 17.22% |
| Stable NDVI | 127,486 | 1,274.86 ha | 48.63% |
| Decreased NDVI | 89,525 | 895.25 ha | 34.15% |

The author command `uv run prepare_doukkala_change_view.py` reads the existing
classification and summary. Pillow maps each class code to one RGBA colour in
the original row/column order without resampling. The palette in the generated
`assets/doukkala-change/view.json` drives both the PNG and browser legend. The
script copies the class metrics and valid coverage from the saved summary,
verifies source hashes, dates, dimensions, no-data and counts, then stages
both assets together and refuses to overwrite existing output. Source bands,
per-date NDVI, change rasters, their summaries, and case metadata stayed unchanged.

The app returns bounded display metadata only for this example. The assets ship
through the existing Vercel `assets/**` include; raw TIFFs and author scripts
remain excluded. There are no new dependencies, routes, external tile services,
NDVI computations, or model calls in the view toggle. The existing question,
context, language, and answer are retained when only the display mode changes.
Choosing another source resets the mode and removes the old change figure/legend.

## Verification

- **113 main tests passed**, including six renderer/artifact checks and one
  catalog/asset check. The PNG's every pixel matches the saved class code and
  palette, all four excluded pixels have zero alpha, and class colour counts equal
  the saved classification counts. Provenance/image hashes and dates match.
  Regenerating metadata copies the saved areas/counts/percentages exactly, class
  percentages sum to 100 using the shared-valid denominator, and the API exposes
  these values only for Doukkala. The existing PNG remained byte-for-byte identical.
- `node --check assets/site.js` and `git diff --check` passed. The strict frontend
  audit reported no findings.
- A real browser switched between both views using clicks and native arrow keys.
  The question survived display changes. Another example and the empty upload
  state hid the toggle, figure, legend and date table correctly. Returning to
  Doukkala reset to satellite imagery. The native source dropdown opened and
  closed with keyboard input. Both answer-language settings retained the view.
- At a 1280 × 1000 desktop test viewport, the map rendered at 512 × 512 beside
  the legend. At 360 × 800, it rendered at 313 × 313 with the legend below it;
  the document had no horizontal overflow. The temporary viewport was reset.
- An isolated local test server deliberately supplied a missing PNG URL. The
  visible error explained recovery through Satellite images; switching back
  restored both RGB previews. The test server/tab were closed and the real asset
  was never modified. No Gemini request was made during browser verification.
- The normal preview showed no console errors, warnings, or CSP violations.

Screenshots: [desktop](screenshots/doukkala_change_view_desktop.jpg) and
[narrow legend](screenshots/doukkala_change_view_narrow.jpg).

## Remaining limits

This is a fixed-footprint scientific raster preview. The ±0.05 threshold remains
a demonstration tolerance; stable does not prove unchanged crops or land. SCL,
atmospheric and registration uncertainty still apply. The subsequent
[change-statistics integration](ndvi_change_gemini.md) now supplies both verified
summaries to Gemini. This display increment itself did not include a new live
Gemini evaluation or production deployment.
