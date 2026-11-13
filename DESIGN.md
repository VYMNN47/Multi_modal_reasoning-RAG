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
    reason: Streamlit owns native control radii.
  - section: spacing
    reason: Streamlit owns the centered layout and widget spacing.
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

The reference is an agronomist's field notebook: the real crop image is the
main visual, with a compact question beneath it. Audience: the portfolio author
and demo reviewers exploring Moroccan agriculture. English controls accept
Unicode text, including French. This is a product form for a shared portfolio demo.
Avoid marketing heroes, invented crop labels, and card grids. The user's Furrow
reference applies only to the decorative topographic contour pattern, not its
branding, marketing content, or color palette.

Runtime ownership: `.streamlit/config.toml` is the canonical theme; the exact
values above mirror it. Streamlit adapts these settings into its native widgets.
`assets/app.css` owns the capped page width and the contour-background adapter.
`assets/topography.svg` is original decorative artwork, embedded as a data URI
by `app.py`; it is not a map or measurement of the displayed field. Native
controls retain Streamlit's theme and behavior. Check theme drift by comparing
the four colors and two font roles with the configuration file.

## Colors

Soil green marks the main action; dark slate text sits on white. Pale green-gray
separates controls from the image. Streamlit owns semantic alert colors and
focus/hover/disabled states. The default is light; user theme overrides remain
platform behavior. Status text always accompanies color.

## Typography

Serif headings give the notebook its character; native sans-serif controls keep
input readable. Browser fallbacks supply accented characters without external
font downloads. Keep one h1, then a section heading for the question.

## Layout

A centered page capped at 72 rem. A labeled example picker leads to two native
columns: image/attribution and question/context. Streamlit stacks the columns on
narrow screens. The first example is ready to use without an upload; changing
the example replaces the question/context, and choosing upload clears them.
The answer-language radio remains outside the form and clears stale results.
Previews keep their aspect ratio and use an inline JPEG thumbnail of at most
1024 px per side. The model still receives the sanitized full RGB PNG. Streamlit
owns responsive column widths, native scrollbars, labels, focus, and resizing.
The dated Casablanca comparison uses two full-width native image columns above
the form, stacking on narrow screens. Each image has its acquisition date and
satellite/instrument caption; NASA attribution and a source/limitations expander
sit directly underneath. Its regional MODIS imagery is never labeled Sentinel-2.

## Elevation & Depth

Use the native form border and control surfaces; add no shadows or overlays.

## Shapes

Keep Streamlit's native controls and image rectangle. No ornamental shapes.

## Components

Canonical owners: upload and its picker/progress/removal are `st.file_uploader`;
text entry and batching are `st.text_area` inside `st.form`; field-adjacent
feedback is `st.error` in reserved placeholders; confirmation is `st.success`.
No separate UX contract is needed for this single screen.

States: empty invites upload; valid upload previews immediately; invalid content
shows a correction hint; submit validates inputs, retrieves reference excerpts,
then requests one multimodal assessment. Two native `st.spinner` messages describe
those real phases. `st.error` shows safe retrieval, API, or citation failures;
success means a complete response passed the output checks, not that an agronomic
diagnosis was verified. Missing reference evidence and unrelated questions use
native `st.info` notices. Only cited excerpts appear in `st.expander` panels, with
source title, year, crop coverage, physical PDF page, geographic scope, use notes,
and an original-PDF link. The application builds citation links from source
metadata; the model cannot supply arbitrary links.
Web reports instead show a publication date and article link, without a PDF page.
Show the submitted context verbatim with wrapping `st.text`, labeled unverified,
before the assessment. Do not render instructions in that context as Markdown.
An explicit unsupported NDVI calculation shows an **Input limitation** notice
without a model-success alert or an API call. English and Français are the two
explicit answer-language choices in the native `st.radio` control.
The answer and its sources remain together in session state for the same inputs
and prompt version, and clear when those change or a new submission fails.
Values survive submission and validation errors. No persistent uploads,
date controls or streamed results exist. The example picker uses Streamlit's
maintained `st.selectbox` with its native accessible popup; no custom select or
navigation shell is introduced. The author chose a public demo without an
access-code field or visitor authentication. Assessments use the server-side
Gemini key; the key never appears in the browser's input controls.
No custom motion or icon-only product actions are added.

Native Streamlit widgets own keyboard semantics and live alerts. Inspect actual
keyboard access and narrow rendering. Full screen-reader certification and custom
first-invalid-field focus are outside this first local slice; do not claim WCAG
certification from native widgets alone.

## Do's and Don'ts

- Do put the actual image before the question.
- Do name the current action “Ask Gemini” and disclose that submitted inputs go to Google.
- Do distinguish a model assessment from a document-supported recommendation.
- Don't infer crop identity or soil chemistry from an RGB preview.
