# Step 2: Connect the form to Gemini

The app can now take validated image/text inputs, ask Gemini, and display the
answer. The model runs on Google's servers. Our Python program builds the
request, authenticates it, and checks the returned response.

## 1. Keep the key on the server

`model.py` defines `get_api_key()`. It loads the project's `.env` with
python-dotenv, then reads `GEMINI_API_KEY` from the Python process environment.
An already-set environment variable wins over the file. Restart after changing
a key that has already been loaded.

The `.env` file is not loaded into Streamlit session state or rendered in the
browser. It is not part of the question or system prompt. The SDK sends the key
as authentication to the Gemini Developer API over HTTPS. The model name selects
which model to call; changing between these Gemini models does not itself require
a new API key.

**Learn:** Configuration and credentials are separate from source code. Environment
variables belong to the server process; `st.session_state` belongs to one user
session. A key is an access credential, not the model itself.

## 2. Use the official SDK

`google-genai` is Google's Python SDK. It handles HTTP requests, authentication
headers, encoding, and response objects so we do not have to construct those
details manually. `httpx2` is its installed HTTP transport and supplies the timeout
and connection-error classes we catch. All direct package versions are pinned.

`answer_image(image_png, question, context)` creates a client for the Developer
API, explicitly uses the selected key, and calls `client.models.generate_content`
with `gemini-3.5-flash-lite`. A `with` block closes its network connections afterward.
There is no model training, weight download, or local GPU requirement.

We set a 60-second HTTP timeout and one attempt. The SDK does not automatically
repeat quota or service failures; the user can choose to retry. That keeps the
demo's request behavior visible and bounded.

**Learn:** An SDK is a library that helps us call an API. Calling a vision model
once is not yet an agent with retrieval tools or a planning loop.

## 3. Send the image and text in the same request

After validation, `app.py` prepares an RGB PNG in memory. JPEG orientation is
applied and embedded metadata is removed, so Gemini receives the same oriented
pixels used for the preview. The prepared image also has a 10 MiB size check.

The user message contains two parts:

1. `Part.from_bytes`: the PNG bytes and their MIME type (`image/png`). The SDK
   encodes those bytes for the network request.
2. A text part containing the question and optional field context as JSON. Empty
   surrounding whitespace is removed; French and other Unicode text are retained.

The selected image is sent directly to the vision model. We have not converted it
into a semantic embedding. The image hash used for session matching is just an
identifier for exact prepared bytes; it cannot search for similar images.

**Learn:** A multimodal request combines image and text inputs. JSON keeps the
question and context clearly named; it does not make user reports true.

## 4. Give the model a clear role and evidence limits

`SYSTEM_PROMPT` tells Gemini to distinguish visible observations, user-reported
context, and uncertain hypotheses. It asks for relative image locations and
conditional next checks. It also states that reference documents and tools are
not available in this step, and asks for no invented measurements, document
searches, nutrient diagnoses, or fertilizer prescriptions.

System instructions describe the assistant's behavior; the question and field
context are the input for this particular request. Synthetic crop details remain
demo context. A prompt guides behavior but does not establish agronomic accuracy.

**Learn:** The model has learned general knowledge, but it has not searched our
downloaded documents. Adding relevant document passages later is what makes the
response retrieval-augmented.

## 5. Validate the response and make failures useful

The interface displays a spinner while waiting. The service accepts a non-empty
public text answer only when the model reports a normal `STOP`. Blocked, empty,
and truncated responses are shown as failures instead of complete answers.

`GeminiError` carries a safe message for the UI. Missing credentials, rejected
requests, unavailable models, quota limits, temporary service failures, timeouts,
and connection problems receive correction hints. Raw provider exception details
are not shown, because they can contain request information. Form values stay
available for correction and retry.

**Learn:** An API can fail even when the Python code is correct. A successful
network request and an accurate agronomic answer are different things.

## 6. Retain the answer without accidentally resending

The API call lives inside the successful form-submit branch. Merely previewing
an image or rerunning the script does not call Gemini.

`st.session_state` stores the answer with the submitted question, context, and an
image hash. Ordinary reruns can redraw that answer. When the inputs change, or a
new submit fails, the previous answer is cleared. A deliberate valid submit asks
Gemini again, even if the inputs are identical. This is a small session record,
not a persistent database or an API-response cache.

**Learn:** Streamlit reruns execute code again. State lets us retain results;
placing the network call behind submit controls when new work happens.

## 7. Read the tests

`tests/test_model.py` runs the real SDK against a simulated HTTP transport. It
checks the serialized image bytes, question/context, system prompt, key header,
and safe behavior for failures. `tests/test_app.py` replaces only the model call
when checking form behavior. The ordinary suite uses no real key or API quota.

A separate live browser submission used the actual Doukkala PNG and existing
key. See [verification](step2_verification.md) for the observed result.

**Teach-back:** Which data goes to Google? Where does the API key go? Why can a
normal Streamlit rerun show the existing answer without making a new request?
Why is this step still not RAG?

## Sources

- [Official Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
- [Gemini content-generation API](https://aistudio.google.com/api-reference/generate-content)
- [Selected model](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite)
- [python-dotenv loading and precedence](https://pypi.org/project/python-dotenv/)
- [Streamlit session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)

Next: step 3 prepares reviewed agricultural passages. Embeddings, retrieval,
citations, and streaming remain separate later steps.
