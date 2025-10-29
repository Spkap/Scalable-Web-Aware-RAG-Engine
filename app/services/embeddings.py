from __future__ import annotations

import time
from typing import List

import google.generativeai as genai
from google.genai import types

from ..utils.logger import get_logger
from ..config import settings

logger = get_logger(__name__)


class GeminiEmbeddings:
    """Wrapper around Gemini embeddings with retries and backoff.

    The class expects a valid GOOGLE_API_KEY in settings or provided to __init__.
    Uses gemini-embedding-001 model with 1536 dimensions.
    """

    def __init__(self, api_key: str | None = None, model: str = "gemini-embedding-001", output_dimensionality: int = 1536) -> None:
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model = model
        self.output_dimensionality = output_dimensionality
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai
        except Exception as exc:  # pragma: no cover - runtime import
            logger.error("Failed to configure Gemini client", extra={"error": str(exc)})
            raise

    def _with_retries(self, func, *args, **kwargs):
        attempt = 0
        backoff = 1.0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                attempt += 1
                error_str = str(exc).lower()
                is_rate_limit = "429" in error_str or "rate limit" in error_str or "quota exceeded" in error_str or "resource exhausted" in error_str
                
                if is_rate_limit:
                    logger.warning("Gemini API rate limit hit, backing off", extra={"attempt": attempt, "backoff": backoff})
                    if attempt >= 5:  # More retries for rate limits
                        logger.error("Gemini API rate limit persisted after retries", extra={"error": str(exc)})
                        raise
                    time.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                else:
                    logger.warning("Gemini API call failed, retrying", extra={"attempt": attempt, "error": str(exc)})
                    if attempt >= 3:
                        logger.error("Gemini API failed after retries", extra={"error": str(exc)})
                        raise
                    time.sleep(backoff)
                    backoff *= 2

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents and return a list of vectors."""

        def _call(texts_batch: List[str]):
            # For batch embedding, we need to make individual calls
            embeddings = []
            for text in texts_batch:
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document",
                    output_dimensionality=self.output_dimensionality
                )
                embeddings.append(result["embedding"])
            return embeddings

        return self._with_retries(_call, texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string and return its vector."""

        def _call(query_text: str):
            result = genai.embed_content(
                model=self.model,
                content=query_text,
                task_type="retrieval_query",
                output_dimensionality=self.output_dimensionality
            )
            return result

        resp = self._with_retries(_call, text)
        return resp.get("embedding", [])


