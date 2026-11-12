import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from google import genai
import httpx2

import rag
from tests.evaluate_search import retrieval_metrics


REAL_CLIENT = genai.Client


def vector(first=1.0, second=0.0):
    return [first, second] + [0.0] * 3070


class EmbeddingRequestTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.status = 200
        self.failure = None
        self.token_count = 10
        self.payload = {"embeddings": [{"values": vector()}]}
        key_patch = patch("model.get_api_key", return_value="test-key")
        key_patch.start()
        self.addCleanup(key_patch.stop)
        client_patch = patch("model.genai.Client", side_effect=self.make_client)
        client_patch.start()
        self.addCleanup(client_patch.stop)

    def make_client(self, **options):
        options["http_options"] = options["http_options"].model_copy(update={
            "client_args": {"transport": httpx2.MockTransport(self.handle_request), "trust_env": False},
        })
        return REAL_CLIENT(**options)

    def handle_request(self, request):
        self.requests.append(request)
        if self.failure:
            raise self.failure("sensitive-provider-detail", request=request)
        if self.status != 200:
            return httpx2.Response(self.status, json={"error": {"code": self.status, "message": "sensitive-provider-detail"}})
        if request.url.path.endswith(":countTokens"):
            return httpx2.Response(200, json={"totalTokens": self.token_count})
        return httpx2.Response(200, json=self.payload)

    def test_documents_send_the_exact_inputs_as_a_batch_with_retrieval_settings(self):
        self.payload["embeddings"].append({"values": vector(0, 2)})
        texts = ["Titre\nTexte français.", "Other title\nOther passage."]
        result = rag.embed_texts(texts, "RETRIEVAL_DOCUMENT")
        self.assertEqual(result, [vector(), vector(0, 2)])
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertTrue(request.url.path.endswith("/gemini-embedding-001:batchEmbedContents"))
        self.assertEqual(request.url.host, "generativelanguage.googleapis.com")
        self.assertEqual(request.headers["x-goog-api-key"], "test-key")
        self.assertNotIn("test-key", str(request.url))
        body = json.loads(request.content)
        self.assertEqual([item["content"]["parts"][0]["text"] for item in body["requests"]], texts)
        self.assertTrue(all(item["taskType"] == "RETRIEVAL_DOCUMENT" and item["outputDimensionality"] == 3072 for item in body["requests"]))
        self.assertNotIn("test-key", request.content.decode())

    def test_query_is_counted_without_truncation_and_uses_the_query_task(self):
        text = "What evidence is needed?\n\nField context (user-reported):\nBlé en Doukkala."
        rag.embed_texts([text], "RETRIEVAL_QUERY")
        self.assertEqual(len(self.requests), 2)
        counter = json.loads(self.requests[0].content)
        self.assertEqual(counter["contents"][0]["parts"][0]["text"], text)
        body = json.loads(self.requests[1].content)
        self.assertEqual(body["requests"][0]["content"]["parts"][0]["text"], text)
        self.assertEqual(body["requests"][0]["taskType"], "RETRIEVAL_QUERY")
        self.assertEqual(body["requests"][0]["outputDimensionality"], 3072)

    def test_invalid_query_token_counts_never_reach_embedding(self):
        for count in (0, 2049, None):
            with self.subTest(count=count):
                self.token_count = count
                before = len(self.requests)
                with self.assertRaisesRegex(rag.GeminiError, "token"):
                    rag.embed_texts(["Question"], "RETRIEVAL_QUERY")
                self.assertEqual(len(self.requests) - before, 1)

    def test_missing_wrong_size_zero_nonfinite_and_truncated_vectors_are_rejected(self):
        payloads = [
            {}, {"embeddings": []}, {"embeddings": [{"values": [1, 2]}]},
            {"embeddings": [{"values": vector(0, 0)}]},
            {"embeddings": [{"values": vector("NaN")}]},
            {"embeddings": [{"values": vector("Infinity")}]},
            {"embeddings": [{"values": vector(), "statistics": {"truncated": True}}]},
        ]
        for payload in payloads:
            with self.subTest(payload_kind=list(payload)):
                self.payload = payload
                with self.assertRaises(rag.GeminiError):
                    rag.embed_texts(["Prepared passage"], "RETRIEVAL_DOCUMENT")

    def test_provider_errors_are_safe_and_not_retried(self):
        for code, hint in ((400, "rejected"), (401, "key"), (403, "key"), (404, "model"), (429, "quota"), (503, "unavailable")):
            with self.subTest(code=code):
                self.status = code
                before = len(self.requests)
                with self.assertRaises(rag.GeminiError) as caught:
                    rag.embed_texts(["Prepared passage"], "RETRIEVAL_DOCUMENT")
                self.assertIn(hint, str(caught.exception).lower())
                self.assertNotIn("sensitive-provider-detail", str(caught.exception))
                self.assertEqual(len(self.requests) - before, 1)

    def test_timeout_and_connection_errors_are_safe(self):
        for failure, hint in ((httpx2.ReadTimeout, "timed out"), (httpx2.ConnectError, "connect")):
            with self.subTest(failure=failure):
                self.failure = failure
                with self.assertRaises(rag.GeminiError) as caught:
                    rag.embed_texts(["Prepared passage"], "RETRIEVAL_DOCUMENT")
                self.assertIn(hint, str(caught.exception))
                self.assertNotIn("sensitive-provider-detail", str(caught.exception))

    def test_empty_inputs_and_unsupported_tasks_make_no_request(self):
        for texts, task in (([], "RETRIEVAL_DOCUMENT"), ([" "], "RETRIEVAL_QUERY"), (["Text"], "UNKNOWN")):
            with self.subTest(task=task), self.assertRaises(rag.GeminiError):
                rag.embed_texts(texts, task)
        self.assertFalse(self.requests)


class SemanticSearchTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.passages = rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")[:3]
        self.save_passages()
        self.vectors = [vector(), vector(0, 2), vector(-3)]
        self.index_path = self.root / "embedding_index.json"

    def save_passages(self):
        (self.root / "passages.jsonl").write_text("".join(json.dumps(p) + "\n" for p in self.passages))

    def build(self):
        with patch("rag.embed_texts", return_value=self.vectors) as embed:
            summary = rag.build_index(self.root)
            embed.assert_called_once_with([p["embedding_text"] for p in self.passages], "RETRIEVAL_DOCUMENT")
        return summary

    def test_index_saves_metadata_and_reloads_with_no_embedding_call(self):
        summary = self.build()
        self.assertEqual(summary["new_vectors"], 3)
        self.assertEqual(summary["embedding_requests"], 1)
        with patch("rag.create_client") as client:
            loaded = rag.load_index(self.root)
            again = rag.build_index(self.root)
        client.assert_not_called()
        self.assertEqual(again["new_vectors"], 0)
        self.assertEqual(again["reused_vectors"], 3)
        self.assertEqual(again["embedding_requests"], 0)
        self.assertEqual([{k: v for k, v in record.items() if k != "vector"} for record in loaded], self.passages)

    def test_changed_text_embeds_only_that_passage_and_metadata_updates_reuse_vectors(self):
        self.build()
        self.passages[0]["use_note"] = "A corrected scope note."
        self.save_passages()
        with patch("rag.create_client") as client:
            self.assertEqual(rag.build_index(self.root)["new_vectors"], 0)
        client.assert_not_called()
        self.assertEqual(rag.load_index(self.root)[0]["use_note"], "A corrected scope note.")
        passage = self.passages[1]
        passage["embedding_text"] += " Updated reviewed context."
        passage["embedding_sha256"] = hashlib.sha256(passage["embedding_text"].encode()).hexdigest()
        self.save_passages()
        with patch("rag.embed_texts", return_value=[vector(2, 1)]) as embed:
            summary = rag.build_index(self.root)
            embed.assert_called_once_with([passage["embedding_text"]], "RETRIEVAL_DOCUMENT")
        self.assertEqual(summary["new_vectors"], 1)
        self.assertEqual(summary["reused_vectors"], 2)

    def test_model_dimensions_or_task_changes_invalidate_the_cache(self):
        self.build()
        original = json.loads(self.index_path.read_text())
        for field, value in (("model", "other-model"), ("dimensions", 768), ("document_task_type", "SEMANTIC_SIMILARITY")):
            with self.subTest(field=field):
                changed = {**original, "settings": {**original["settings"], field: value}}
                self.index_path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(rag.GeminiError, "index"):
                    rag.load_index(self.root)
                self.assertEqual(self.build()["new_vectors"], 3)

    def test_embedding_failure_preserves_the_existing_index(self):
        self.build()
        previous = self.index_path.read_bytes()
        self.passages[0]["embedding_text"] += " Changed."
        self.passages[0]["embedding_sha256"] = hashlib.sha256(self.passages[0]["embedding_text"].encode()).hexdigest()
        self.save_passages()
        with patch("rag.embed_texts", side_effect=rag.GeminiError("Simulated quota failure")):
            with self.assertRaises(rag.GeminiError):
                rag.build_index(self.root)
        self.assertEqual(self.index_path.read_bytes(), previous)

    def test_missing_stale_and_corrupt_indexes_fail_before_a_query_request(self):
        with patch("rag.create_client") as client:
            with self.assertRaisesRegex(rag.GeminiError, "index"):
                rag.semantic_search("Question", data_dir=self.root)
        client.assert_not_called()
        self.build()
        original = self.index_path.read_text()
        self.passages[0]["use_note"] = "Changed metadata"
        self.save_passages()
        with patch("rag.create_client") as client:
            with self.assertRaisesRegex(rag.GeminiError, "stale"):
                rag.semantic_search("Question", data_dir=self.root)
        client.assert_not_called()
        self.passages[0]["use_note"] = json.loads(original)["passages"][0]["use_note"]
        self.save_passages()
        for corrupted in ("not json", original.replace('"vector": [1.0', '"vector": [NaN', 1)):
            with self.subTest(corruption=corrupted[:8]):
                self.index_path.write_text(corrupted)
                with self.assertRaises(rag.GeminiError):
                    rag.load_index(self.root)

    def test_changed_hash_over_limit_unverified_or_duplicate_passages_make_no_request(self):
        original = json.loads(json.dumps(self.passages))
        for change in ("hash", "limit", "model", "duplicate", "empty"):
            with self.subTest(change=change), patch("rag.create_client") as client:
                self.passages = json.loads(json.dumps(original))
                if change == "hash":
                    self.passages[0]["embedding_text"] += " Changed without recounting."
                elif change == "limit":
                    self.passages[0]["token_count"] = 2049
                elif change == "model":
                    self.passages[0]["token_model"] = "unverified"
                elif change == "duplicate":
                    self.passages.append(self.passages[0])
                else:
                    self.passages = []
                self.save_passages()
                with self.assertRaises(rag.GeminiError):
                    rag.build_index(self.root)
                client.assert_not_called()

    def test_search_ranks_cosine_scores_and_returns_source_text_without_vectors(self):
        self.build()
        with patch("rag.embed_texts", return_value=[vector(10)]) as embed:
            results = rag.semantic_search(" Question? ", " Blé en Doukkala. ", data_dir=self.root)
            embed.assert_called_once_with(["Question?\n\nField context (user-reported):\nBlé en Doukkala."], "RETRIEVAL_QUERY")
        self.assertEqual([result["passage_id"] for result in results], [p["passage_id"] for p in self.passages])
        self.assertEqual([result["score"] for result in results], [1.0, 0.0, -1.0])
        for result in results:
            self.assertNotIn("vector", result)
            self.assertIn("text", result)
            self.assertIn("citation", result)
            self.assertIn("geographic_scope", result)

    def test_search_validates_text_and_k_before_calling_the_api(self):
        for question, context, k in ((" ", "", 3), ("x" * 2001, "", 3), ("Q", "x" * 4001, 3), ("Q", "", 0), ("Q", "", True)):
            with self.subTest(question_size=len(question), k=k), patch("rag.create_client") as client:
                with self.assertRaises(rag.GeminiError):
                    rag.semantic_search(question, context, k, self.root)
                client.assert_not_called()

    def test_cosine_uses_direction_instead_of_vector_length(self):
        self.assertEqual(rag.cosine_similarity(vector(2), vector(8)), 1)
        self.assertEqual(rag.cosine_similarity(vector(2), vector(0, 4)), 0)
        self.assertEqual(rag.cosine_similarity(vector(2), vector(-8)), -1)
        self.assertAlmostEqual(rag.cosine_similarity(vector(2, 2), vector(3, 0)), 1 / math.sqrt(2))
        for invalid in ([1], vector(0, 0), vector(float("nan"))):
            with self.assertRaises(rag.GeminiError):
                rag.cosine_similarity(invalid, vector())


class SavedIndexTests(unittest.TestCase):
    def test_real_index_matches_the_prepared_passages_and_loads_offline(self):
        with patch("rag.create_client") as client:
            records = rag.load_index()
        client.assert_not_called()
        self.assertEqual(len(records), 16)
        self.assertEqual(len({record["source_id"] for record in records}), 8)
        for record in records:
            self.assertAlmostEqual(rag.vector_norm(record["vector"]), 1.0, places=5)

    def test_evaluation_counts_only_expected_passages_and_their_ranks(self):
        results = [
            {"passage_id": "unrelated", "source_id": "B", "pdf_page": 9},
            {"passage_id": "expected-one", "source_id": "A", "pdf_page": 1},
            {"passage_id": "other", "source_id": "B", "pdf_page": 2},
            {"passage_id": "expected-two", "source_id": "A", "pdf_page": 2},
        ]
        metrics = retrieval_metrics(results, ["expected-one", "expected-two"], [["A", 1], ["A", 2]])
        self.assertTrue(metrics["hit_at_3"])
        self.assertEqual(metrics["passage_recall_at_3"], 0.5)
        self.assertEqual(metrics["reciprocal_rank_at_3"], 0.5)
        self.assertFalse(metrics["all_expected_pages_in_top_3"])


if __name__ == "__main__":
    unittest.main()
