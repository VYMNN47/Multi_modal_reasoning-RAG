"use strict";

const byId = id => document.getElementById(id);
const state = { examples: [], files: [], urls: [], limit: 4 * 1024 * 1024 };
const controls = byId("controls");
const source = byId("image-source");
const question = byId("question");
const context = byId("context");
const picker = byId("image-files");

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function message(id, text = "") {
  byId(id).textContent = text;
  byId(id).hidden = !text;
}

function clearAnswer() {
  byId("answer").hidden = true;
  byId("answer-text").replaceChildren();
  byId("references").replaceChildren();
  message("request-status");
  message("request-error");
}

function safeLink(label, url) {
  const link = element("a", label);
  if (typeof url === "string" && url.startsWith("https://")) {
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  }
  return link;
}

function renderNdviResults(results) {
  byId("ndvi-results").hidden = !results;
  const rows = byId("ndvi-rows");
  rows.replaceChildren();
  if (!results) return;
  for (const scene of results.scenes) {
    const row = element("tr");
    const date = new Date(scene.date + "T00:00:00Z").toLocaleDateString("en-GB", {
      day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
    });
    const dateCell = element("th", date);
    dateCell.scope = "row";
    row.append(dateCell, element("td", scene.mean.toFixed(4)), element("td", scene.median.toFixed(4)));
    rows.append(row);
  }
  byId("ndvi-coverage").textContent = `Same ${results.common_valid_pixels.toLocaleString("en-US")} valid land pixels on both dates; ${results.excluded_pixels.toLocaleString("en-US")} pixels excluded by the shared quality mask.`;
}

function renderPreviews() {
  for (const url of state.urls) URL.revokeObjectURL(url);
  state.urls = [];
  const custom = source.value === "upload";
  const example = state.examples.find(item => item.id === source.value);
  const images = custom ? state.files.map((file, index) => {
    const url = URL.createObjectURL(file);
    state.urls.push(url);
    return { url, caption: `Image ${index + 1} · ${file.name}` };
  }) : example?.images || [];
  const previews = byId("previews");
  previews.replaceChildren();
  byId("workspace").classList.toggle("pair", images.length === 2);
  if (!images.length) previews.append(element("p", "Choose one or two images to preview the field.", "empty"));
  for (const image of images) {
    const figure = element("figure");
    const photo = element("img");
    photo.alt = image.caption;
    photo.src = image.url;
    photo.addEventListener("error", () => {
      if (photo.isConnected) message(custom ? "upload-error" : "request-error", "This image could not be previewed. Export a complete PNG or JPEG and try again.");
    });
    figure.append(photo, element("figcaption", image.caption));
    previews.append(figure);
  }
  byId("upload-area").hidden = !custom;
  byId("attribution").hidden = !example;
  byId("attribution").textContent = example?.attribution || "";
  byId("example-note").hidden = !example;
  byId("example-description").textContent = example?.description || "";
  byId("example-source").hidden = !example?.source_url;
  if (example?.source_url?.startsWith("https://")) byId("example-source").href = example.source_url;
  renderNdviResults(example?.ndvi_results);
}

function renderFiles() {
  const list = byId("file-list");
  list.replaceChildren();
  state.files.forEach((file, index) => {
    const row = element("li");
    const remove = element("button", "Remove", "remove");
    remove.type = "button";
    remove.setAttribute("aria-label", `Remove image ${index + 1}: ${file.name}`);
    remove.addEventListener("click", () => {
      state.files.splice(index, 1);
      clearAnswer();
      message("upload-error");
      renderFiles();
      renderPreviews();
      byId("choose-files").focus();
    });
    row.append(element("span", `${file.name} · ${(file.size / 1024).toFixed(1)} KB`), remove);
    list.append(row);
  });
  byId("choose-files").textContent = state.files.length ? "Add an image" : "Choose images";
  byId("choose-files").disabled = state.files.length === 2;
}

document.querySelector('[data-action="choose-files"]').addEventListener("click", () => picker.click());
picker.addEventListener("change", () => {
  const next = [...state.files, ...Array.from(picker.files || [])];
  picker.value = "";
  if (next.length > 2) return message("upload-error", "Choose up to two images. Remove an image before adding another.");
  if (next.some(file => !/\.(png|jpe?g)$/i.test(file.name) || !["image/png", "image/jpeg"].includes(file.type) || file.size === 0)) {
    return message("upload-error", "Choose complete PNG or JPEG files.");
  }
  if (next.reduce((total, file) => total + file.size, 0) > state.limit) return message("upload-error", "Choose images totaling 4 MB or less.");
  state.files = next;
  message("upload-error");
  clearAnswer();
  renderFiles();
  renderPreviews();
});

function selectSource() {
  const example = state.examples.find(item => item.id === source.value);
  state.files = [];
  question.value = example?.question || "";
  context.value = example?.context || "";
  clearAnswer();
  for (const id of ["upload-error", "question-error", "context-error"]) message(id);
  question.removeAttribute("aria-invalid");
  context.removeAttribute("aria-invalid");
  renderFiles();
  renderPreviews();
}
source.addEventListener("change", selectSource);
for (const input of [question, context, ...document.querySelectorAll('input[name="language"]')]) {
  input.addEventListener("input", clearAnswer);
}

function appendInline(parent, text, sources) {
  const pattern = /\*\*[^*]+\*\*|\[([^\]]+)\]\((https:\/\/[^\s)]+)\)/g;
  let position = 0;
  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(position, match.index)));
    if (match[0].startsWith("**")) parent.append(element("strong", match[0].slice(2, -2)));
    else if (sources.some(source => source.url === match[2] && source.citation === `[${match[1]}]`)) parent.append(safeLink(match[1], match[2]));
    else parent.append(document.createTextNode(match[0]));
    position = match.index + match[0].length;
  }
  parent.append(document.createTextNode(text.slice(position)));
}

function renderAnswer(data) {
  byId("answer-text").lang = document.querySelector('input[name="language"]:checked').value === "Français" ? "fr" : "en";
  byId("answer-title").textContent = data.kind === "input_limit" ? "Input limitation" : "Gemini response";
  byId("evidence-notice").textContent = data.evidence_status === "used"
    ? "Reported field context is unverified. References are background guidance; check their date, crops, and geographic scope."
    : data.evidence_status === "out_of_scope"
      ? "This demo handles agricultural imagery, soils, crop nutrition, water, and field checks."
      : "No reference excerpt was cited. Review the assessment’s stated evidence limits.";
  if (data.ndvi_results && data.evidence_status !== "out_of_scope") {
    renderNdviResults(data.ndvi_results);
    byId("evidence-notice").textContent = "The saved NDVI measurements are shown above. Cited references support background or method claims; your editable field context remains unverified.";
  }
  byId("reported-context").textContent = data.field_context || "No field context supplied.";
  const content = byId("answer-text");
  let list;
  for (const line of data.text.split("\n")) {
    if (!line.trim()) { list = null; continue; }
    const heading = line.match(/^#{1,3}\s+(.+)$/);
    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!list) { list = element("ul"); content.append(list); }
      const item = element("li");
      appendInline(item, bullet[1], data.sources);
      list.append(item);
    } else {
      list = null;
      const block = element(heading ? "h3" : "p");
      appendInline(block, heading ? heading[1] : line, data.sources);
      content.append(block);
    }
  }
  const references = byId("references");
  for (const source of data.sources) {
    const detail = element("details");
    const published = source.source_format === "web" ? `Published: ${source.publication_date || source.publication_year || "not stated"}` : `Publication year: ${source.publication_year ?? "unverified"} · Physical PDF page: ${source.pdf_page}`;
    detail.append(element("summary", `${source.citation} · ${source.section}`), element("p", source.title), element("p", published, "caption"),
      element("p", `Crops covered: ${(source.crops || []).join(", ") || "not crop-specific"}`, "caption"), element("p", source.geographic_scope), element("p", source.use_note),
      safeLink(source.source_format === "web" ? "Open source" : "Open original PDF", source.url), element("blockquote", source.text));
    references.append(detail);
  }
  byId("references-section").hidden = data.sources.length === 0;
  byId("answer").hidden = false;
  byId("answer").focus({ preventScroll: true });
  byId("answer").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

byId("assessment-form").addEventListener("submit", async event => {
  event.preventDefault();
  clearAnswer();
  for (const id of ["upload-error", "question-error", "context-error"]) message(id);
  question.removeAttribute("aria-invalid");
  context.removeAttribute("aria-invalid");
  if (!question.value.trim() || question.value.length > 2000) {
    message("question-error", "Enter a question using 1–2,000 characters, not just spaces.");
    question.setAttribute("aria-invalid", "true");
    question.focus();
    return;
  }
  if (context.value.length > 4000) {
    message("context-error", "Shorten the field context to 4,000 characters or fewer.");
    context.setAttribute("aria-invalid", "true");
    context.focus();
    return;
  }
  if (source.value === "upload" && !state.files.length) {
    message("upload-error", "Choose one or two PNG/JPEG images.");
    byId("choose-files").focus();
    return;
  }
  const payload = new FormData();
  payload.append("question", question.value);
  payload.append("context", context.value);
  payload.append("language", document.querySelector('input[name="language"]:checked').value);
  payload.append("case", source.value);
  for (const file of state.files) payload.append("images", file, file.name);
  controls.disabled = true;
  byId("assessment-form").setAttribute("aria-busy", "true");
  byId("ask").textContent = "Reviewing…";
  const measured = state.examples.find(example => example.id === source.value)?.ndvi_results;
  message("request-status", measured ? "Explaining saved NDVI measurements and reviewing your images…" : "Reviewing your images and agricultural references…");
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: payload, cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error((typeof data.error === "string" && data.error) || `The server could not complete the assessment (HTTP ${response.status}). Try again.`);
    if (typeof data.text !== "string" || !Array.isArray(data.sources)) throw new Error("The server returned an incomplete assessment. Try again.");
    renderAnswer(data);
    message("request-status", data.kind === "input_limit" ? "Input limitation ready." : "Assessment ready.");
  } catch (error) {
    message("request-status");
    message("request-error", error instanceof TypeError ? "Could not connect to the server. Try again." : error.message || "The assessment could not be completed. Try again.");
    byId("request-error").focus();
  } finally {
    controls.disabled = false;
    byId("assessment-form").removeAttribute("aria-busy");
    byId("ask").textContent = "Ask Gemini";
  }
});

async function loadExamples() {
  renderPreviews();
  try {
    const response = await fetch("/api/examples");
    if (!response.ok) throw new Error();
    const data = await response.json();
    state.examples = data.examples;
    state.limit = data.max_upload_bytes;
    for (const example of state.examples) source.add(new Option(example.label, example.id));
    source.value = state.examples[0]?.id || "upload";
    selectSource();
  } catch {
    message("request-error", "The examples could not be loaded. You can still upload your own images.");
  } finally {
    controls.disabled = false;
    renderFiles();
    message("request-status");
  }
}
loadExamples();
