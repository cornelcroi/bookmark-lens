"""
Embedding generation service using sentence-transformers.

Converts text to vector embeddings for semantic search.
"""

import logging
import numpy as np
from typing import Optional, List
from sentence_transformers import SentenceTransformer

from ..config import Config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings for text using local transformer models."""

    def __init__(self, config: Config):
        self.config = config
        self.model_name = config.embedding_model_name
        self.dimension = config.embedding_dimension

        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        # Validate dimension
        test_emb = self.model.encode(["test"], normalize_embeddings=True)
        actual_dim = test_emb.shape[1]
        if actual_dim != self.dimension:
            raise ValueError(
                f"Model {self.model_name} produces {actual_dim}D vectors, "
                f"but config specifies {self.dimension}D"
            )
        logger.info(f"Embedding model loaded: {self.model_name} ({self.dimension}D)")

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate normalized embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Normalized embedding vector (L2 norm = 1)
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.dimension, dtype=np.float32)

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True  # L2 normalization for cosine similarity
        )

        return embedding.astype(np.float32)

    def build_embedding_text(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        content_text: Optional[str] = None,
        user_note: Optional[str] = None,
        summary: Optional[str] = None,  # Phase 2
        tags: Optional[List[str]] = None,  # Phase 2
        topic: Optional[str] = None  # Phase 2
    ) -> str:
        """
        Combine bookmark fields into text for embedding.

        Field priority (most important first):
        1. Title
        2. User note (captures user intent)
        3. Summary (Phase 2)
        4. Tags (Phase 2)
        5. Topic (Phase 2)
        6. Description
        7. Content (truncated)

        Args:
            title: Page title
            description: Meta description
            content_text: Extracted page content
            user_note: User's context/note
            summary: LLM summary (Phase 2)
            tags: Tags (Phase 2)
            topic: Topic classification (Phase 2)

        Returns:
            Combined text for embedding
        """
        parts = []

        if title:
            parts.append(f"Title: {title}")

        if user_note:
            parts.append(f"Note: {user_note}")

        if summary:  # Phase 2
            parts.append(f"Summary: {summary}")

        if tags:  # Phase 2
            parts.append(f"Tags: {', '.join(tags)}")

        if topic:  # Phase 2
            parts.append(f"Topic: {topic}")

        if description:
            parts.append(f"Description: {description}")

        if content_text:
            # Truncate content to avoid overwhelming the embedding
            content = content_text[:3000]  # ~500-700 words
            parts.append(f"Content: {content}")

        return "\n".join(parts)
