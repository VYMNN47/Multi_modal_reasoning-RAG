# Step 1: Python environment and upload form

This page describes the first completed increment. The current app includes
[step 2](step2.md): its button is now “Ask Gemini” and a valid submit makes an
API request. The environment and validation concepts below still apply.

The goal is to take an image, a question, and optional context from a browser,
check that they are usable, and preview the image. This step ends there.

## 1. Give the project its own Python packages

Python is the interpreter that executes our code. A **virtual environment** is a
directory containing a project-specific interpreter entry point and installed
packages. Here that directory is `.venv/`; it is separate from both our source
files and downloaded data.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

`uv` creates the environment and installs the dependencies. The requirements file
pins Streamlit (the web interface) and Pillow (image reading/validation).
Additional packages installed automatically are dependencies of those packages.
Only the direct dependencies are pinned at this stage.

```bash
source .venv/bin/activate
python --version
python -m streamlit run app.py
```

Activation changes the current shell's `PATH`, so `python` points into `.venv/`.
`python -m streamlit` runs Streamlit using that interpreter. Activation does not
run the app, and each new terminal needs its own activation. `deactivate` exits
the environment; Ctrl+C stops the server. The installed packages stay on disk.

The `.venv/` directory is disposable and Git-ignored. The original satellite and
document files live in `demo_data/` and are independent of it.

## 2. Start with one Python module

`app.py` contains two functions: `load_image` checks image bytes; `main` builds
the screen. A module is simply a Python file that can be imported by other code.

The final `if __name__ == "__main__":` calls `main` when Streamlit executes the
file. When a test imports `load_image`, that condition is false, so importing the
module does not build the interface. There is no need for a framework or extra
service layer to connect two functions.

## 3. Understand the uploaded file

`st.file_uploader` gives Python an in-memory `UploadedFile` object after upload.
`uploaded.getvalue()` returns its **bytes**, the encoded file contents. The
filename and claimed MIME type are labels; they do not prove what the bytes are.

`BytesIO(data)` wraps those bytes with a file-like interface. Pillow can then
read them without our application saving a file. A `with` block closes image
resources even when an error occurs. `load_image` returns a decoded RGB image
that `st.image` renders as a preview.

## 4. Validate at the point where data enters

Our boundary checks are deliberately small:

- Reject empty files and files over 10 MiB before decoding.
- Ask Pillow to recognize only PNG/JPEG contents.
- Reject more than 16 million pixels before decoding the full image, and reject
  animated PNGs. Compressed byte size alone does not bound memory use.
- Check the file structure with `verify()`, then reopen and decode the pixels.
  Either step can catch damage that the other does not.
- Respect JPEG EXIF orientation and convert to RGB for a consistent preview.
- Reject blank/space-only questions and enforce text-length bounds on submit.

`ValueError` means the input is unusable. The UI catches it and uses `st.error`
to show how to correct the input. Unexpected programming errors are not silently
converted into successful checks. No claim is made that these checks prove the
picture is a satellite image, identify a crop, or establish agronomic accuracy.

## 5. Learn Streamlit's execution model

Streamlit normally reruns the script from top to bottom when a widget changes.
We keep the uploader **outside** the form so selecting/removing a file can update
the preview immediately.

The question and context are **inside** `st.form`. Their edits are batched in the
browser and sent together when “Check inputs” is pressed. The submit button
returns `True` for that submission run; an unrelated rerun does not submit again.
That distinction will help us control API calls in step 2.

Stable widget keys (`image`, `question`, `context`) identify the inputs across
reruns. `clear_on_submit=False` preserves their values after a check. This is
session behavior, not saved storage: a new session or refresh can lose the inputs.

The empty placeholders put errors beside the relevant input even though
validation executes after the form has collected its values. We use Streamlit's
native widgets rather than custom HTML or browser scripting.

## 6. Check the behavior, not just the syntax

```bash
python -m unittest discover -s tests -v
```

The tests decode the three downloaded images, accept JPEG, and reject empty,
corrupt, unsupported, oversized, excessive-pixel, and animated inputs. AppTest
drives the real upload widget and form to check previews, validation messages,
retained text, and that an unrelated rerun does not repeat submission success.

Also try it yourself: upload one demo PNG, leave the question empty, click “Check
inputs,” then add a question and submit again. The image and other text should
remain available while you correct the question.

**Teach-back:** Why is the uploader outside the form? Why do we check both file
size and pixel count? Why does a file named `field.png` still need decoding?

## Sources

- [Streamlit installation](https://docs.streamlit.io/get-started/installation)
- [Streamlit forms and reruns](https://docs.streamlit.io/develop/concepts/architecture/forms)
- [File upload API and its validation limits](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader)
- [Pillow image opening and verification](https://pillow.readthedocs.io/en/stable/reference/Image.html)
- [uv virtual environments](https://docs.astral.sh/uv/pip/environments/)

Next: step 2 will load the existing private `.env` and send one deliberate image
request to Gemini. No model client, embeddings, retrieval, or streaming parser
has been added here.
