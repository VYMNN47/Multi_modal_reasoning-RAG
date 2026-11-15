# Doukkala NDVI production verification

Deployed and checked on **15 November 2026**.

Production: [geoscan-morocco.vercel.app](https://geoscan-morocco.vercel.app/).
Deployment: `dpl_12zk4DbtvgPoPdcdh5FiBByknDwY`.
Created: 2026-11-15 13:11:44 UTC. Vercel reports Ready, Python 3.14, and a
33.48 MB function in iad1. The deployment uploaded the current working tree;
it did not stage, commit, or push Git changes.

## Verified release

- All **118 offline tests** passed before publishing; JavaScript syntax,
  whitespace and dependency compatibility checks passed.
- The point-in-time audit of **52 resolved local Python packages** found no
  known vulnerabilities and skipped no packages. See
  [the dependency report](ndvi_vercel_dependencies.json).
- Vercel built successfully, uploaded 56 files, and assigned the production alias.
  The alias was inspected again and points at this deployment.
- **17 public HTTP GET checks** passed. The page, CSS, JavaScript, class PNG,
  display metadata and both Doukkala previews match the local bytes exactly.
  The public catalog includes the actual dates, saved NDVI and three class totals.
  The health endpoint returns `{"status":"ok"}`. Secret/source/index/raw-data
  paths return 404. See [the HTTP report](ndvi_vercel_check.json).
- The real browser displays both dated satellite previews, the change map,
  readable legend, class counts/hectares/percentages and excluded-pixel note.
- Two consecutive **Ask Gemini** requests completed without reloading, first
  French, then English. Both returned the correct three hectares/percentages and
  the 262,140-pixel denominator. The English response also correctly states
  2,621.40 ha valid area, 0.04 ha excluded area and stable-within-tolerance limits.
  Loading disabled controls; completion restored them. These were real hosted
  model responses using the existing server credential, not local input notices.
- The reference disclosure opens its actual method excerpt. Native arrow-key
  view changes preserve the answer. At a 360 × 800 test viewport, the map and
  legend are 313 px wide and document width equals viewport width (345 px after
  the scrollbar). At 1280 × 1000 the map and legend appear side by side.
  Temporary viewport sizing was reset. No console errors or warnings were seen.

Browser evidence: [recorded answers and checks](ndvi_vercel_browser.json),
[deployed map](screenshots/doukkala_ndvi_vercel_map.jpg),
[deployed English response](screenshots/doukkala_ndvi_vercel_response.jpg).

## Rollback

The prior verified production deployment remains available:
`dpl_C2PWmtf6eRNqg5X7TYC3XZGM5TiL`,
`https://geoscan-morocco-6b7rqwk10-aymnns-projects.vercel.app`.
If a release-breaking problem appears, use the existing CLI login from the
project directory to restore it, then recheck public health and the original cases:

```bash
npx --yes --cache /tmp/geoscan-npm-cache vercel@65.15.0 rollback https://geoscan-morocco-6b7rqwk10-aymnns-projects.vercel.app --scope aymnns-projects --global-config .vercel/cli
```

No database migration or uploaded-file persistence needs reversal. The generated
deployment URL retains its existing Vercel authentication protection; verification
used the public production alias without changing protection settings.
See the official [deploy](https://vercel.com/docs/cli/deploy) and
[rollback](https://vercel.com/docs/cli/rollback) references.

## Limits

The checks establish hosted functionality, not agronomic accuracy or citation
entailment. The full ten-case prompt suite was previously checked locally; the
hosted check used two real assessments. No load test, field validation or long-term
availability monitoring was performed. Gemini quota, transient provider errors,
and hosting time limits still apply. Source files remain uncommitted locally.
