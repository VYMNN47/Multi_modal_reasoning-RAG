# Deploy the portfolio demo on Vercel

The **GeoScan interface is live** at [geoscan-morocco.vercel.app](https://geoscan-morocco.vercel.app),
in project `geoscan-morocco`, under scope `aymnns-projects`. Public HTTP/health,
interactive controls, image previews, sample upload, and the dated comparison
have been checked, and the GeoScan name is visible. A real hosted comparison
completed retrieval and two-image generation with source citations. After the
user's explicit approval, `GEMINI_API_KEY` was configured as a server-side secret
for Preview and Production. Its name and scopes were verified without displaying
the value. The author subsequently requested removal of the demo access code;
the public demo permits assessments without identifying visitors. Longer-running
reliability checks remain pending. No automation bypass is configured.
The original ten-step learning plan is still available; streaming remains step 6.

## 1. Let visitors try a real example

The first page now loads a Gharb image, suggested wheat/nitrogen question, and
synthetic field context. The picker also offers Tadla/phosphorus and
Doukkala/irrigation scenarios. These reuse the three downloaded Sentinel-2 PNGs.
The crop, irrigation, and soil statements are scenarios, not verified image labels.
The fourth choice, **Casablanca: Drought, 2023–2024**, displays a sourced NASA
MODIS pair 372 days apart. Both JPEGs and their case metadata are explicitly
included in the deployment. See [comparison walkthrough](comparison.md).

`EXAMPLES` in `app.py` holds the image filename, question, and context for each
choice. `select_example()` changes those values before the text widgets render
and clears the old assessment. Choosing **Upload my own image** clears the example
text. Questions/context remain editable. Changing the picker intentionally
replaces the current draft; language changes and ordinary form reruns do not
regenerate the example. Streamlit batches text edits until form submission.

Selecting or previewing a field uses no Gemini quota. **Ask Gemini** starts the
existing retrieval/generation path. Citation validation and the 3,072-dimensional
index are unchanged. The final assessment stays in the current session.

**Learn:** A UI callback updates state; it does not have to call an AI model.
Useful defaults let a reviewer explore the product before preparing their own data.

## 2. Add the contour pattern

`assets/topography.svg` is original decorative artwork inspired by the Furrow
reference's contours. It does not depict the uploaded field. `assets/app.css`
adds it as a faint repeating background, caps the page width, and keeps the
existing palette, fonts, and native Streamlit controls. No tracking, remote
fonts, image service, animation, or copied brand content was added.

The image and form sit beside each other on desktop and stack on narrow screens.
Preview thumbnails are embedded as data URLs, with a maximum side of 1024 px.
This avoids a later image request relying on the same function instance. The
vision API still receives the full, validated, metadata-stripped RGB PNG.

**Learn:** Visual assets and layout can change independently of the retrieval
and model code. A display thumbnail is not the same payload as the model input.

## 3. Expose the existing app through ASGI

`asgi.py` creates `st.App` pointing at the existing `app.py`. This is the
callable Python application; it does not spawn a second web server. Vercel did
not automatically detect Streamlit, so `api/index.py` reexports this same
`asgi.app`. `vercel.json` names `api/index.py` as the function and rewrites
`/(.*)` to `/api/index`, sending page, asset, upload, and Streamlit endpoint
requests through that entry point. The local module path is `api.index:app`.
The tool-only `pyproject.toml` was removed after the first public runtime check
found that Vercel had prioritized it and omitted the app's dependencies.
`requirements.txt` is the dependency source and `.python-version` requests
Python 3.14. No new Python dependency was added.

`vercel.json` sets a 300-second function duration and explicitly includes the
runtime Python, prompt, CSS/SVG, example PNGs/JPEGs, comparison metadata,
prepared passages, index, and Streamlit configuration. The first deployment
attempt exposed a schema limit: the `includeFiles` pattern must be at most 256
characters. Short directory patterns now keep it within that limit, while
`.vercelignore` explicitly excludes raw data. Negated child patterns were removed
after Vercel's native CLI pruned the parent directory and omitted the examples.
The uploaded source manifest was then checked for all eight required data files.
It excludes local credentials, tooling, tests/docs, raw source PDFs/OCR,
GeoTIFFs, and archives from deployment uploads.
`.vercel/` project-link metadata is Git-ignored. The saved index is read-only at
runtime: do not run passage preparation or document embedding during deployment.

Run the same ASGI entry point locally:

```bash
source .venv/bin/activate
python -m uvicorn api.index:app --host 127.0.0.1 --port 8501
```

The original `python -m streamlit run app.py` command also remains available.

**Learn:** Your Python UI script describes the app; ASGI defines how a hosting
runtime sends HTTP/WebSocket events to it. Vercel owns the network listener.
See [Vercel's Python entry points](https://vercel.com/docs/functions/runtimes/python)
and [Streamlit's App interface](https://docs.streamlit.io/1.65.0/develop/api-reference/server/st.app).

## 4. Configure the Vercel project

The deployment uses the Vercel CLI to upload the local working tree; a Git
push is not required for that route. Vercel CLI 65.15.0 was run through `npx`,
with its npm cache in `/tmp/field-notes-npm-cache` and its account configuration
in the Git-ignored `.vercel/cli` directory. The project link also stays under
`.vercel/`. Credentials in that directory must not enter deployment uploads.

The project is `geoscan-morocco` in scope `aymnns-projects`. It was renamed
from `field-notes-morocco` while retaining the same project ID. For a repeat
preview deployment from this directory:

```bash
npx --yes --cache /tmp/field-notes-npm-cache vercel@65.15.0 deploy --global-config .vercel/cli --scope aymnns-projects
```

Add `--prod` to deploy to the production environment and update the public
`geoscan-morocco.vercel.app` alias. A preview deployment uses Preview variables;
a production deployment uses Production variables.

The CLI reads the project link and `.vercelignore`, uploads the allowed files,
installs the Python requirements, and builds the function. A ready deployment
means that build finished; it does not prove the app's interactive flow works.

For later Git-based deployments, import the repository with this directory as
its project root. Use the **Other** framework preset and retain the Python
dependency-installation defaults. Do not configure an npm build, static output
directory, or `streamlit run` build command.

Server-side configuration:

1. The approved `GEMINI_API_KEY` secret is configured for both Preview and
   Production. Configure this same name when reproducing deployment in a
   different project; keep its value out of source and logs.
2. Keep Fluid compute enabled for WebSocket support. Vercel sets `VERCEL=1`;
   the app uses that flag for its hosted upload boundary.
3. Create a new deployment and review its build/runtime logs before sharing.
   Adding/changing environment variables requires a new deployment.

Do not upload `.env`, commit the secret, or use a browser-public environment
variable prefix. Local `.env` loading still supplies the Gemini key for local
development.

The demo has no access-code field or visitor authentication, as requested by
the author. Anyone who can open the public URL can run an assessment against
the server's Gemini quota. This choice does not expose the API key to the
browser. There is no per-visitor rate limiter.

Vercel's function request-body limit is 4.5 MB. The hosted app accepts files up
to **4 MiB** (displayed as 4 MB), leaving room for multipart overhead; local
development retains 10 MiB. File signatures, single-frame checks, the 16-million-
pixel limit, and model-input checks still apply. Built-in PNGs are well below
the upload limit. [Vercel function limits](https://vercel.com/docs/functions/limitations).

**Learn:** Environment variables keep credentials on the server. Cloud limits
must agree with what the upload form promises, rather than failing after upload.

## 5. Verify the hosted app before sharing

The production URL is public. Protected previews require normal Vercel sign-in;
a Vercel authentication page or HTTP 401 is not an application health result.
Use the browser's normal authenticated session for a protected preview, or
plain HTTP requests against the public production URL. No automation bypass
is configured or required.

The public root and `/_stcore/health` both returned HTTP 200. A request to
`/.env` returned the app's HTML, without credentials or the private file.
The Gharb controls, a 425 KB sample upload, and both comparison originals were
checked on the hosted app. A real comparison assessment completed retrieval and
generation and displayed NASA and PDF citations.
See [deployment verification](vercel_deployment.md) for its final outcome.

Check the following on the actual deployment URL:

- `/_stcore/health` returns HTTP 200, and the page loads its controls and pattern.
- Each of the four examples changes the image/question/context, without an API
  call until submission. A valid submission generates a cited answer without
  an access code. Inspect the cited excerpt against the generated claim.
- The Casablanca choice shows both dates and sends both images. Its cited NASA
  report opens as an article, without a fabricated PDF page.
- Upload a small PNG/JPEG, edit the text, and confirm an answer uses those inputs.
- Open two independent browser sessions and verify that uploads, edits, and
  assessments stay separate. Try refresh/reconnect, not only a fresh load.
- Try empty/invalid input, an unrelated question, and an unsupported NDVI request.
- Inspect narrow-screen layout and the open example picker with keyboard input.
- Leave a session open past five minutes, then verify reconnection and another
  submission. Confirm expected state loss is clear and does not mix requests.

WebSockets close when a function reaches its maximum duration, and reconnects
can reach another instance. Streamlit keeps session/upload state in memory. Also,
the [current Gemini retry policy](gemini_reliability.md) can also make a slow
assessment run longer than Vercel's 300-second limit. Increasing an SDK timeout
does not increase that hosting limit or guarantee a complete hosted request.
Uploaded-file HTTP requests can also encounter multi-instance routing issues.
Inline previews reduce media dependence, but do not provide distributed upload
storage or session persistence. These are **hosted acceptance checks**, not
claims established by the local run. If routing or session behavior fails,
pause sharing and use a stateful Streamlit host or redesign storage/session
handling before relying on Vercel for this app. Sources:
[Vercel WebSocket lifecycle](https://vercel.com/docs/functions/websockets),
[Streamlit deployment architecture](https://docs.streamlit.io/develop/concepts/architecture/architecture).

For rollback, use Vercel's previous deployment. If the first preview is faulty,
remove it or leave it unshared while fixing it. Removing `GEMINI_API_KEY`
and redeploying disables live analysis in new sessions. No database migration or user-data
cleanup is involved.

Run the automated checks from the project root:

```bash
python -m unittest discover -s tests -v
uv pip check --python .venv/bin/python
```

The suite uses simulated Gemini transports and no real key. ASGI integration
uses a child process and an in-memory HTTP/WebSocket test client; network-
restricted agent sandboxes may require running that test outside the sandbox.
See [preparation verification](vercel_verification.md) for the actual results.
