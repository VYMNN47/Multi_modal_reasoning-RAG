---
version: alpha
name: GeoScan
description: A field notebook with editable Moroccan satellite-image examples and cited assessments.
colors:
  primary: "#236440"
  background: "#FFFFFF"
  surface: "#F1F5F3"
  text: "#172C35"
typography:
  body:
    fontFamily: "sans-serif"
  heading:
    fontFamily: "serif"
omitted:
  - section: rounded
    reason: CSS control geometry is owned by assets/site.css.
  - section: spacing
    reason: Responsive layout and spacing are owned by assets/site.css.
components:
  upload:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
  form:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text}"
  button:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
---

## Overview

GeoScan is an agronomist's field notebook for the portfolio author and reviewers
exploring Moroccan agriculture. The real crop images are the main visual; the
question, field context, and cited assessment follow them. English controls accept
Unicode text, with English or French model answers. Keep the original decorative
topographic contour pattern, white background, soil green actions, and restrained
serif headings. Avoid marketing heroes, invented crop labels, and ornamental grids.

Runtime ownership: `assets/site.css` supplies the CSS variables matching the
frontmatter colors and the system/Georgia font stacks. `assets/topography.svg`
is original decorative artwork, not a map or measurement of the displayed field.
`assets/index.html` and `assets/site.js` own the single-screen workflow; `app.py`
and `asgi.py` own server validation and assessment requests. No Streamlit controls,
styles, sessions, or configuration are used.

## Colors

Soil green marks the main action and links; dark slate text sits on white. Pale
green-gray separates controls, help, and loading status from images. Border,
muted-text, and error colors are CSS variables. Error text always accompanies its
color. The fixed light theme honors forced colors and native focus behavior.

## Typography

Georgia/Times serif headings give the notebook its character. A system sans-serif
stack keeps labels and text readable, including French accents. No external font
requests are needed. Use one h1, h2 for measurements, the form and response, and h3 for answer
sections. Long filenames and paragraphs wrap rather than overflowing.

## Layout

The page is centered and capped at 72rem. The example selector and answer language
sit above the workspace. One image uses an image/form column pair. Two images use
two equal preview columns above the form, sharing the same layout for custom
uploads and the dated NASA and Doukkala NDVI examples. Below 640px, settings, previews, and the form
stack in reading order. Photos preserve aspect ratio and are never stretched into
a false spatial comparison. Each preview identifies its image/order or its known
acquisition date and satellite. NASA and Copernicus attribution are attached only
to the appropriate curated examples.

The document owns vertical scrolling. Scrollbars stay visible and operable. Form
buttons stay full width while busy; image removal restores the one-image layout.
Reduced-motion settings disable smooth response scrolling and button translation.

## Elevation & Depth

Use flat control surfaces and the form border. Add no shadows or overlays.

## Shapes

Use rectangular images, modest rounded native controls, and the original contour
sheet. No extra ornamental shapes or custom icon-only actions.

## Components

Canonical owners: native HTML select and radios for source/language; a labeled
file input and visible button for selection; a file list with named Remove
buttons; native textareas and a form for text/submission; inline alerts and a
live status region for feedback; native details/summary for provenance. Browser
select popup geometry is accepted. `assets/site.css` owns global focus, pointer,
scrollbar, disabled, and reduced-motion styling. No separate UX contract is needed
for this single screen.

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Select/Listbox | Native HTML select | assets/index.html and assets/site.css | native | Browser selection and open popup |
| Form | Native form and JavaScript submission handler | assets/site.js and asgi.py | example, single image, image pair | tests/test_app.py and real browser |
| Upload | Native file input and browser File list | assets/site.js and app.py | one or two files | Repeated requests, removal, image validation |
| Scrollbar | Global CSS rules | assets/site.css | document | Desktop and narrow-screen checks |
| Toast | Inline alert/status regions | assets/index.html and assets/site.js | loading, error, ready | Browser feedback and API failure tests |
| Measurements | Native semantic table | app.py load_ndvi_results and assets/site.js renderNdviResults | fixed two-date NDVI summary | tests/test_demo.py, SDK checks and browser |

The image-choice button starts disabled until its JavaScript event handler and
initial state are ready. No inline event handler is used; the content security
policy permits only the application script.

Selecting an example fills editable question/context and shows its images without
calling Gemini. Choosing custom upload clears those example inputs. One or two
files may be selected together or added sequentially; a second preserves the
first. Remove affects only its named image. More than two files, invalid formats,
empty files, or more than 4 MiB combined produce correction text without changing
a valid selection. The server additionally verifies signatures, dimensions,
single-frame content, orientation, and the prepared image-size limit.

Image selection and previews stay in the browser. Ask Gemini sends one complete
multipart assessment request. During that request, input controls are disabled,
the form exposes aria-busy, and the live status describes the actual assessment.
A response is final text, not a private reasoning transcript. Failure preserves
files and text for retry. Editing any input clears stale answers. Refresh discards
browser state; there is no persistent image store or visitor authentication.

The Python API validates each request independently, performs semantic retrieval,
and calls Gemini with the ordered images. Undated pairs do not establish a shared
place or chronology; dates/locations entered in context remain unverified reports.
The original NASA case keeps its verified acquisition-date metadata and pinned
case report. The Doukkala NDVI case shows a fixed two-row table of saved means
and medians with date row headers, column headers, tabular numerals, and a shared
valid-pixel count. It uses existing color tokens and document scrolling; it has
no sorting, paging, or new controls. Switching to another example or upload hides
the measurements. Dates use English labels and UTC date-only formatting,
independent of the model's answer language.

Selecting the NDVI example reads its saved summary for display and makes no
Gemini call. Ask Gemini reads it again, verifies its pinned checksum and dates,
and sends bounded measurements with the two RGB previews and the NDVI method
reference. No band download or NDVI recalculation occurs in the web request.
This measured case has a dedicated prompt and does not retrieve unrelated soil
or fertilizer passages. Other examples retain their original retrieval and
agronomy prompt. Explicit NDVI calculation requests for RGB-only inputs still
return an input limitation without retrieval or Gemini generation. The browser
cannot submit its own measurement packet.

The response shows user context verbatim as text, followed by the final assessment
and only the cited source panels. Model output and provenance never enter raw
innerHTML. The limited Markdown renderer creates headings, paragraphs, lists, and
bold text through DOM nodes; only canonical citations matching the returned source
metadata become HTTPS links. The server checks citation membership, not entailment.
No confidence badge or agronomic accuracy certification is implied.

For the measured case, the evidence notice distinguishes saved application
numbers from document citations. The table remains factual application output;
the model explains it and states the limits. Web method references without a
publication date display "not stated" and crop-general methods display
"not crop-specific".

## Do's and Don'ts

- Do put real images before the question and disclose that submissions go to Google.
- Do preserve inputs on failure and make one intentional action produce one request.
- Do keep the Gemini key on the server and raw documents/index files off public routes.
- Don't infer crop identity, soil chemistry, or a cause from an RGB preview alone.
- Don't claim full accessibility certification from native controls or static audits.
