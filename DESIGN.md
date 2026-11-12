---
version: alpha
name: Field notes
description: A field notebook for preparing questions about Moroccan satellite crop imagery.
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
Unicode text, including French. This is a product form for a local desktop demo.
Avoid marketing heroes, decorative maps, invented crop labels, and card grids.

Runtime ownership: `.streamlit/config.toml` is the canonical theme; the exact
values above mirror it. Streamlit adapts these settings into its native widgets.
There are no custom CSS tokens or copied component implementations. Check theme
drift by comparing the four colors and two font roles with that file.

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

One centered, naturally scrolling column. Upload, immediate preview, then the
answer-language radio, then the question and optional context form. The language
control sits outside the form so changing it immediately clears a stale answer.
The image fits the available width and keeps
its aspect ratio. Controls remain reachable on narrow screens. Streamlit owns
responsive widths, document scrollbars, label spacing, and textarea resizing.

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
Show the submitted context verbatim with wrapping `st.text`, labeled unverified,
before the assessment. Do not render instructions in that context as Markdown.
An explicit unsupported NDVI calculation shows an **Input limitation** notice
without a model-success alert or an API call. English and Français are the two
explicit answer-language choices in the native `st.radio` control.
The answer and its sources remain together in session state for the same inputs
and prompt version, and clear when those change or a new submission fails.
Values survive submission and validation errors. No persistent uploads,
navigation, select/date controls, or streamed results exist in step 5.
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
