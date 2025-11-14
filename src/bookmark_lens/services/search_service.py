"""
Search service combining vector similarity and SQL filtering.

Implements hybrid search: semantic search + structured filters.
"""

import logging
from typing import List

from ..config import Config
from ..database.duckdb_client import DuckDBClient
from ..database.lancedb_client import LanceDBClient
from ..models.bookmark import BookmarkSearchQuery, BookmarkSearchResult
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SearchService:
    """Hybrid search service for bookmarks."""

    def __init__(
        self,
        config: Config,
        duckdb_client: DuckDBClient,
        lancedb_client: LanceDBClient,
        embedding_service: EmbeddingService
    ):
        self.config = config
        self.duckdb = duckdb_client
        self.lancedb = lancedb_client
        self.embedding_service = embedding_service

    def search(self, query: BookmarkSearchQuery) -> List[BookmarkSearchResult]:
        """
        Search bookmarks using hybrid approach.

        Steps:
        1. Generate query embedding
        2. Vector search in LanceDB (over-fetch for filtering)
        3. Apply SQL filters in DuckDB
        4. Sort by similarity score
        5. Apply final limit

        Args:
            query: Search query with filters

        Returns:
            List of matching bookmarks with scores
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query.query)

        # Vector search (over-fetch to allow filtering)
        vector_limit = query.limit * 5
        vector_results = self.lancedb.search(
            query_embedding=query_embedding,
            limit=vector_limit
        )

        if not vector_results:
            logger.info(f"No results found for query: {query.query}")
            return []

        # Extract bookmark IDs and scores
        bookmark_ids = [r["bookmark_id"] for r in vector_results]
        scores_map = {r["bookmark_id"]: r["score"] for r in vector_results}

        # Build SQL query with filters
        placeholders = ",".join(["?"] * len(bookmark_ids))
        sql = f"""
            SELECT
                b.id, b.url, b.title, b.description,
                b.summary_short, b.topic, b.created_at,
                GROUP_CONCAT(bt.tag, ',') as tags
            FROM bookmarks b
            LEFT JOIN bookmark_tags bt ON b.id = bt.bookmark_id
            WHERE b.id IN ({placeholders})
        """
        params = bookmark_ids.copy()

        # Add filters
        if query.domain:
            sql += " AND b.domain = ?"
            params.append(query.domain)

        if query.topic:
            sql += " AND b.topic = ?"
            params.append(query.topic)

        if query.from_date:
            sql += " AND b.created_at >= ?"
            params.append(query.from_date)

        if query.to_date:
            sql += " AND b.created_at <= ?"
            params.append(query.to_date)

        sql += " GROUP BY b.id, b.url, b.title, b.description, b.summary_short, b.topic, b.created_at"

        # Execute query
        raw_results = self.duckdb.execute(sql, params)
        
        # Convert tuples to dicts
        columns = ["id", "url", "title", "description", "summary_short", "topic", "created_at", "tags"]
        results = [dict(zip(columns, row)) for row in raw_results]

        # Filter by tags if specified
        if query.tags:
            filtered_results = []
            for row in results:
                if row["tags"]:
                    row_tags = row["tags"].split(",")
                    if any(tag in row_tags for tag in query.tags):
                        filtered_results.append(row)
            results = filtered_results

        # Build response objects with scores
        search_results = []
        for row in results:
            bookmark_id = row["id"]
            tags = row["tags"].split(",") if row["tags"] else []

            search_results.append(
                BookmarkSearchResult(
                    id=bookmark_id,
                    url=row["url"],
                    title=row["title"],
                    description=row["description"],
                    summary_short=row["summary_short"],
                    tags=tags,
                    topic=row["topic"],
                    created_at=row["created_at"],
                    similarity_score=scores_map[bookmark_id]
                )
            )

        # Sort by similarity score (descending)
        search_results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Apply final limit
        return search_results[:query.limit]
