# Deploy the stateless GeoScan web app on Vercel

## 1. Understand the boundary

The frontend is `assets/index.html`, `assets/site.css`, and `assets/site.js`.
It holds image selections and previews in the browser. `POST /api/analyze` sends
all images and text in one multipart request. `asgi.py` validates and dispatches
that request; `app.py` prepares images, retrieves evidence, and calls the existing
Gemini model code. `api/index.py` exports the ASGI application for Vercel.

**Learn:** Vercel is the host. The application framework does not need to maintain
a browser session when every request carries all required inputs. Consecutive
assessments can run on different workers without sharing uploaded files.

## 2. Run and verify locally

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
python -m uvicorn asgi:app --reload --host 127.0.0.1 --port 8501
```

In another terminal:

```bash
python -m unittest discover -s tests -v
node --check assets/site.js
uv pip check --python .venv/bin/python
```

Use Python 3.14, matching `.python-version`. The dependencies are pinned in the
single `requirements.txt`; no frontend build or additional package manifest is
needed. Document embeddings are already saved: do not run `rag.py embed` during
startup or deployment.

**Learn:** Test the backend contract and the actual browser workflow separately.
A passing SDK transport test cannot prove that the page submits both images.

## 3. Keep credentials on the server

`GEMINI_API_KEY` is already configured as a Vercel server Secret for Preview and
Production in the `geoscan-morocco` project. The new API reads the same variable.
The local `.env` remains useful for local development and is excluded from Git
and deployment uploads. There is no browser-public key or access-code field.

**Learn:** The browser calls your own endpoint. Only the server calls Google;
putting a secret into JavaScript would expose it to every visitor.

## 4. Deploy the existing project

The linked project is `geoscan-morocco`, scope `aymnns-projects`. Its CLI login and
project metadata are under the Git-ignored `.vercel/` directory.

```bash
npx --yes --cache /tmp/geoscan-npm-cache vercel@65.15.0 deploy --prod --yes --logs --scope aymnns-projects --global-config .vercel/cli
```

`vercel.json` routes requests to `api/index.py`, permits a 300-second function,
and includes the runtime Python, frontend assets, v8 prompt, example images,
reviewed passages, and saved index. The static output directory is the empty
`public/` folder; the API explicitly serves the page and allowlisted assets.
This prevents Vercel from publishing Python source or the document index as
static files. `.vercelignore` excludes credentials, tests,
docs, raw PDFs/OCR, GeoTIFFs, and archives. Protected generated deployment URLs
may require Vercel login; test the public production alias with ordinary HTTP or
a browser. Do not create an automation bypass just to check health.

A CLI deployment uploads the working tree. It does not create a Git commit or
push changes. A Git push does not automatically deploy unless a Git integration
has separately been connected.

## 5. Respect the request limits

The API and frontend allow at most two images totaling 4 MiB. The body limit
allows another 64 KiB for bounded multipart fields and overhead, remaining below
Vercel's documented 4.5 MB function payload limit. Each image is limited to
16 million pixels and a single PNG/JPEG frame. The prepared, metadata-free RGB
PNGs must fit the model's 10 MiB combined limit before retrieval starts.

The body cap applies even without Content-Length. Unknown/duplicate fields,
invalid languages/cases, corrupted images, extra files, and mixing example IDs
with uploads are rejected. Only allowlisted example files and the frontend asset
directory are publicly served. The document index and `.env` are not routes.

**Learn:** Limits must be validated in the browser for helpful feedback and again
on the server because a client can bypass the page.

## 6. Check production behavior

- `GET /api/health` returns `{"status":"ok"}`.
- The page, CSS, JavaScript, and all curated images load without console errors.
- Selecting files creates local previews and sends no upload request.
- Add a second image, remove it, and add a different one without refreshing.
- Submit two complete assessments in succession and verify both retain the form.
- Confirm one real Gemini assessment and working citation/source panels.
- Test English/French, empty/invalid input, a second browser tab, and narrow layout.
- Confirm `/.env`, `/.git/config`, and the embedding-index URL return 404.

Changing question, context, language, source, or files clears the previous
assessment. An API error preserves input for retry. Unsupported NDVI calculations
can exercise the complete request/validation path without consuming Google quota.
Do not label those notices as model-generated assessments.

## Verified deployment: 14 November 2026

Production: [geoscan-morocco.vercel.app](https://geoscan-morocco.vercel.app/).
Deployment ID: `dpl_C2PWmtf6eRNqg5X7TYC3XZGM5TiL`.

- All 92 offline tests passed, and the JavaScript syntax check passed.
- The page, health endpoint, example catalog, CSS, JavaScript, and topography
  asset returned 200. Python source, the prompt, the embedding index, `.env`,
  and `.git/config` returned 404 after restricting the static output directory.
- Two consecutive two-image POSTs succeeded in one HTTP session, without
  cookies or a refresh. These used English/French local NDVI notices, not model
  generation, to check the request path without spending provider quota.
- A real browser request sent both uploaded images through retrieval and Gemini.
  The answer described both images, disclosed unknown dates and footprint,
  rendered clickable citations, and exposed the cited excerpt when expanded.
  See [the focused live report](two_image_live_check.json).
- Both previews remained visible after the response. At a 390-pixel viewport
  they stacked with no horizontal overflow. See the [desktop pair](screenshots/custom_pair_desktop.jpg),
  [narrow layout](screenshots/custom_pair_narrow.jpg), and [response](screenshots/geoscan_web_response.jpg).
- The resolved runtime dependency audit reported no known vulnerabilities in
  32 packages. This is a point-in-time dependency check, not a security audit.

These checks do not establish agronomic accuracy. No load test or complete
ten-case live prompt evaluation was performed. Deployment uploaded the current
working tree; it did not stage, commit, or push files.

## Remaining limits and rollback

The demo remains public and uses the server's Gemini quota. Provider failures,
rate limits, and Vercel's 300-second duration still apply. A 120-second SDK timeout
with one retry per provider call can exceed the hosting duration in a slow
assessment. Uploaded files are not durable storage. Citation membership does not
establish claim entailment or agronomic accuracy. Streaming remains future work.

Rollback means promoting an earlier verified stateless Vercel deployment.
The previous Streamlit version has a known consecutive-upload session problem.
No database migration is involved.

## Sources

- [Vercel function limits](https://vercel.com/docs/functions/limitations)
- [Vercel output directory configuration](https://vercel.com/docs/project-configuration/vercel-json#outputdirectory)
- [Starlette requests and multipart limits](https://starlette.dev/requests/)
- [Starlette static-file handling](https://starlette.dev/staticfiles/)
- [Historical Streamlit deployment record](vercel_deployment.md)
