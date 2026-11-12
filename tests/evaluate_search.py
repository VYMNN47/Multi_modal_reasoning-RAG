"""Explicit live check: python -m tests.evaluate_search (uses Gemini API quota)."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

import rag


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "step4_retrieval_test.json"


def retrieval_metrics(results: list[dict], required_ids: list[str], required_pages: list[list]) -> dict:
    top = results[:3]
    expected = set(required_ids)
    hits = [rank for rank, result in enumerate(top, 1) if result["passage_id"] in expected]
    pages = {(result["source_id"], result["pdf_page"]) for result in top}
    return {
        "hit_at_3": bool(hits),
        "passage_recall_at_3": len(hits) / len(expected),
        "reciprocal_rank_at_3": 1 / hits[0] if hits else 0.0,
        "all_expected_pages_in_top_3": {tuple(page) for page in required_pages} <= pages,
    }


def evaluate() -> dict:
    cases = json.loads(Path(__file__).with_name("rag_review_cases.json").read_text())
    queries = [{
        "id": f"{case['id']}_{language}", "question": case[f"question_{language}"], "context": "",
        "required_passage_ids": case["required_passage_ids"], "required_source_pages": case["required_source_pages"],
    } for case in cases for language in ("en", "fr")]
    queries.append({
        "id": "doukkala_supplied_context", "question": "What water, soil, and management evidence should be checked before changing fertilizer?",
        "context": "Synthetic demo context: an irrigated field in Doukkala reportedly has uneven growth.",
        "required_passage_ids": cases[2]["required_passage_ids"], "required_source_pages": cases[2]["required_source_pages"],
    })
    queries.extend({"id": identifier, "question": question, "context": ""} for identifier, question in (
        ("unrelated_football", "Who won the men's football World Cup in 2018?"),
        ("unrelated_python", "How do I reverse a Python list?"),
        ("unrelated_french_travel", "Comment réserver un billet de train pour Paris ?"),
    ))
    checked = []
    for query in queries:
        started = perf_counter()
        results = rag.semantic_search(query["question"], query["context"], top_k=5)
        item = {**query, "elapsed_seconds": round(perf_counter() - started, 3), "results": [{
            key: result[key] for key in (
                "passage_id", "source_id", "pdf_page", "citation", "score", "section", "text",
                "publication_year", "geographic_scope", "source_url", "use_note",
            )
        } for result in results]}
        if "required_passage_ids" in query:
            item["metrics"] = retrieval_metrics(results, query["required_passage_ids"], query["required_source_pages"])
        else:
            item["observation"] = "No relevant passage exists for this question. The ranker still returns nearest neighbors; no abstention filter is implemented."
        checked.append(item)
        print(f"{query['id']}: top score={results[0]['score']:.4f}; {item.get('metrics', {}).get('hit_at_3', 'unrelated probe')}", flush=True)
    relevant = [item["metrics"] for item in checked if "metrics" in item]
    return {
        "checked_at": datetime.now(ZoneInfo("Africa/Casablanca")).isoformat(timespec="seconds"),
        "settings": rag.INDEX_SETTINGS, "query_task_type": "RETRIEVAL_QUERY",
        "index_sha256": hashlib.sha256((rag.DATA_DIR / "embedding_index.json").read_bytes()).hexdigest(),
        "passages_sha256": hashlib.sha256((rag.DATA_DIR / "passages.jsonl").read_bytes()).hexdigest(),
        "query_count": len(checked), "query_embedding_calls": len(checked), "query_token_count_calls": len(checked),
        "aggregate": {"relevant_query_count": len(relevant), "hit_at_3": sum(item["hit_at_3"] for item in relevant) / len(relevant),
                      "mean_passage_recall_at_3": sum(item["passage_recall_at_3"] for item in relevant) / len(relevant),
                      "mrr_at_3": sum(item["reciprocal_rank_at_3"] for item in relevant) / len(relevant)},
        "limits": "Small fixed demo set, not a held-out agronomic benchmark. No model/chunker comparison, calibrated relevance cutoff, generated answer, or agronomic accuracy evaluation.",
        "queries": checked,
    }


if __name__ == "__main__":
    try:
        report = evaluate()
        rag.atomic_write(REPORT, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    except (rag.GeminiError, OSError, ValueError):
        raise SystemExit("Live retrieval check failed; the existing report was not replaced. Check the index, key, connection, and quota.") from None
    print(json.dumps(report["aggregate"], indent=2))
    if report["aggregate"]["hit_at_3"] < 1:
        raise SystemExit("At least one expected demo passage missed the top three. Inspect docs/step4_retrieval_test.json.")
