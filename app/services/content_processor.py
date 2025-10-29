from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentProcessor:
    """Utility class to fetch, clean and chunk web content.

    Methods are intentionally small and testable. `fetch_url_content` runs the
    synchronous requests call inside a thread to keep the interface async.
    """

    USER_AGENT = {"User-Agent": "WebRAG/1.0"}

    @staticmethod
    async def fetch_url_content(url: str) -> str:
        """Fetch raw HTML from a URL using requests in a thread.

        Raises:
            ValueError: when non-200 response is returned.
        """
        def _get(u: str) -> str:
            resp = requests.get(u, headers=ContentProcessor.USER_AGENT, timeout=10)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch {u}: HTTP {resp.status_code}")
            return resp.text

        try:
            html = await asyncio.to_thread(_get, url)
            return html
        except Exception as exc:
            logger.error("Error fetching url", extra={"url": url, "error": str(exc)})
            raise
    @staticmethod
    def fetch_url_content_sync(url: str) -> str:
        """Fetch raw HTML from a URL synchronously.

        Raises:
            ValueError: when non-200 response is returned.
        """
        try:
            resp = requests.get(url, headers=ContentProcessor.USER_AGENT, timeout=10)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch {url}: HTTP {resp.status_code}")
            return resp.text
        except Exception as exc:
            logger.error("Error fetching url", extra={"url": url, "error": str(exc)})
            raise

    @staticmethod
    def clean_html(html: str) -> str:
        """Remove scripts/styles and extract visible text using BeautifulSoup.

        Normalizes whitespace and returns a single string containing the page text.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted tags
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        # Prefer body text, fall back to whole document
        body = soup.body.get_text(separator=" ") if soup.body else soup.get_text(separator=" ")
        # Normalize whitespace
        cleaned = " ".join(body.split())
        return cleaned

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
        """Chunk text into smaller pieces using LangChain's RecursiveCharacterTextSplitter.

        This is a thin wrapper that imports the correct splitter implementation at
        runtime (supports both the standalone `langchain-text-splitters` package
        and older `langchain.text_splitter` locations).
        """
        try:
            # Preferred newer package
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            try:
                # Fallback for older LangChain versions
                from langchain.text_splitter import RecursiveCharacterTextSplitter
            except ImportError:
                raise ImportError(
                    "Could not import RecursiveCharacterTextSplitter from langchain_text_splitters or langchain.text_splitter"
                )

        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        return text_splitter.split_text(text)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rudimentary token estimate: words * 1.3 rounded to int."""
        words = len(text.split())
        return int(words * 1.3)
 
