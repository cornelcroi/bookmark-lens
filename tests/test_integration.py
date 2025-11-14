"""
Integration tests for bookmark-lens (Core Mode - no LLM).

Tests the complete flow: save → search → stats with mocked URL fetching.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from bookmark_lens.config import Config
from bookmark_lens.database.duckdb_client import DuckDBClient
from bookmark_lens.database.lancedb_client import LanceDBClient
from bookmark_lens.services.content_fetcher import ContentFetcher
from bookmark_lens.services.embedding_service import EmbeddingService
from bookmark_lens.services.bookmark_service import BookmarkService
from bookmark_lens.services.search_service import SearchService
from bookmark_lens.models.bookmark import BookmarkCreate, BookmarkSearchQuery


# Mock content for different URLs
MOCK_CONTENT = {
    "https://github.com/anthropics/mcp": {
        "title": "Model Context Protocol",
        "description": "A protocol for connecting AI assistants to data sources",
        "content": "# Model Context Protocol\n\nMCP enables seamless integration between LLM applications and external data sources.",
        "domain": "github.com"
    },
    "https://aws.amazon.com/bedrock/": {
        "title": "Amazon Bedrock - AWS",
        "description": "Build and scale generative AI applications with foundation models",
        "content": "# Amazon Bedrock\n\nAmazon Bedrock is a fully managed service for building AI applications.",
        "domain": "aws.amazon.com"
    },
    "https://python.org/docs/tutorial": {
        "title": "Python Tutorial",
        "description": "Official Python programming tutorial",
        "content": "# Python Tutorial\n\nLearn Python programming from basics to advanced topics.",
        "domain": "python.org"
    },
    "https://github.com/pytorch/pytorch": {
        "title": "PyTorch Deep Learning Framework",
        "description": "Tensors and Dynamic neural networks in Python",
        "content": "# PyTorch\n\nPyTorch is an open source machine learning framework.",
        "domain": "github.com"
    },
    "https://docs.anthropic.com/claude/docs": {
        "title": "Claude API Documentation",
        "description": "Documentation for Claude AI API",
        "content": "# Claude API\n\nClaude is a next-generation AI assistant.",
        "domain": "docs.anthropic.com"
    }
}


class MockContentFetcher:
    """Mock content fetcher that returns predefined content."""
    
    def __init__(self, config):
        self.config = config
    
    def fetch(self, url, full_content=True):
        """Return mock content for known URLs."""
        from bookmark_lens.models.bookmark import ContentResult
        
        if url in MOCK_CONTENT:
            mock = MOCK_CONTENT[url]
            return ContentResult(
                url=url,
                normalized_url=url,
                domain=mock["domain"],
                title=mock["title"],
                description=mock["description"],
                content_text=mock["content"] if full_content else "",
                fetch_success=True
            )
        
        # Unknown URL
        return ContentResult(
            url=url,
            normalized_url=url,
            domain="example.com",
            title="Unknown Page",
            description="",
            content_text="",
            fetch_success=False,
            error_message="URL not in mock data"
        )


@pytest.fixture
def temp_dir():
    """Create temporary directory for test databases."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def config(temp_dir):
    """Create test configuration (Core Mode - no LLM)."""
    return Config(
        db_path=str(Path(temp_dir) / "test.db"),
        lance_path=str(Path(temp_dir) / "test.lance"),
        embedding_model_name="all-MiniLM-L6-v2",
        embedding_dimension=384,
        fetch_timeout=30,
        user_agent="test-agent",
        max_content_length=50000
    )


@pytest.fixture
def services(config):
    """Initialize all services with mocked content fetcher."""
    # Initialize databases
    duckdb = DuckDBClient(config.db_path)
    duckdb.initialize_schema()
    
    lancedb = LanceDBClient(config.lance_path, config.embedding_dimension)
    lancedb.initialize_table()
    
    # Initialize services with mock fetcher
    content_fetcher = MockContentFetcher(config)
    embedding_service = EmbeddingService(config)
    
    bookmark_service = BookmarkService(
        config,
        duckdb,
        lancedb,
        content_fetcher,
        embedding_service
    )
    
    search_service = SearchService(
        config,
        duckdb,
        lancedb,
        embedding_service
    )
    
    return {
        "duckdb": duckdb,
        "lancedb": lancedb,
        "bookmark": bookmark_service,
        "search": search_service
    }


class TestBookmarkSaveAndRetrieve:
    """Test saving and retrieving bookmarks."""
    
    def test_save_single_bookmark(self, services):
        """Test saving a single bookmark."""
        bookmark = services["bookmark"].save_bookmark(
            BookmarkCreate(
                url="https://github.com/anthropics/mcp",
                note="MCP protocol documentation",
                manual_tags=["mcp", "ai"],
                source="manual"
            )
        )
        
        assert bookmark.id is not None
        assert bookmark.url == "https://github.com/anthropics/mcp"
        assert bookmark.title == "Model Context Protocol"
        assert bookmark.description == "A protocol for connecting AI assistants to data sources"
        assert bookmark.domain == "github.com"
        assert "mcp" in bookmark.tags
        assert "ai" in bookmark.tags
        assert bookmark.user_note == "MCP protocol documentation"
    
    def test_save_multiple_bookmarks(self, services):
        """Test saving multiple bookmarks."""
        urls = [
            ("https://github.com/anthropics/mcp", ["mcp", "ai"], "MCP docs"),
            ("https://aws.amazon.com/bedrock/", ["aws", "ai"], "Bedrock service"),
            ("https://python.org/docs/tutorial", ["python", "tutorial"], "Python guide"),
        ]
        
        bookmarks = []
        for url, tags, note in urls:
            bm = services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags, note=note, source="manual")
            )
            bookmarks.append(bm)
        
        assert len(bookmarks) == 3
        assert all(bm.id is not None for bm in bookmarks)
        assert bookmarks[0].domain == "github.com"
        assert bookmarks[1].domain == "aws.amazon.com"
        assert bookmarks[2].domain == "python.org"
    
    def test_get_bookmark_by_id(self, services):
        """Test retrieving bookmark by ID."""
        saved = services["bookmark"].save_bookmark(
            BookmarkCreate(
                url="https://github.com/pytorch/pytorch",
                manual_tags=["ml", "pytorch"],
                note="Deep learning framework"
            )
        )
        
        retrieved = services["bookmark"].get_bookmark(saved.id)
        
        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.url == saved.url
        assert retrieved.title == "PyTorch Deep Learning Framework"
        assert retrieved.tags == saved.tags


class TestSemanticSearch:
    """Test semantic search functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_bookmarks(self, services):
        """Create test bookmarks before each test."""
        test_data = [
            ("https://github.com/anthropics/mcp", ["mcp", "ai"], "MCP protocol"),
            ("https://aws.amazon.com/bedrock/", ["aws", "ai"], "AWS AI service"),
            ("https://python.org/docs/tutorial", ["python", "tutorial"], "Learn Python"),
            ("https://github.com/pytorch/pytorch", ["ml", "pytorch"], "ML framework"),
            ("https://docs.anthropic.com/claude/docs", ["ai", "claude"], "Claude API"),
        ]
        
        for url, tags, note in test_data:
            services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags, note=note, source="manual")
            )
    
    def test_search_by_topic(self, services):
        """Test searching by topic/keyword."""
        results = services["search"].search(
            BookmarkSearchQuery(query="AI assistant protocol", limit=10)
        )
        
        assert len(results) > 0
        # MCP should be highly relevant
        assert any("mcp" in r.url.lower() for r in results[:2])
    
    def test_search_with_domain_filter(self, services):
        """Test searching with domain filter."""
        results = services["search"].search(
            BookmarkSearchQuery(query="AI", domain="github.com", limit=10)
        )
        
        assert len(results) > 0
        assert all(r.url.startswith("https://github.com") for r in results)
    
    def test_search_with_tag_filter(self, services):
        """Test searching with tag filter."""
        results = services["search"].search(
            BookmarkSearchQuery(query="programming", tags=["python"], limit=10)
        )
        
        assert len(results) > 0
        assert all("python" in r.tags for r in results)
    
    def test_search_machine_learning(self, services):
        """Test searching for machine learning content."""
        results = services["search"].search(
            BookmarkSearchQuery(query="machine learning framework", limit=10)
        )
        
        assert len(results) > 0
        # PyTorch should be highly relevant
        assert any("pytorch" in r.url.lower() for r in results[:2])
    
    def test_search_no_results(self, services):
        """Test search with no matching results."""
        results = services["search"].search(
            BookmarkSearchQuery(query="quantum computing blockchain", limit=10)
        )
        
        # Should return something (semantic search is fuzzy) but with low scores
        assert all(r.similarity_score < 0.5 for r in results)


class TestBookmarkStats:
    """Test bookmark statistics."""
    
    @pytest.fixture(autouse=True)
    def setup_bookmarks(self, services):
        """Create test bookmarks with varied dates."""
        now = datetime.now()
        test_data = [
            ("https://github.com/anthropics/mcp", ["mcp", "ai"], now),
            ("https://aws.amazon.com/bedrock/", ["aws", "ai"], now - timedelta(days=2)),
            ("https://python.org/docs/tutorial", ["python"], now - timedelta(days=5)),
            ("https://github.com/pytorch/pytorch", ["ml", "pytorch"], now - timedelta(days=8)),
            ("https://docs.anthropic.com/claude/docs", ["ai", "claude"], now - timedelta(days=10)),
        ]
        
        for url, tags, created_at in test_data:
            bm = services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags, source="manual")
            )
            # Update created_at to simulate different save times
            services["duckdb"].conn.execute(
                "UPDATE bookmarks SET created_at = ? WHERE id = ?",
                [created_at, bm.id]
            )
            services["duckdb"].conn.commit()
    
    def test_total_count(self, services):
        """Test getting total bookmark count."""
        result = services["duckdb"].conn.execute(
            "SELECT COUNT(*) FROM bookmarks"
        ).fetchone()
        
        assert result[0] == 5
    
    def test_count_by_domain(self, services):
        """Test counting bookmarks by domain."""
        results = services["duckdb"].conn.execute("""
            SELECT domain, COUNT(*) as count
            FROM bookmarks
            GROUP BY domain
            ORDER BY count DESC
        """).fetchall()
        
        assert len(results) >= 2
        # GitHub should have 2 bookmarks
        github_count = next((count for domain, count in results if domain == "github.com"), 0)
        assert github_count == 2
    
    def test_count_by_tag(self, services):
        """Test counting bookmarks by tag."""
        results = services["duckdb"].conn.execute("""
            SELECT tag, COUNT(*) as count
            FROM bookmark_tags
            GROUP BY tag
            ORDER BY count DESC
        """).fetchall()
        
        assert len(results) > 0
        # AI tag should appear multiple times
        ai_count = next((count for tag, count in results if tag == "ai"), 0)
        assert ai_count >= 3
    
    def test_count_recent_bookmarks(self, services):
        """Test counting bookmarks from last week."""
        week_ago = datetime.now() - timedelta(days=7)
        result = services["duckdb"].conn.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE created_at >= ?",
            [week_ago]
        ).fetchone()
        
        # Should have 3 bookmarks from last week
        assert result[0] == 3
    
    def test_count_with_filters(self, services):
        """Test counting with domain and tag filters."""
        result = services["duckdb"].conn.execute("""
            SELECT COUNT(DISTINCT b.id)
            FROM bookmarks b
            JOIN bookmark_tags bt ON b.id = bt.bookmark_id
            WHERE b.domain = ? AND bt.tag = ?
        """, ["github.com", "ai"]).fetchone()
        
        assert result[0] == 1  # Only MCP bookmark


class TestBookmarkUpdate:
    """Test updating bookmarks."""
    
    def test_update_note(self, services):
        """Test updating bookmark note."""
        from bookmark_lens.models.bookmark import BookmarkUpdate
        
        # Save bookmark
        saved = services["bookmark"].save_bookmark(
            BookmarkCreate(url="https://github.com/anthropics/mcp", note="Original note")
        )
        
        # Update note
        updated = services["bookmark"].update_bookmark(
            saved.id,
            BookmarkUpdate(note="Updated note")
        )
        
        assert updated.user_note == "Updated note"
    
    def test_update_tags_replace(self, services):
        """Test replacing tags."""
        from bookmark_lens.models.bookmark import BookmarkUpdate
        
        saved = services["bookmark"].save_bookmark(
            BookmarkCreate(url="https://github.com/anthropics/mcp", manual_tags=["old", "tags"])
        )
        
        updated = services["bookmark"].update_bookmark(
            saved.id,
            BookmarkUpdate(manual_tags=["new", "tags"], tag_mode="replace")
        )
        
        assert "new" in updated.tags
        assert "tags" in updated.tags
        assert "old" not in updated.tags
    
    def test_update_tags_append(self, services):
        """Test appending tags."""
        from bookmark_lens.models.bookmark import BookmarkUpdate
        
        saved = services["bookmark"].save_bookmark(
            BookmarkCreate(url="https://github.com/anthropics/mcp", manual_tags=["existing"])
        )
        
        updated = services["bookmark"].update_bookmark(
            saved.id,
            BookmarkUpdate(manual_tags=["new"], tag_mode="append")
        )
        
        assert "existing" in updated.tags
        assert "new" in updated.tags


class TestBookmarkDelete:
    """Test deleting bookmarks."""
    
    def test_delete_bookmark(self, services):
        """Test deleting a bookmark."""
        saved = services["bookmark"].save_bookmark(
            BookmarkCreate(url="https://github.com/anthropics/mcp", manual_tags=["test"])
        )
        
        # Delete
        deleted = services["bookmark"].delete_bookmark(saved.id)
        assert deleted is True
        
        # Verify it's gone
        retrieved = services["bookmark"].get_bookmark(saved.id)
        assert retrieved is None
    
    def test_delete_nonexistent(self, services):
        """Test deleting non-existent bookmark."""
        deleted = services["bookmark"].delete_bookmark("nonexistent_id")
        assert deleted is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
