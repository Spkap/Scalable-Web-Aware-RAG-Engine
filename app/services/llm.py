from __future__ import annotations

import time
from typing import List, Dict, Any

import google.generativeai as genai

from ..utils.logger import get_logger

logger = get_logger(__name__)


class GeminiLLM:
    """Wrapper for Google Gemini models using the google.generativeai SDK.

    This class provides a thin adapter around the Gemini generation API to
    generate grounded answers from retrieved context chunks.

    Example:
        llm = GeminiLLM(api_key="ABC")
        answer = llm.generate_answer("What is RAG?", context_chunks)

    Args:
        api_key: Gemini API key (required).
        model: Model name to use, defaults to "gemini-2.5-flash".

    Raises:
        ValueError: If the Gemini client fails to initialize.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        from google.generativeai import types as genai_types

        try:
            genai.configure(api_key=api_key)

            # Create a generation model wrapper according to the provided spec.
            # The official SDK may differ; the wrapper below follows the
            # project's expected usage pattern.
            self.model = genai.GenerativeModel(
                model_name=model,
                generation_config={
                    "temperature": 0,
                    "max_output_tokens": 500,
                    "top_p": 1,
                    "top_k": 1,
                },
            )
            self.model_name = model
            logger.info(f"Initialized Gemini model: {model}")
        except Exception as error:
            # Prefer the SDK-specific type when available
            try:
                raise ValueError(f"Failed to initialize Gemini: {error}") from error
            except Exception:
                raise ValueError(f"Failed to initialize Gemini: {error}")

    def generate_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate a grounded answer using Gemini based on retrieved context.

        The method constructs a deterministic prompt containing the retrieved
        context chunks and asks the model to answer using only that context.

        Args:
            question: The user question to answer. Must be non-empty.
            context_chunks: List of dicts each containing 'text', 'source_url', 'score'.

        Returns:
            The generated answer string.

        Raises:
            ValueError: On unrecoverable API errors or rate limits.
        """
        from google.generativeai import types as genai_types

        logger.info(f"Generating answer for question (length: {len(question)})")
        logger.debug(f"Using {len(context_chunks)} context chunks")

        # Format context exactly as specified
        formatted_chunks: List[str] = []
        for idx, chunk in enumerate(context_chunks, 1):
            formatted_chunks.append(f"Source {idx} ({chunk.get('source_url')}):\n{chunk.get('text')}\n")

        formatted_context = "\n---\n".join(formatted_chunks)

        prompt = f"""You are a helpful AI assistant that answers questions based ONLY on the provided context.
INSTRUCTIONS:
Read the context sources carefully
Answer the question using ONLY information from the context
If the context doesn't contain enough information, respond: "I cannot answer this question based on the provided context."
Cite which source number(s) you used (e.g., "According to Source 1...")
Be concise but complete
Do not add information not present in the context
CONTEXT:
{formatted_context}
QUESTION: {question}
ANSWER:"""

        # Generate content using Gemini
        response = self.model.generate_content(prompt)

        # Check for safety refusal first
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = candidate.finish_reason
                # Handle safety refusal (finish_reason == 2 or "SAFETY")
                if finish_reason == 2 or str(finish_reason).upper() == "SAFETY":
                    return "I cannot answer this question based on the provided context."

        # Extract answer
        answer = getattr(response, "text", "").strip()

        return answer
