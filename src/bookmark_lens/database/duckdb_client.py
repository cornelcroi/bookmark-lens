"""
DuckDB client for storing bookmark metadata, tags, and relational data.

This is the source of truth for all bookmark information.
"""

import duckdb
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class DuckDBClient:
    """Client for managing DuckDB database operations."""

    def __init__(self, db_path: str):
        """
        Initialize DuckDB client.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path

        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = duckdb.connect(db_path)

    def initialize_schema(self) -> None:
        """
        Create database schema if it doesn't exist.

        Creates:
            - bookmarks table (main bookmark data)
            - bookmark_tags table (tags for bookmarks)
            - Indexes for common queries
        """
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                domain TEXT NOT NULL,
                title TEXT,
                description TEXT,
                content_text TEXT,
                user_note TEXT,
                summary_short TEXT,
                summary_long TEXT,
                topic TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                source TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookmarks_url
            ON bookmarks(url)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookmarks_domain
            ON bookmarks(domain)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at
            ON bookmarks(created_at)
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmark_tags (
                id TEXT PRIMARY KEY,
                bookmark_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_bookmark_id
            ON bookmark_tags(bookmark_id)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_tag
            ON bookmark_tags(tag)
        """)

        # Commit the changes
        self.conn.commit()

    def insert_bookmark(self, bookmark_data: Dict[str, Any]) -> str:
        """
        Insert a new bookmark.

        Args:
            bookmark_data: Dictionary with bookmark fields:
                - id: UUID string
                - url: Normalized URL
                - domain: Extracted domain
                - title, description, content_text: Page content
                - user_note: User's context
                - summary_short, summary_long, topic: LLM-generated (optional)
                - created_at, updated_at: Timestamps
                - source: Origin of bookmark

        Returns:
            Bookmark ID

        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required_fields = ['id', 'url', 'domain', 'created_at', 'updated_at', 'source']
        for field in required_fields:
            if field not in bookmark_data:
                raise ValueError(f"Missing required field: {field}")

        self.conn.execute("""
            INSERT INTO bookmarks (
                id, url, domain, title, description, content_text,
                user_note, summary_short, summary_long, topic,
                created_at, updated_at, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            bookmark_data['id'],
            bookmark_data['url'],
            bookmark_data['domain'],
            bookmark_data.get('title'),
            bookmark_data.get('description'),
            bookmark_data.get('content_text'),
            bookmark_data.get('user_note'),
            bookmark_data.get('summary_short'),
            bookmark_data.get('summary_long'),
            bookmark_data.get('topic'),
            bookmark_data['created_at'],
            bookmark_data['updated_at'],
            bookmark_data['source']
        ])

        self.conn.commit()
        return bookmark_data['id']

    def get_bookmark(self, bookmark_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a bookmark by ID.

        Args:
            bookmark_id: Bookmark UUID

        Returns:
            Dictionary with bookmark data, or None if not found
        """
        result = self.conn.execute("""
            SELECT
                id, url, domain, title, description, content_text,
                user_note, summary_short, summary_long, topic,
                created_at, updated_at, source
            FROM bookmarks
            WHERE id = ?
        """, [bookmark_id]).fetchone()

        if not result:
            return None

        # Convert to dictionary
        columns = [
            'id', 'url', 'domain', 'title', 'description', 'content_text',
            'user_note', 'summary_short', 'summary_long', 'topic',
            'created_at', 'updated_at', 'source'
        ]
        return dict(zip(columns, result))

    def update_bookmark(self, bookmark_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update bookmark fields.

        Args:
            bookmark_id: Bookmark UUID
            updates: Dictionary of fields to update
                Must include 'updated_at' timestamp

        Returns:
            True if updated, False if bookmark not found
        """
        if not updates:
            return False

        # Build SET clause dynamically
        set_clauses = []
        values = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)

        values.append(bookmark_id)

        sql = f"""
            UPDATE bookmarks
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """

        result = self.conn.execute(sql, values)
        self.conn.commit()

        return result.fetchone() is not None

    def delete_bookmark(self, bookmark_id: str) -> bool:
        """
        Delete a bookmark and its associated tags.

        Args:
            bookmark_id: Bookmark UUID

        Returns:
            True if deleted, False if not found
        """
        # Check if exists
        if not self.get_bookmark(bookmark_id):
            return False

        # Delete tags first (DuckDB doesn't support CASCADE)
        self.conn.execute("""
            DELETE FROM bookmark_tags WHERE bookmark_id = ?
        """, [bookmark_id])

        self.conn.execute("""
            DELETE FROM bookmarks WHERE id = ?
        """, [bookmark_id])

        self.conn.commit()
        return True

    def bookmark_exists(self, url: str) -> Optional[str]:
        """
        Check if a bookmark with this URL already exists.

        Args:
            url: URL to check

        Returns:
            Bookmark ID if exists, None otherwise
        """
        result = self.conn.execute("""
            SELECT id FROM bookmarks WHERE url = ?
        """, [url]).fetchone()

        return result[0] if result else None

    def add_tags(
        self,
        bookmark_id: str,
        tags: List[str],
        source: str = "manual"
    ) -> None:
        """
        Add tags to a bookmark.

        Args:
            bookmark_id: Bookmark UUID
            tags: List of tag strings (will be normalized)
            source: 'manual' or 'auto'
        """
        for tag in tags:
            # Normalize tag: lowercase, strip whitespace
            normalized_tag = tag.lower().strip()

            if not normalized_tag:
                continue

            # Generate tag ID
            tag_id = str(uuid.uuid4())

            self.conn.execute("""
                INSERT INTO bookmark_tags (id, bookmark_id, tag, source)
                VALUES (?, ?, ?, ?)
            """, [tag_id, bookmark_id, normalized_tag, source])

        self.conn.commit()

    def get_tags(self, bookmark_id: str) -> List[Dict[str, Any]]:
        """
        Get all tags for a bookmark.

        Args:
            bookmark_id: Bookmark UUID

        Returns:
            List of tag dictionaries with fields: id, tag, source
        """
        results = self.conn.execute("""
            SELECT id, tag, source
            FROM bookmark_tags
            WHERE bookmark_id = ?
        """, [bookmark_id]).fetchall()

        return [
            {'id': r[0], 'tag': r[1], 'source': r[2]}
            for r in results
        ]

    def delete_tags(
        self,
        bookmark_id: str,
        source: Optional[str] = None
    ) -> None:
        """
        Delete tags for a bookmark.

        Args:
            bookmark_id: Bookmark UUID
            source: If specified, only delete tags with this source
                    (e.g., 'manual' or 'auto')
        """
        if source:
            self.conn.execute("""
                DELETE FROM bookmark_tags
                WHERE bookmark_id = ? AND source = ?
            """, [bookmark_id, source])
        else:
            self.conn.execute("""
                DELETE FROM bookmark_tags
                WHERE bookmark_id = ?
            """, [bookmark_id])

        self.conn.commit()

    def execute(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute arbitrary SQL query.

        Args:
            sql: SQL query string
            params: Optional query parameters

        Returns:
            Query result
        """
        if params:
            return self.conn.execute(sql, params).fetchall()
        else:
            return self.conn.execute(sql).fetchall()

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()
