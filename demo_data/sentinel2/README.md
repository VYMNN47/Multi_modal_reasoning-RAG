# Moroccan Sentinel-2 demo images

Three real agricultural-landscape crops from Sentinel-2B Level-2A imagery,
acquired on **14 February 2025**. All images were downloaded from the public
Sentinel-2 Cloud-Optimized GeoTIFF archive via the Earth Search catalog.

## Files

- `*_rgb_10m.png`: RGB images ready for the demo upload, 512 x 512 pixels.
- `*_rgb_10m.tif`: identical RGB pixels with georeferencing preserved.
- `*_source.stac.json`: the original catalog record for each source scene.
- `manifest.json`: acquisition times, source URLs, coordinates/bounds, CRS,
  processing details, cloud classification checks, and SHA-256 checksums.
- `preview.jpg`: a labeled contact sheet, for browsing only.

Each crop spans **5.12 x 5.12 km** at native **10 m/pixel**, and contains
multiple fields. No parcel boundaries or crop species have been established.

## What was checked

All three crops were visually inspected for agricultural field patterns.
At 20 m resolution the source Scene Classification Layer (SCL) flags no
cloud, cirrus, cloud-shadow, or no-data pixels inside the crop bounds.
This automated classification does not prove that every pixel is cloud-free.
PNG and GeoTIFF pixel arrays were checked for exact equality; the GeoTIFFs
were reopened to verify their CRS, dimensions, and 10 m pixel size.

## Interpretation limits

These are **8-bit true-color display products**, not numerical reflectance
bands. They cannot be used to compute NDVI. Obtain the original red and NIR
bands, with their scale/offset metadata, for quantitative vegetation indices.

The separate [Doukkala change dataset](../doukkala_change/README.md) now supplies
analytical B04/B08 bands for 20 February 2024 and 14 February 2025 on this exact
Doukkala footprint. Its 2025 RGB preview is identical to the existing demo PNG.

The images show real land. Crop identity, irrigation, soil chemistry, nutrient
deficiencies, and treatment needs are **not verified**. Any invented scenario
context added to the demo must be explicitly labeled synthetic. Differences
in greenness are observations, not diagnoses. These are spatial subsets of
Sentinel granules, not complete 110 km source tiles.

## Source and attribution

**Contains modified Copernicus Sentinel data 2025.**
Modification: pixel-aligned spatial cropping of the source TCI visualization,
without resampling or additional color adjustment. The contact sheet also
resizes the images and adds descriptive labels.

- Catalog: https://earth-search.aws.element84.com/v1
- Archive: https://registry.opendata.aws/sentinel-2-l2a-cogs/
- Legal notice: https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice
- Accessed: 2026-11-10.

No application code or project dependencies were changed.
