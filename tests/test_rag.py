from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import rag


class PassagePreparationTests(unittest.TestCase):
    def setUp(self):
        self.page = {"source_id": "SOURCE", "pdf_page": 2, "text": "Original OCR page", "mean_ocr_word_confidence": 80.0}
        self.document = {
            "id": "SOURCE", "title": "Wheat guide", "publication_year": None,
            "publication_date": None, "crops": ["wheat"], "geographic_scope": "Morocco",
            "pdf_file": "sources/wheat.pdf", "pdf_sha256": "source-hash", "source_url": "https://example.org/wheat.pdf",
            "language": "fr", "use_note": "Historical guidance", "license": "Not verified",
            "license_url": None, "pdf_pages": 4,
        }
        self.review = {"reviewed_on": "2026-11-12", "pages": [{
            "source_id": "SOURCE", "pdf_page": 2,
            "page_text_sha256": hashlib.sha256(self.page["text"].encode()).hexdigest(),
            "sections": [{"heading": "Soil testing", "text": "First complete paragraph.\n\nSecond complete paragraph."}],
            "review_note": "Checked selected prose against PDF; tables excluded.",
        }]}

    def build(self, review=None):
        return rag.build_passages(review or self.review, [self.page], [self.document])

    def test_paragraph_boundaries_are_preserved_without_silent_truncation(self):
        self.assertEqual(rag.split_paragraphs(" First line\nwraps.\n\nSecond paragraph. ", max_chars=22), ["First line wraps.", "Second paragraph."])
        with self.assertRaisesRegex(ValueError, "paragraph"):
            rag.split_paragraphs("x" * 23, max_chars=22)

    def test_provenance_unknown_date_and_token_input_are_preserved(self):
        passage = self.build()[0]
        self.assertEqual(passage["source_id"], "SOURCE")
        self.assertEqual(passage["pdf_page"], 2)
        self.assertIsNone(passage["publication_year"])
        self.assertEqual(passage["geographic_scope"], "Morocco")
        self.assertEqual(passage["crops"], ["wheat"])
        self.assertEqual(passage["citation"], "[SOURCE, PDF p. 2]")
        self.assertEqual(passage["embedding_text"], "Wheat guide\nSoil testing\n\nFirst complete paragraph.\n\nSecond complete paragraph.")
        self.assertEqual(passage["pdf_sha256"], "source-hash")

    def test_ids_stay_stable_when_other_reviewed_sections_are_added(self):
        original = self.build()[0]
        review = deepcopy(self.review)
        review["pages"][0]["sections"].insert(0, {"heading": "Other", "text": "A different complete paragraph."})
        extended = self.build(review)
        self.assertEqual(extended[1]["passage_id"], original["passage_id"])

    def test_missing_pages_changed_ocr_and_duplicate_passages_are_rejected(self):
        for change in ("missing", "changed", "duplicate"):
            with self.subTest(change=change):
                review = deepcopy(self.review)
                if change == "missing":
                    review["pages"][0]["pdf_page"] = 9
                elif change == "changed":
                    review["pages"][0]["page_text_sha256"] = "different-hash"
                else:
                    review["pages"][0]["sections"] *= 2
                with self.assertRaises(ValueError):
                    self.build(review)


class TokenValidationTests(unittest.TestCase):
    def test_actual_counter_checks_the_exact_embedding_input(self):
        passages = [{"passage_id": "p", "embedding_text": "Titre\nTexte français.", "embedding_sha256": "digest"}]
        client_patch = patch("rag.create_client")
        with client_patch as factory:
            factory.return_value.__enter__.return_value.models.count_tokens.return_value.total_tokens = 12
            result, requests = rag.verify_token_limits(passages, [])
            self.assertEqual(result[0]["token_count"], 12)
            self.assertEqual(requests, 1)
            factory.return_value.__enter__.return_value.models.count_tokens.assert_called_once_with(
                model="gemini-embedding-001", contents="Titre\nTexte français.")

    def test_unchanged_verified_inputs_reuse_counts_without_network_access(self):
        passage = {"passage_id": "p", "embedding_text": "Text", "embedding_sha256": "digest"}
        cached = {**passage, "token_count": 8, "token_model": "gemini-embedding-001"}
        with patch("rag.create_client") as factory:
            result, requests = rag.verify_token_limits([passage], [cached])
            self.assertEqual(result[0]["token_count"], 8)
            self.assertEqual(requests, 0)
            factory.assert_not_called()

    def test_over_limit_and_invalid_counts_fail_instead_of_truncating(self):
        for count in (2049, 0, None):
            with self.subTest(count=count), patch("rag.create_client") as factory:
                factory.return_value.__enter__.return_value.models.count_tokens.return_value.total_tokens = count
                with self.assertRaises(ValueError):
                    rag.verify_token_limits([{"passage_id": "p", "embedding_text": "Text", "embedding_sha256": "digest"}], [])

    def test_changed_embedding_text_does_not_reuse_the_old_count(self):
        old = {"passage_id": "p", "embedding_text": "Old text", "embedding_sha256": "old", "token_model": "gemini-embedding-001", "token_count": 2}
        new = {"passage_id": "p", "embedding_text": "New text", "embedding_sha256": "new"}
        with patch("rag.create_client") as factory:
            factory.return_value.__enter__.return_value.models.count_tokens.return_value.total_tokens = 3
            result, requests = rag.verify_token_limits([new], [old])
            self.assertEqual(requests, 1)
            self.assertEqual(result[0]["token_count"], 3)


class PreparedCorpusTests(unittest.TestCase):
    def test_saved_corpus_rebuilds_offline_from_reviewed_source_pages(self):
        review = json.loads((rag.DATA_DIR / "reviewed_sections.json").read_text())
        pages = rag.read_jsonl(rag.DATA_DIR / "recommended_pages.jsonl")
        documents = json.loads((rag.DATA_DIR / "manifest.json").read_text())["documents"]
        saved = rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")
        with patch("rag.create_client") as client:
            rebuilt, requests = rag.verify_token_limits(rag.build_passages(review, pages, documents), saved)
        self.assertEqual(rebuilt, saved)
        self.assertEqual(requests, 0)
        client.assert_not_called()
        self.assertEqual(len({passage["source_id"] for passage in saved}), 8)

    def test_three_demo_cases_have_reviewed_passages_and_correct_pages(self):
        cases = json.loads(Path(__file__).with_name("rag_review_cases.json").read_text())
        passages = {passage["passage_id"]: passage for passage in rag.read_jsonl(rag.DATA_DIR / "passages.jsonl")}
        self.assertEqual(len(cases), 3)
        for case in cases:
            with self.subTest(case=case["id"]):
                selected = [passages[identifier] for identifier in case["required_passage_ids"]]
                selected_pages = {(passage["source_id"], passage["pdf_page"]) for passage in selected}
                self.assertTrue({tuple(page) for page in case["required_source_pages"]} <= selected_pages)
                self.assertTrue(all(passage["review_status"] == "selected_prose_verified_against_pdf" for passage in selected))
                self.assertTrue(all(0 < passage["token_count"] <= 2048 for passage in selected))

    def test_review_report_keeps_pending_pages_and_tables_explicit(self):
        report = json.loads((rag.DATA_DIR / "passage_review_report.json").read_text())
        self.assertEqual(len(report["pages"]), 50)
        self.assertEqual(sum(page["status"] == "not_reviewed_for_passages" for page in report["pages"]), 40)
        self.assertEqual(sum(page["low_ocr_confidence"] for page in report["pages"]), 3)
        self.assertTrue(all(page["numerical_tables_require_review"] for page in report["pages"]))

    def test_token_verification_failure_preserves_existing_output(self):
        fixture = PassagePreparationTests()
        fixture.setUp()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sources").mkdir()
            pdf_bytes = b"test-source-pdf"
            (root / "sources/wheat.pdf").write_bytes(pdf_bytes)
            fixture.document["pdf_sha256"] = hashlib.sha256(pdf_bytes).hexdigest()
            (root / "manifest.json").write_text(json.dumps({"documents": [fixture.document]}))
            (root / "recommended_pages.jsonl").write_text(json.dumps(fixture.page) + "\n")
            (root / "reviewed_sections.json").write_text(json.dumps(fixture.review))
            previous = json.dumps({"passage_id": "previous"}) + "\n"
            (root / "passages.jsonl").write_text(previous)
            with patch("rag.create_client", side_effect=rag.GeminiError("Simulated credential failure")):
                with self.assertRaises(rag.GeminiError):
                    rag.prepare_corpus(root)
            self.assertEqual((root / "passages.jsonl").read_text(), previous)
            self.assertFalse((root / "passage_review_report.json").exists())


if __name__ == "__main__":
    unittest.main()
