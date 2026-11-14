# GeoScan deployment verification

> Historical Streamlit record. The interface was replaced by the stateless web/API version on 14 November 2026. See [the current deployment guide](vercel.md).

Checked on 13 November 2026.

Public URL: **https://geoscan-morocco.vercel.app**

Vercel project: `geoscan-morocco`, scope `aymnns-projects`, Hobby plan.
Streamlit deployment recorded here: `dpl_BRHsiPfqUEpxGmMGM1Y9W423fe1V`.

## What was deployed

The existing Streamlit app, the three Sentinel-2 examples, the NASA dated
comparison, the prepared 16-passage index, and the citation-checked Gemini
integration. The app and project were renamed to **GeoScan**, with the subtitle
“Moroccan crop and land analysis”. The matching domain is attached to the project
and follows production deployments.

`api/index.py` exports the existing ASGI app. Vercel routes requests through
that file, installs the pinned `requirements.txt` with Python 3.14, and bundles
the required assets. The unused tool-only `pyproject.toml` was removed because
Vercel prioritized it and omitted the app dependencies. Explicit raw-data
exclusions replaced negated directory patterns after the native CLI omitted
the examples. The source manifest confirmed all eight required data files and
no private credentials or raw document files.

**Learn:** A ready build does not prove the app starts or its WebSocket-driven
interface works. Check packaging, server health, the real browser, and an actual
assessment separately.

## Credentials and access

With explicit approval, the existing `GEMINI_API_KEY` was stored as a Secret in
Vercel Preview and Production, then applied by redeploying. Its value was never
printed or placed in public app files. The local `.env`, CLI credentials, and
raw PDFs/OCR/GeoTIFFs are excluded from uploads.

The author requested removal of the initial demo-code gate. The field, validation,
environment variable, example configuration, and local code were removed.
Assessments now require no access code or visitor identity. Anyone able to open
the public URL can use the server's Gemini quota. The API key remains server-side.

An automation bypass created by Vercel's CLI health-check command was revoked.
The project was verified to have no automation bypass afterward; Vercel sign-in
protection for protected deployment URLs remains unchanged. Public production
checks used normal browser and HTTP requests.

**Learn:** A server secret configures how the app calls Google; an access gate
controls who can trigger that call. Removing the gate does not put the API key
in the browser. Environment-variable changes require a new deployment.

## Results

- **96 offline tests passed** after the access-code removal, including actual
  SDK request serialization, citation validation, upload checks, paired-image
  dates/order, and the production ASGI entry point's HTTP/WebSocket smoke test.
- Public `/` and `/_stcore/health` return HTTP 200. Health reports `ok`.
  `/.env` returns the application HTML, without the local credential file.
- The hosted Gharb example and a 425 KB public sample upload preview correctly.
- Both original NASA comparison images and their dates render on the hosted app.
- A real hosted comparison completed live semantic retrieval and two-image
  generation, with NASA article and agricultural PDF citations.
- On the final deployment, a fresh browser session submitted the Gharb example
  **without an access code** and received a complete response citing
  `MA_PNTTA_NPK_155`, `MA_INRA_CEREALS`, and `MA_PNTTA_WHEAT_N_62`.
- Final cloud settings confirm the Gemini secret in both environments, no
  `DEMO_ACCESS_CODE`, and no automation bypass. Private local files retain
  restricted permissions.

Screenshots: [public interface](screenshots/geoscan_vercel_public.jpg),
[hosted comparison](screenshots/geoscan_vercel_comparison.jpg),
[comparison response](screenshots/geoscan_vercel_response.jpg).

## Remaining limits and rollback

No load test, full production mobile/accessibility pass, or deliberate
long-duration reconnect/multi-instance upload stress test was performed.
Streamlit state remains in memory; Vercel connections can end at the configured
300-second function limit. The retry policy can make slow assessments exceed
that limit. Provider availability and rate limits still apply.

These are integration checks, not agronomic validation or a complete v7 prompt
quality evaluation. Citation membership is checked; individual claims still
need review against the displayed sources. See the known limits in
[the comparison walkthrough](comparison.md).

To stop public traffic, pause the project in Vercel. To disable live calls for
new sessions, remove the Gemini secret and redeploy. For rollback, select a
known working deployment in Vercel; the previous GeoScan deployment
`dpl_GR97gvwCUFfZ9GNhiRb94B6UTU6L` passed a hosted comparison but still requires
the former demo code. No database migration or uploaded-file cleanup is needed.
