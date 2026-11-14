# Doukkala two-date vegetation data and NDVI

Real Sentinel-2B Level-2A data for the existing agricultural-landscape crop near
Sidi Bennour, Morocco. This data package contains the source inputs and calibrated
NDVI for two comparable February dates in the internship exercise.

| Role | Acquisition date | Platform / tile / orbit | Full-scene cloud cover | Crop SCL cloud, shadow, cirrus |
| --- | --- | --- | --- | --- |
| Before | 20 February 2024 | Sentinel-2B / 29SNS / R137 | 0.381887% | 0% |
| After | 14 February 2025 | Sentinel-2B / 29SNS / R137 | 0.006186% | 0% |

The dates are 360 days apart and six calendar days apart within February. Among
the February 2024 scenes returned for this footprint, 20 February offered a
same-satellite, same-orbit match with low scene cloud cover. Both crops were also
visually checked for clouds and matching roads, settlements, and field patterns.
SCL is an automated quality classification, not a guarantee of cloud absence.

## Files and footprint

Each dated directory contains:

- `B04_10m.tif`: red band, original unsigned 16-bit digital numbers.
- `B08_10m.tif`: near-infrared band, original unsigned 16-bit digital numbers.
- `SCL_10m.tif`: scene classification labels aligned to the band grid.
- `rgb.png`: an 8-bit true-colour display crop; use for viewing, not NDVI.
- `source.stac.json`: the full selected Earth Search catalog item.
- `product_metadata.xml`: source product metadata used to verify calibration.

All image arrays are 512 × 512 pixels, covering 5.12 × 5.12 km on the existing
10 m grid in **EPSG:32629**. UTM bounds are west 556270, south 3612650, east
561390, north 3617770 metres. The GeoTIFFs preserve this CRS and transform.
The 2025 RGB PNG is byte-for-byte identical to the original Doukkala demo image.

SCL's source resolution is **20 m**. Nearest-neighbour sampling places its labels
on the exact 10 m target grid without creating intermediate class values or
additional spatial detail. The original crop starts halfway through native SCL
cells, so aligned counts need not equal native counts multiplied by four.
SCL labels found here are 4 (vegetation), 5 (not vegetated), and, in 2025, four
10 m output pixels labelled 6 (water). SCL vegetation is not a crop-type label.

`manifest.json` records source URLs, acquisition times, processing baselines,
the grid, calibration, SCL class counts, and SHA-256 hashes for all downloaded
assets and source metadata. The source inputs are about 2.9 MiB; the calculated
NDVI outputs are a separate 1.8 MiB under `ndvi/`.

## Reflectance calibration

The spectral files store **raw digital numbers**, not already converted floating
point reflectance. For valid B04 and B08 pixels on both dates:

```text
reflectance = DN × 0.0001 − 0.1
```

The scale and offset are stored in each GeoTIFF and in the manifest. Both were
checked against the source product XML: quantification value 10000 and
BOA_ADD_OFFSET of −1000 for band IDs 3 (B04) and 7 (B08). Do not apply the offset
twice, and exclude DN 0 as no-data before converting. Rasterio `read()` returns
the stored digital numbers; apply its band `scales` and `offsets` explicitly.

The selected source is Earth Search **`sentinel-2-c1-l2a`**, whose calibration is
described by the [provider](https://github.com/Element84/earth-search/issues/41)
and the [Copernicus product documentation](https://sentiwiki.copernicus.eu/web/s2-products).
The older `sentinel-2-l2a` catalog used for the original RGB demo has
[reported offset inconsistencies](https://github.com/Element84/earth-search/issues/71).
Both analytical dates therefore use Collection 1 and explicit calibration checks.

## NDVI calculation

Run `uv run calculate_doukkala_ndvi.py` from the repository root to calculate
NDVI entirely offline from the saved bands. This uses an isolated Rasterio
environment and refuses to overwrite an existing `ndvi/` directory. Move only
that derived directory aside to recalculate; the source bands stay unchanged.

The script verifies source checksums, grid alignment, types, and calibration tags
before calculating:

```text
red = B04_DN × B04_scale + B04_offset
nir = B08_DN × B08_scale + B08_offset
NDVI = (nir − red) / (nir + red)
```

This is the [Sentinel-2 NDVI definition](https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/ndvi/).
Calibration uses float64 arithmetic; the resulting indices are stored as float32.

The valid-land policy keeps [SCL classes](https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/)
4 (vegetation) and 5 (not vegetated). Keeping both avoids selecting only green
pixels and losing land that became bare. The policy excludes water, cloud and
terrain shadows, clouds, cirrus, snow, unclassified, defective, and missing data.
The calculation also requires valid input band masks, nonzero raw red/NIR values,
nonnegative calibrated reflectance, and a finite positive denominator. Invalid
pixels are masked rather than clipped into the NDVI range. Zero and negative
NDVI values remain valid when these quality conditions hold.

Both output dates use the intersection of their eligible pixels. This gives
**262,140 common valid pixels**, excluding the four pixels labelled water in 2025
from both dates. No other pixels failed the numeric or quality checks.

| Date | Mean NDVI | Median NDVI | Minimum | Maximum |
| --- | --- | --- | --- | --- |
| 20 February 2024 | 0.466847 | 0.403136 | -0.143646 | 0.945346 |
| 14 February 2025 | 0.421007 | 0.292425 | -0.046547 | 0.942147 |

These are dimensionless indices over common valid land in the entire view,
including nonvegetated surfaces, roads, and settlements. They are not averages
for a verified crop or parcel. Two images alone cannot establish crop identity
or the cause of a change. SCL screening remains automated at native 20 m
resolution, and matching pixel grids do not constitute a scientific subpixel
co-registration assessment.

The derived directory contains:

- `2024-02-20_ndvi_10m.tif` and `2025-02-14_ndvi_10m.tif`: calibrated, single-band,
  float32 NDVI on the original 512 × 512, 10 m, EPSG:32629 grid. Valid values are
  in [-1, 1]; excluded pixels have the declared no-data value **-9999**.
- `common_valid_mask.tif`: 1 for the shared eligible land pixels, 0 for excluded pixels.
- `summary.json`: the method, mask policy, statistics, source-manifest hash, grid,
  and output checksums. The source manifest and source files are unchanged.

## Web example and Ask Gemini

Select **Doukkala: NDVI, 2024–2025** beside the existing examples. The interface
shows the two RGB previews, dated mean/median values, and shared mask counts.
These are precomputed measurements, shown independently of the model's answer.

`case.json` pins the acquisition dates, image paths, method reference, summary
path, and the summary's SHA-256. Loading the example reads that saved summary;
it does not call Gemini or rerun the calculation. On **Ask Gemini**, the server
reads and verifies the summary again, then supplies a bounded `ndvi_results`
object with the RGB images, question, editable context, and method reference.
File paths and hashes are not sent to the model or exposed in the public summary.
The browser cannot provide or replace the measurements. If the saved summary
does not match its pinned checksum, the assessment fails without a model request.

The measured case uses its own `doukkala-ndvi-v3` instruction. It asks Gemini to
attribute numbers to the application's saved calculations, keep user reports
separate, and avoid inventing crop types, causes, or changed-area percentages.
Only the method reference is supplied; unrelated soil/fertilizer retrieval is
not needed for this case. The original RGB examples and NASA comparison retain
their existing retrieval and v8 instruction. RGB-only uploads still cannot
provide an NDVI measurement.

The runtime deployment needs `case.json`, `ndvi/summary.json`, and the two
`*/rgb.png` previews. Raw bands, NDVI rasters, source STAC/XML metadata, and
preparation scripts remain outside the deployment upload. Regenerating the NDVI
summary requires reviewing and updating its pinned checksum in `case.json`.

The web request still supplies only the per-date NDVI summary. The new offline
change classification below is not yet displayed or supplied to Gemini. A change
map, legend, imagery/change switch, and visible area figures are the next increment.

## NDVI change and classification

Run `uv run calculate_doukkala_change.py` to subtract the saved 2024 NDVI from
the saved 2025 NDVI at every common valid pixel:

```text
change = NDVI(2025-02-14) - NDVI(2024-02-20)
```

The simple demonstration threshold is **0.05 NDVI units**, not 5% vegetation
change. It was chosen for this prototype, not calibrated against field reference
data. Small differences are grouped as stable to make the comparison interpretable;
this does not establish a statistical significance or measurement-error threshold.

| Output code | NDVI change class | Rule | Pixels | Share of valid pixels | Projected-grid area |
| --- | --- | --- | ---: | ---: | ---: |
| 1 | Decreased | change < −0.05 | 89,525 | 34.15% | 895.25 ha |
| 2 | Stable within tolerance | −0.05 ≤ change ≤ +0.05 | 127,486 | 48.63% | 1,274.86 ha |
| 3 | Increased | change > +0.05 | 45,129 | 17.22% | 451.29 ha |
| 0 | Excluded / no data | Outside the shared valid mask | 4 | Excluded from denominator | 0.04 ha |

The denominator is **262,140 common valid land pixels**, covering 2,621.40 ha.
Each 10 m × 10 m projected-grid pixel represents 100 m² or 0.01 ha. Areas use
the EPSG:32629 grid, not parcel boundaries. The common mask remains unchanged;
all four excluded pixels keep no-data status in both outputs.

`change/` contains:

- `ndvi_change_10m.tif`: float32 differences on the original 512 × 512 grid;
  excluded pixels are −9999. Mean change is −0.045841, median −0.013386,
  minimum −0.876041, maximum +0.776157. The median is calculated from the
  pixelwise differences; it is not the difference between the two date medians.
- `ndvi_change_classes_10m.tif`: uint8 class codes 1–3, with no-data code 0.
- `summary.json`: dates, formula, threshold, class rules, counts, areas,
  difference statistics, input provenance hashes, and output checksums.

Subtraction uses float64 arithmetic on the saved float32 NDVI inputs and stores
float32 differences. Classification compares those saved differences with the
float32 representation of 0.05, including both threshold boundaries as stable.
This makes the categories reproducible when the difference raster is reopened.

The script verifies the input checksums, chronological dates, CRS, pixel grid,
band formats, valid masks, NDVI range, and counts before writing. It stages both
rasters and the summary together, refuses to overwrite an existing `change/`,
and never alters the original source bands or per-date NDVI outputs. To regenerate,
move only the derived `change/` directory aside first. Runtime web dependencies
do not change. Reading, masks and GeoTIFF output follow the Rasterio documentation
on [reading](https://rasterio.readthedocs.io/en/stable/topics/reading.html),
[valid masks](https://rasterio.readthedocs.io/en/stable/topics/masks.html), and
[writing](https://rasterio.readthedocs.io/en/stable/topics/writing.html).

These are **NDVI change classes**, not verified changes in crop type, vegetation
area, yield, or cause. The view includes nonvegetated surfaces, SCL can contain
errors, and residual atmospheric, timing, and registration differences remain.
Stable means the chosen tolerance was not exceeded. No independent cloud detector
or manual correction mask was added in this increment. The threshold's suitability
has not been validated against independent reference observations.

## Reproduce and verify

The pinned sources are the
[2024 item](https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items/S2B_T29SNS_20240220T111943_L2A)
and the
[2025 item](https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items/S2B_T29SNS_20250214T111323_L2A).
No account or API key is needed. From the repository root:

```bash
uv run prepare_doukkala.py
```

The script uses Rasterio 1.4.4 and Pillow 13.0.0 in an isolated environment, reads
small COG windows, and publishes the data directory only when both dates finish.
It refuses to replace an existing package; move this directory aside first if
you intend to prepare it again. The web application's dependencies stay separate.
The implementation follows Rasterio's
[windowed reading](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html)
and [grid alignment](https://rasterio.readthedocs.io/en/stable/topics/virtual-warping.html)
documentation.

Validate the saved data without network access using the application's existing
Python environment:

```bash
python -m unittest discover -s tests -p test_doukkala_data.py -v
```

These checks cover dates, original-footprint alignment, CRS, 16-bit analytical
bands, scale/offset tags, no-data, quality labels, original 2025 RGB identity,
and hashes for all data and source metadata.

Check the saved NDVI artifacts with the existing application environment:

```bash
python -m unittest discover -s tests -p test_doukkala_ndvi.py -v
```

The formula and masking checks use the separate data environment so Rasterio
and NumPy do not become web-app dependencies:

```bash
uv run --no-project --with rasterio==1.4.4 python -m unittest discover -s tests -p check_ndvi.py -v
```

These cover known calibrated results, negative and zero NDVI, clouds and other
excluded SCL labels, missing/nonfinite/negative spectral data, zero denominators,
misaligned arrays, and invalid calibration. Artifact checks verify geographic
alignment, float32 storage, shared masks, source-band sample calculations,
summary statistics, and output hashes. The full `test_*.py` suite also checks
that the new script and derived files stay outside deployment uploads.

Verify the saved change artifacts without Rasterio in the web environment:

```bash
python -m unittest discover -s tests -p test_doukkala_change.py -v
```

The two artifact tests independently check every pixel's subtraction and class,
grid preservation, no-data handling, summary statistics, areas, percentage
denominators, and checksums. The 13 calculation and writer checks use the separate
author environment:

```bash
uv run --no-project --with rasterio==1.4.4 python -m unittest discover -s tests -p check_ndvi_change.py -v
```

These cover threshold boundaries, adjacent float32 values, the full [-2, 2]
change range, negative NDVI, integer subtraction, invalid inputs, excluded pixels,
unchanged inputs, saved areas/classes, checksum/grid failures, mask validation,
and refusal to overwrite an existing output.

Verification on 14 November 2026: **106 main tests and 18 author calculation/writer
checks passed** (13 change checks and five existing NDVI checks). The documented
offline command produced the saved outputs. Hash comparison confirmed that all
18 existing source, case, and NDVI data files stayed unchanged; only this README
was updated. No new Gemini calls, interface changes, or production deployment
were part of this increment.

**Contains modified Copernicus Sentinel data 2024 and 2025.** Modification: spatial
cropping, SCL label alignment, and PNG export of the provider's true-colour product.
Spectral pixel values were not stretched or converted to display RGB. See the
[Sentinel data legal notice](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice).
