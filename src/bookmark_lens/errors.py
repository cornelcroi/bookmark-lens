"""Custom exceptions for bookmark-lens."""


class BookmarkLensError(Exception):
    """Base exception for all bookmark-lens errors."""
    pass


class BookmarkNotFoundError(BookmarkLensError):
    """Raised when a bookmark ID doesn't exist."""
    pass


class BookmarkAlreadyExistsError(BookmarkLensError):
    """Raised when attempting to save a duplicate bookmark."""
    pass


class ContentFetchError(BookmarkLensError):
    """Raised when fetching URL content fails."""
    pass


class EmbeddingError(BookmarkLensError):
    """Raised when embedding generation fails."""
    pass


class SearchError(BookmarkLensError):
    """Raised when search operation fails."""
    pass


class DatabaseError(BookmarkLensError):
    """Raised when database operations fail."""
    pass


class LLMError(BookmarkLensError):
    """Raised when LLM API calls fail."""
    pass


class ConfigurationError(BookmarkLensError):
    """Raised when configuration is invalid."""
    pass


class ValidationError(BookmarkLensError):
    """Raised when input validation fails."""
    pass
