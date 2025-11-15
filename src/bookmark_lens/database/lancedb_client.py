"""
LanceDB client for storing and searching embedding vectors.

Provides fast semantic search capabilities for bookmarks.
"""

import lancedb
import numpy as np
import pyarrow as pa
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class LanceDBClient:
    """Client for managing LanceDB vector operations."""

    def __init__(self, db_path: str, embedding_dimension: int):
        """
        Initialize LanceDB client.

        Args:
            db_path: Path to LanceDB directory
            embedding_dimension: Size of embedding vectors (e.g., 384 for MiniLM)
        """
        self.db_path = db_path
        self.embedding_dimension = embedding_dimension

        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect to LanceDB
        self.db = lancedb.connect(db_path)
        self.table_name = "bookmark_embeddings"
        self.table = None

    def initialize_table(self) -> None:
        """
        Create embeddings table if it doesn't exist.

        Schema:
            - bookmark_id: UUID linking to DuckDB bookmarks table
            - embedding: Vector array (float32)
            - embedding_text: Text that was embedded (for debugging)
            - model_name: Name of embedding model used
            - created_at: Timestamp
        """
        # Define schema
        schema = pa.schema([
            pa.field("bookmark_id", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), self.embedding_dimension)),
            pa.field("embedding_text", pa.string()),
            pa.field("model_name", pa.string()),
            pa.field("created_at", pa.timestamp('us'))
        ])

        # Check if table exists
        try:
            self.table = self.db.open_table(self.table_name)
        except Exception:
            # Table doesn't exist, create it with empty data
            empty_data = {
                "bookmark_id": [],
                "embedding": [],
                "embedding_text": [],
                "model_name": [],
                "created_at": []
            }

            empty_table = pa.table(empty_data, schema=schema)

            self.table = self.db.create_table(
                self.table_name,
                empty_table,
                mode="overwrite"
            )

    def add_embedding(
        self,
        bookmark_id: str,
        embedding: np.ndarray,
        text: str,
        model: str
    ) -> None:
        """
        Add or update an embedding for a bookmark.

        Args:
            bookmark_id: UUID of bookmark
            embedding: Embedding vector (numpy array)
            text: Text that was embedded
            model: Name of embedding model
        """
        # Validate embedding shape
        if embedding.shape[0] != self.embedding_dimension:
            raise ValueError(
                f"Embedding dimension {embedding.shape[0]} doesn't match "
                f"expected {self.embedding_dimension}"
            )

        # Ensure embedding is float32
        if embedding.dtype != np.float32:
            embedding = embedding.astype(np.float32)

        # Check if embedding already exists for this bookmark
        existing = self.get_embedding(bookmark_id)
        if existing:
            # Delete old embedding first
            self.delete_embedding(bookmark_id)

        data = [{
            "bookmark_id": bookmark_id,
            "embedding": embedding.tolist(),
            "embedding_text": text,
            "model_name": model,
            "created_at": datetime.utcnow()
        }]

        self.table.add(data)

    def get_embedding(self, bookmark_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve embedding for a bookmark.

        Args:
            bookmark_id: UUID of bookmark

        Returns:
            Dictionary with embedding data, or None if not found
        """
        try:
            # Query by bookmark_id
            results = (
                self.table.search()
                .where(f"bookmark_id = '{bookmark_id}'")
                .limit(1)
                .to_list()
            )

            if results:
                result = results[0]
                return {
                    "bookmark_id": result["bookmark_id"],
                    "embedding": np.array(result["embedding"], dtype=np.float32),
                    "embedding_text": result["embedding_text"],
                    "model_name": result["model_name"],
                    "created_at": result["created_at"]
                }

            return None

        except Exception:
            return None

    def search(
        self,
        query_embedding: np.ndarray,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings using vector similarity.

        Args:
            query_embedding: Query vector (numpy array)
            limit: Maximum number of results

        Returns:
            List of dictionaries with bookmark_id and similarity score
            Sorted by similarity (highest first)
        """
        # Validate query embedding
        if query_embedding.shape[0] != self.embedding_dimension:
            raise ValueError(
                f"Query embedding dimension {query_embedding.shape[0]} doesn't match "
                f"expected {self.embedding_dimension}"
            )

        # Ensure float32
        if query_embedding.dtype != np.float32:
            query_embedding = query_embedding.astype(np.float32)

        try:
            # Perform vector search
            results = (
                self.table.search(query_embedding.tolist())
                .limit(limit)
                .to_list()
            )

            # Format results
            formatted_results = []
            for result in results:
                # LanceDB returns distance; convert to similarity score [0, 1]
                # For cosine similarity with normalized vectors, distance = 1 - similarity
                # So similarity = 1 - distance
                distance = result.get("_distance", 0.0)
                similarity = max(0.0, min(1.0, 1.0 - distance))

                formatted_results.append({
                    "bookmark_id": result["bookmark_id"],
                    "score": similarity
                })

            return formatted_results

        except Exception as e:
            # Handle empty table or other errors
            print(f"Search error: {e}")
            return []

    def delete_embedding(self, bookmark_id: str) -> bool:
        """
        Delete embedding for a bookmark.

        Args:
            bookmark_id: UUID of bookmark

        Returns:
            True if deleted, False if not found
        """
        try:
            # Check if exists
            if not self.get_embedding(bookmark_id):
                return False

            self.table.delete(f"bookmark_id = '{bookmark_id}'")
            return True

        except Exception:
            return False

    def update_embedding(
        self,
        bookmark_id: str,
        embedding: np.ndarray,
        text: str
    ) -> None:
        """
        Update embedding for a bookmark.

        LanceDB doesn't support direct updates, so we delete and re-add.

        Args:
            bookmark_id: UUID of bookmark
            embedding: New embedding vector
            text: New text that was embedded
        """
        # Get existing to preserve model_name
        existing = self.get_embedding(bookmark_id)
        model_name = existing["model_name"] if existing else "unknown"

        self.delete_embedding(bookmark_id)
        self.add_embedding(bookmark_id, embedding, text, model_name)

    def count(self) -> int:
        """
        Get total number of embeddings.

        Returns:
            Count of embeddings in table
        """
        try:
            return self.table.count_rows()
        except Exception:
            return 0

    def close(self) -> None:
        """Close database connection."""
        # LanceDB connections are lightweight, no explicit close needed
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
