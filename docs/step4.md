# Step 4: Embed and search agricultural passages

We now have semantic search over **16 reviewed passages from eight sources**.
It runs independently from Streamlit and the vision model. This lets you inspect
the evidence before we give it to the model in step 5.

## 1. What an embedding does

An embedding is a list of numbers representing a text's meaning. Similar texts
can have similar vector directions even when they use different words or
languages. Our model returns **3,072 numbers for each text**. These dimensions
are learned features, not named measurements such as nitrogen, pH, or moisture.

We use the selected `gemini-embedding-001` with the existing key and SDK.
Google documents a 2,048-token input limit and supports 3,072 dimensions for
this model. We explicitly request that dimension count for documents and queries.
[Model reference](https://aistudio.google.com/docs/models/gemini-embedding-001).

The model is already trained. We are calling its embedding API, not training
a new model. The embedding model finds text; `gemini-3.5-flash-lite` interprets
the image and writes an answer. They do different jobs.

## 2. Embed the exact prepared input

Step 3 created `passages.jsonl`. Each record contains the reviewed text, its
source/page metadata, and an `embedding_text` made from:

```text
Document title
Section heading

Reviewed passage text
```

`prepared_passages()` checks that this exact input still matches its SHA-256
hash, has a valid model-specific token count, and has a unique passage ID.
Invalid/unverified inputs must go through preparation again. The 16 inputs
contain 1,953 verified tokens in total; the largest contains 218.

`build_index()` passes the inputs to `embed_texts()`, which calls:

```python
client.models.embed_content(
    model="gemini-embedding-001",
    contents=texts,
    config=types.EmbedContentConfig(
        task_type="RETRIEVAL_DOCUMENT",
        output_dimensionality=3072,
    ),
)
```

This is the existing Google SDK. For our list of 16 inputs, it sends one
`batchEmbedContents` HTTP request and returns 16 separate vectors, in input order.
The code checks the response count, vector dimensions, finite values, nonzero
length, and any reported truncation before saving anything.
[SDK embedding method](https://googleapis.github.io/python-genai/#embed-content).

**Learn:** A token count measures input length; a hash detects changed input;
an embedding represents meaning. Those three values are not interchangeable.

## 3. Keep a small local index

The index is `demo_data/rag_documents/embedding_index.json`. It contains:

- The embedding model, dimension count, and document task type.
- Every prepared passage's text and metadata, including source ID, physical PDF
  page, date, crop, geographic scope, review notes, and reuse information.
- Its corresponding vector.

For 16 passages, a flat JSON file and a linear scan are sufficient. We need no
vector database, framework, new Python dependency, or separate server. The key
and uploaded images are not stored in this file.

On another `embed` run, the code compares the model, dimensions, task type,
passage ID, exact input, and input hash. Matching records reuse their vectors.
Changing a source-scope note only updates metadata; changing the embedded title,
heading, or text requires a new vector. Changing the embedding settings requires
new vectors for all passages. Deleted passages are dropped on the next rebuild.

The complete new index is written to a temporary file, then replaces the old
file. An API failure leaves the previous index intact. Search rejects a missing,
stale, incompatible, or invalid index before making a query request.

**Learn:** Caching saves document API calls. It does not make new queries offline.
This is a local JSON index, not a trained model stored on your computer.

## 4. Turn a question into a search query

`semantic_search(question, context="", top_k=3)` joins the stripped question and,
if supplied, the user-reported context:

```text
What should I check before changing fertilizer?

Field context (user-reported):
Synthetic demo context: an irrigated field in Doukkala has uneven growth.
```

It checks the same text-length limits as the form, counts the exact combined
input with the embedding tokenizer, and rejects inputs over 2,048 tokens rather
than truncating them. It then embeds the input with `RETRIEVAL_QUERY` and the
same model/dimensions as the documents. Each search makes one token-count call
and one embedding call. User-session searches are not written to disk by this
code; the fixed synthetic evaluation questions are saved in their test report.

`RETRIEVAL_DOCUMENT` and `RETRIEVAL_QUERY` are a complementary pair: one prepares
reference text to be found, the other prepares the search request.
[Google's retrieval task guidance](https://aistudio.google.com/docs/embeddings#supported-task-types).

The image is not embedded or searched in this step. Retrieval uses the question
and supplied context; the vision model still receives the image separately.

**Learn:** Keyword search looks for shared words. Semantic search can match an
English nitrogen question to a French passage about *carence azotée*. That
capability must be checked on our own sources and questions.

## 5. Rank by cosine similarity

Python compares the query vector with every saved document vector using:

```text
cosine similarity = dot(query, passage) / (length(query) × length(passage))
```

`cosine_similarity()` computes the equivalent dot product after dividing each
vector by its length. This compares direction rather than magnitude. The code
sorts scores highest first, breaks exact ties by passage ID, and returns the
requested number of results. Every result keeps its original text and source
metadata; the large vector is omitted from search output.

The mathematical score range is -1 to 1. **A score of 0.75 does not mean a
75% chance of nutrient deficiency, or even a 75% chance that the passage answers
the question.** It is a ranking signal in this embedding space.
[Cosine similarity guidance](https://aistudio.google.com/docs/embeddings).

There is no calibrated relevance cutoff or automatic refusal yet. A nearest
neighbor exists even for an unrelated question. Step 5 must check whether the
retrieved evidence addresses the question and disclose missing evidence.

## 6. Run it yourself

From the project root:

```bash
source .venv/bin/activate
python rag.py embed
python rag.py search "What affects phosphorus availability in calcareous soils?"
python rag.py search "Quels facteurs influencent la disponibilité du phosphore dans un sol calcaire ?"
python rag.py search "What should I check before changing fertilizer?" --context "Synthetic demo context: an irrigated field in Doukkala has uneven growth."
```

The prepared index already exists. An unchanged `embed` run reports
`new_vectors: 0`, `reused_vectors: 16`, and `embedding_requests: 0`.
`--top-k 5` returns five results instead of three. Read the `score`, `text`,
`citation`, `publication_year`, `geographic_scope`, and `use_note` fields together.
Do not promote old regional guidance into a diagnosis of the uploaded parcel.

If you revise reviewed source sections, run `python rag.py` to rebuild/count
passages, then `python rag.py embed` to refresh vectors. The original default
preparation command still works; `python rag.py prepare` is its explicit alias.

## 7. What our live checks found

The three existing scenarios each have an English and French question. We added
one question with separate synthetic Doukkala context and three unrelated probes.
Expected passage IDs were fixed before the live search.

| Queries | Expected evidence | Observed top-three result |
| --- | --- | --- |
| Wheat nitrogen, English + French | PNTTA 155 p. 2 and PNTTA 62 p. 1 | Both expected passages found; expected passage at rank 1 |
| Calcareous-soil phosphorus, English + French | Two PNTTA 155 p. 4 passages | Both found; expected passage at rank 1 |
| Doukkala, English + French | Two Doukkala p. 1 passages and cereal irrigation p. 20 | Two of three found; cereal irrigation passage missed |
| Question + separate Doukkala context | Same three passages | One of three found; another Doukkala passage was rank 4 |

Across these seven relevant queries, hit@3 was 7/7 and MRR@3 was 1.0. Mean
expected-passage recall@3 was **0.810**, so retrieval is useful but incomplete.
Hit@3 asks whether at least one expected passage appeared in the first three;
recall@3 asks how many of the expected passages appeared. Rank 1 success does
not prove that every needed piece of evidence was found.

The football, Python-list, and French travel questions had no relevant passage
in our corpus, but still returned results. Their top scores were approximately
0.529, 0.481, and 0.508, versus 0.707–0.767 for the relevant probes. These few
examples do not justify a universal cutoff. We have not compared embedding
models/chunkers, run a held-out benchmark, or measured agronomic accuracy.

Read [the recorded results](step4_retrieval_test.json) and
[verification notes](step4_verification.md). To deliberately repeat the live
check, using API quota, run:

```bash
python -m tests.evaluate_search
```

## 8. Test the code without API calls

```bash
python -m unittest discover -s tests -v
```

`tests/test_search.py` uses the real SDK with a simulated HTTP transport to
check task types, exact payloads, token limits, response validation, quota errors,
and timeouts. Temporary indexes check caching, stale-data rejection, source
metadata, atomic replacement after success, and cosine ranking. The saved real
index is also checked offline. Existing image/form/model tests still run.

Network errors, missing credentials, and quota failures produce safe messages;
raw provider error details are not printed. There are no automatic API retries.

Try explaining this sequence in your own words: **prepare text → embed documents
once → embed a question → compare vectors → inspect retrieved source passages**.
Then explain why an apparently relevant passage can still be the wrong evidence
for a particular crop, field, or management decision.

Next is step 5: add selected references to the multimodal request and validate
the answer's citations. The Streamlit answer path has not changed in step 4.
