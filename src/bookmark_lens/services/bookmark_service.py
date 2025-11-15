"""
Bookmark service for orchestrating bookmark operations.

Combines content fetching, embedding generation, and database storage.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from ..config import Config
from ..database.duckdb_client import DuckDBClient
from ..database.lancedb_client import LanceDBClient
from ..models.bookmark import BookmarkCreate, Bookmark, BookmarkUpdate
from .content_fetcher import ContentFetcher
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class BookmarkService:
    """High-level service for bookmark operations."""

    def __init__(
        self,
        config: Config,
        duckdb_client: DuckDBClient,
        lancedb_client: LanceDBClient,
        content_fetcher: ContentFetcher,
        embedding_service: EmbeddingService
    ):
        self.config = config
        self.duckdb = duckdb_client
        self.lancedb = lancedb_client
        self.content_fetcher = content_fetcher
        self.embedding_service = embedding_service

    def save_bookmark(self, bookmark_create: BookmarkCreate) -> Bookmark:
        """
        Save a new bookmark with full pipeline.

        Steps:
        1. Check if URL already exists
        2. Fetch content
        3. Generate embedding
        4. Store in both databases

        Args:
            bookmark_create: Bookmark creation data

        Returns:
            Complete Bookmark object
        """
        url = str(bookmark_create.url)

        # Check if already exists
        existing_id = self.duckdb.bookmark_exists(url)
        if existing_id:
            logger.info(f"Bookmark already exists: {existing_id}, updating...")
            update = BookmarkUpdate(
                note=bookmark_create.note,
                manual_tags=bookmark_create.manual_tags,
                tag_mode="append"
            )
            return self.update_bookmark(existing_id, update)

        logger.info(f"Fetching content: {url}")
        content_result = self.content_fetcher.fetch(url, full_content=True)

        bookmark_data_summary_short = None
        bookmark_data_summary_long = None
        bookmark_data_topic = None

        embedding_text = self.embedding_service.build_embedding_text(
            title=content_result.title,
            description=content_result.description,
            content_text=content_result.content_text,
            user_note=bookmark_create.note,
            summary=bookmark_data_summary_short,
            tags=bookmark_create.manual_tags if bookmark_create.manual_tags else None,
            topic=bookmark_data_topic
        )

        embedding = self.embedding_service.generate_embedding(embedding_text)

        bookmark_id = str(uuid.uuid4())
        now = datetime.utcnow()

        bookmark_data = {
            "id": bookmark_id,
            "url": content_result.normalized_url,
            "domain": content_result.domain,
            "title": content_result.title,
            "description": content_result.description,
            "content_text": content_result.content_text,
            "user_note": bookmark_create.note,
            "summary_short": bookmark_data_summary_short,
            "summary_long": bookmark_data_summary_long,
            "topic": bookmark_data_topic,
            "created_at": now,
            "updated_at": now,
            "source": bookmark_create.source
        }

        try:
            # Store in DuckDB
            self.duckdb.insert_bookmark(bookmark_data)
            logger.info(f"Bookmark saved to DuckDB: {bookmark_id}")

            # Store tags
            if bookmark_create.manual_tags:
                self.duckdb.add_tags(
                    bookmark_id,
                    bookmark_create.manual_tags,
                    source="manual"
                )
            
            # Store embedding in LanceDB
            self.lancedb.add_embedding(
                bookmark_id=bookmark_id,
                embedding=embedding,
                text=embedding_text,
                model=self.embedding_service.model_name
            )
            logger.info(f"Embedding saved to LanceDB: {bookmark_id}")

            return self._build_bookmark_response(bookmark_id)

        except Exception as e:
            # Rollback: delete from DuckDB if LanceDB failed
            logger.error(f"Failed to save bookmark: {e}")
            try:
                self.duckdb.delete_bookmark(bookmark_id)
            except:
                pass
            raise

    def get_bookmark(self, bookmark_id: str) -> Optional[Bookmark]:
        """
        Get bookmark by ID.

        Args:
            bookmark_id: Bookmark ID

        Returns:
            Bookmark object or None if not found
        """
        bookmark_data = self.duckdb.get_bookmark(bookmark_id)
        if not bookmark_data:
            return None

        tags_data = self.duckdb.get_tags(bookmark_id)
        tags = [t["tag"] for t in tags_data]

        return Bookmark.from_db_row(bookmark_data, tags=tags)

    def update_bookmark(
        self,
        bookmark_id: str,
        update: BookmarkUpdate
    ) -> Bookmark:
        """
        Update bookmark note and/or tags.

        If note changes, regenerates embedding.

        Args:
            bookmark_id: Bookmark ID
            update: Update data

        Returns:
            Updated Bookmark object

        Raises:
            ValueError: If bookmark not found
        """
        existing = self.duckdb.get_bookmark(bookmark_id)
        if not existing:
            raise ValueError(f"Bookmark {bookmark_id} not found")

        # Update note if provided
        if update.note is not None:
            self.duckdb.update_bookmark(
                bookmark_id,
                {"user_note": update.note, "updated_at": datetime.utcnow()}
            )

            # Regenerate embedding with new note
            embedding_text = self.embedding_service.build_embedding_text(
                title=existing["title"],
                description=existing["description"],
                content_text=existing["content_text"],
                user_note=update.note
            )
            embedding = self.embedding_service.generate_embedding(embedding_text)

            self.lancedb.update_embedding(
                bookmark_id=bookmark_id,
                embedding=embedding,
                text=embedding_text
            )
            logger.info(f"Re-embedded bookmark {bookmark_id} with new note")

        # Update tags if provided
        if update.manual_tags is not None:
            if update.tag_mode == "replace":
                # Delete existing manual tags
                self.duckdb.delete_tags(bookmark_id, source="manual")

            self.duckdb.add_tags(
                bookmark_id,
                update.manual_tags,
                source="manual"
            )
            logger.info(f"Updated tags for bookmark {bookmark_id}")

        return self._build_bookmark_response(bookmark_id)

    def delete_bookmark(self, bookmark_id: str) -> bool:
        """
        Delete bookmark from both databases.

        Args:
            bookmark_id: Bookmark ID

        Returns:
            True if deleted, False if not found
        """
        # Delete from DuckDB (cascades to tags)
        deleted = self.duckdb.delete_bookmark(bookmark_id)
        if not deleted:
            return False

        self.lancedb.delete_embedding(bookmark_id)

        logger.info(f"Deleted bookmark: {bookmark_id}")
        return True

    def _build_bookmark_response(self, bookmark_id: str) -> Bookmark:
        """
        Build complete Bookmark response with tags.

        Args:
            bookmark_id: Bookmark ID

        Returns:
            Complete Bookmark object

        Raises:
            ValueError: If bookmark not found
        """
        bookmark_data = self.duckdb.get_bookmark(bookmark_id)
        if not bookmark_data:
            raise ValueError(f"Bookmark {bookmark_id} not found")

        tags_data = self.duckdb.get_tags(bookmark_id)
        tags = [t["tag"] for t in tags_data]

        return Bookmark.from_db_row(bookmark_data, tags=tags)
