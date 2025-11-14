"""
Pydantic data models for type-safe bookmark operations.

Provides validation, serialization, and type hints for all bookmark-related data.
"""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, HttpUrl, Field, field_validator


class BookmarkCreate(BaseModel):
    """Input model for creating a new bookmark."""

    url: HttpUrl
    note: Optional[str] = None
    manual_tags: List[str] = Field(default_factory=list)
    source: str = "manual"

    @field_validator('manual_tags')
    @classmethod
    def normalize_tags(cls, tags: List[str]) -> List[str]:
        """Normalize tags to lowercase and strip whitespace."""
        return [tag.lower().strip() for tag in tags if tag.strip()]

    @field_validator('note')
    @classmethod
    def validate_note(cls, note: Optional[str]) -> Optional[str]:
        """Validate and normalize note."""
        if note:
            note = note.strip()
            return note if note else None
        return None


class Bookmark(BaseModel):
    """Full bookmark representation with all fields."""

    id: str
    url: str
    domain: str
    title: Optional[str] = None
    description: Optional[str] = None
    content_text: Optional[str] = None
    user_note: Optional[str] = None
    summary_short: Optional[str] = None
    summary_long: Optional[str] = None
    topic: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    source: str

    @classmethod
    def from_db_row(
        cls,
        row: dict,
        tags: Optional[List[str]] = None
    ) -> "Bookmark":
        """
        Create Bookmark instance from database row.

        Args:
            row: Dictionary from DuckDB query
            tags: Optional list of tag strings

        Returns:
            Bookmark instance
        """
        return cls(
            id=row['id'],
            url=row['url'],
            domain=row['domain'],
            title=row.get('title'),
            description=row.get('description'),
            content_text=row.get('content_text'),
            user_note=row.get('user_note'),
            summary_short=row.get('summary_short'),
            summary_long=row.get('summary_long'),
            topic=row.get('topic'),
            tags=tags or [],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            source=row['source']
        )


class BookmarkSearchQuery(BaseModel):
    """Input model for searching bookmarks."""

    query: str = Field(..., min_length=1, description="Search query text")
    domain: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    topic: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = Field(default=10, ge=1, le=100, description="Max results (1-100)")

    @field_validator('tags')
    @classmethod
    def normalize_tags(cls, tags: List[str]) -> List[str]:
        """Normalize tags to lowercase."""
        return [tag.lower().strip() for tag in tags if tag.strip()]

    @field_validator('query')
    @classmethod
    def validate_query(cls, query: str) -> str:
        """Validate and normalize query."""
        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty")
        return query

    @field_validator('domain')
    @classmethod
    def normalize_domain(cls, domain: Optional[str]) -> Optional[str]:
        """Normalize domain to lowercase."""
        if domain:
            return domain.lower().strip()
        return None


class BookmarkSearchResult(BaseModel):
    """Output model for search results."""

    id: str
    url: str
    title: Optional[str]
    description: Optional[str]
    summary_short: Optional[str]
    tags: List[str]
    topic: Optional[str]
    created_at: datetime
    similarity_score: float = Field(..., ge=0.0, le=1.0)

    @classmethod
    def from_db_row(
        cls,
        row: dict,
        score: float,
        tags: Optional[List[str]] = None
    ) -> "BookmarkSearchResult":
        """
        Create BookmarkSearchResult from database row and similarity score.

        Args:
            row: Dictionary from DuckDB query
            score: Similarity score [0, 1]
            tags: Optional list of tags

        Returns:
            BookmarkSearchResult instance
        """
        # Handle tags - could be a comma-separated string or list
        if tags is None and 'tags' in row and row['tags']:
            if isinstance(row['tags'], str):
                tags = row['tags'].split(',')
            else:
                tags = row['tags']

        return cls(
            id=row['id'],
            url=row['url'],
            title=row.get('title'),
            description=row.get('description'),
            summary_short=row.get('summary_short'),
            tags=tags or [],
            topic=row.get('topic'),
            created_at=row['created_at'],
            similarity_score=score
        )


class BookmarkUpdate(BaseModel):
    """Input model for updating an existing bookmark."""

    note: Optional[str] = None
    manual_tags: Optional[List[str]] = None
    tag_mode: Literal["replace", "append"] = "replace"

    @field_validator('manual_tags')
    @classmethod
    def normalize_tags(cls, tags: Optional[List[str]]) -> Optional[List[str]]:
        """Normalize tags to lowercase and strip whitespace."""
        if tags is not None:
            return [tag.lower().strip() for tag in tags if tag.strip()]
        return None

    @field_validator('note')
    @classmethod
    def validate_note(cls, note: Optional[str]) -> Optional[str]:
        """Validate and normalize note."""
        if note is not None:
            note = note.strip()
            return note if note else None
        return None


class ContentResult(BaseModel):
    """Result from fetching and parsing web content."""

    url: str
    normalized_url: str
    domain: str
    title: Optional[str] = None
    description: Optional[str] = None
    content_text: str = ""
    fetch_success: bool
    error_message: Optional[str] = None

    model_config = {"frozen": False}  # Allow mutation during content extraction
