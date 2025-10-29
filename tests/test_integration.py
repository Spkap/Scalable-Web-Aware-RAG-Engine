"""
Integration tests for WebRAG system.
Runs an end-to-end scenario: health -> ingest -> wait -> query.

These tests assume the services are running locally (docker-compose up -d)
and the API is reachable at http://localhost:8000.
"""
from __future__ import annotations

import os
import pytest
import requests
import time
import uuid

# Allow overriding the integration test target via environment variable.
# Default: http://localhost:8000
BASE_URL = os.environ.get("WEBRAG_BASE_URL", "http://localhost:8000")
TEST_TIMEOUT = 60


class TestWebRAGIntegration:
    """Integration test suite for the WebRAG RAG pipeline."""

    job_id: str | None = None

    def test_01_health_check(self):
        resp = requests.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_02_ingest_url(self):
        payload = {"url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}
        resp = requests.post(f"{BASE_URL}/ingest-url", json=payload, timeout=10)
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data.get("status") in ("pending", "processing")
        # store job id
        TestWebRAGIntegration.job_id = data["job_id"]
        # validate uuid
        uuid.UUID(TestWebRAGIntegration.job_id)

    def test_03_check_job_status(self):
        assert self.job_id is not None
        time.sleep(2)
        resp = requests.get(f"{BASE_URL}/status/{self.job_id}", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == self.job_id
        assert data["status"] in ["pending", "processing", "completed", "failed"]

    def test_04_wait_for_completion(self):
        assert self.job_id is not None
        for i in range(TEST_TIMEOUT):
            resp = requests.get(f"{BASE_URL}/status/{self.job_id}", timeout=10)
            assert resp.status_code == 200
            data = resp.json()
            if data["status"] == "completed":
                return
            if data["status"] == "failed":
                pytest.fail(f"Ingestion failed: {data.get('error_message')}")
            time.sleep(1)
        pytest.fail("Ingestion did not complete within timeout")

    def test_05_query_knowledge_base(self):
        payload = {"question": "What is retrieval augmented generation?", "top_k": 5}
        resp = requests.post(f"{BASE_URL}/query", json=payload, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "metadata" in data
        assert len(data["answer"]) > 50
        assert ("retrieval" in data["answer"].lower()) or ("rag" in data["answer"].lower())
        assert len(data["sources"]) > 0 and len(data["sources"]) <= 5

    def test_06_query_with_filters(self):
        payload = {
            "question": "What is RAG?",
            "top_k": 3,
            "filters": {"source_url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"},
        }
        resp = requests.post(f"{BASE_URL}/query", json=payload, timeout=30)
        assert resp.status_code == 200
        data = resp.json()
        for src in data.get("sources", []):
            assert "wikipedia.org" in src.get("source_url", "")

    def test_07_invalid_url_ingestion(self):
        invalid_urls = ["not-a-url", "ftp://example.com", "javascript:alert(1)", ""]
        for invalid in invalid_urls:
            resp = requests.post(f"{BASE_URL}/ingest-url", json={"url": invalid}, timeout=10)
            # Pydantic validation returns 422 for invalid URLs
            assert resp.status_code == 422

    def test_08_empty_query(self):
        resp = requests.post(f"{BASE_URL}/query", json={"question": ""}, timeout=10)
        # Pydantic validation should return 422 for empty question
        assert resp.status_code == 422

    def test_09_query_nonexistent_content(self):
        payload = {"question": "What is the capital of Atlantis?", "filters": {"source_url": "https://nonexistent.example.com"}}
        resp = requests.post(f"{BASE_URL}/query", json=payload, timeout=30)
        # Either 404 or a 200 with an inability answer is acceptable
        if resp.status_code == 200:
            data = resp.json()
            assert "cannot answer" in data.get("answer", "").lower()
        else:
            assert resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 
