#!/usr/bin/env python3
"""
Simple integration tests without pytest dependency.
Tests Core Mode (no LLM) with mocked URL fetching.
"""

import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from bookmark_lens.config import Config
from bookmark_lens.database.duckdb_client import DuckDBClient
from bookmark_lens.database.lancedb_client import LanceDBClient
from bookmark_lens.services.embedding_service import EmbeddingService
from bookmark_lens.services.bookmark_service import BookmarkService
from bookmark_lens.services.search_service import SearchService
from bookmark_lens.models.bookmark import BookmarkCreate, BookmarkSearchQuery, ContentResult


# Mock content for URLs
MOCK_CONTENT = {
    "https://github.com/anthropics/mcp": {
        "title": "Model Context Protocol",
        "description": "A protocol for connecting AI assistants to data sources",
        "content": "MCP enables seamless integration between LLM applications and external data sources.",
        "domain": "github.com"
    },
    "https://aws.amazon.com/bedrock/": {
        "title": "Amazon Bedrock - AWS",
        "description": "Build and scale generative AI applications",
        "content": "Amazon Bedrock is a fully managed service for building AI applications with foundation models.",
        "domain": "aws.amazon.com"
    },
    "https://python.org/docs/tutorial": {
        "title": "Python Tutorial",
        "description": "Official Python programming tutorial",
        "content": "Learn Python programming from basics to advanced topics with examples and exercises.",
        "domain": "python.org"
    },
    "https://github.com/pytorch/pytorch": {
        "title": "PyTorch Deep Learning Framework",
        "description": "Tensors and Dynamic neural networks",
        "content": "PyTorch is an open source machine learning framework for deep learning applications.",
        "domain": "github.com"
    },
}


class MockContentFetcher:
    """Mock content fetcher."""
    
    def __init__(self, config):
        self.config = config
    
    def fetch(self, url, full_content=True):
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
        
        return ContentResult(
            url=url,
            normalized_url=url,
            domain="example.com",
            title="Unknown",
            description="",
            content_text="",
            fetch_success=False
        )


def setup_services():
    """Setup test services with temp databases."""
    temp_dir = tempfile.mkdtemp()
    
    config = Config(
        db_path=str(Path(temp_dir) / "test.db"),
        lance_path=str(Path(temp_dir) / "test.lance"),
        embedding_model_name="all-MiniLM-L6-v2",
        embedding_dimension=384,
        fetch_timeout=30,
        user_agent="test",
        max_content_length=50000
    )
    
    duckdb = DuckDBClient(config.db_path)
    duckdb.initialize_schema()
    
    lancedb = LanceDBClient(config.lance_path, config.embedding_dimension)
    lancedb.initialize_table()
    
    content_fetcher = MockContentFetcher(config)
    embedding_service = EmbeddingService(config)
    
    bookmark_service = BookmarkService(
        config, duckdb, lancedb, content_fetcher, embedding_service
    )
    
    search_service = SearchService(config, duckdb, lancedb, embedding_service)
    
    return {
        "temp_dir": temp_dir,
        "duckdb": duckdb,
        "bookmark": bookmark_service,
        "search": search_service
    }


def cleanup(services):
    """Cleanup temp directory."""
    shutil.rmtree(services["temp_dir"])


def test_save_bookmarks():
    """Test 1: Save multiple bookmarks."""
    print("\n=== Test 1: Save Bookmarks ===")
    services = setup_services()
    
    try:
        urls = [
            ("https://github.com/anthropics/mcp", ["mcp", "ai"], "MCP docs"),
            ("https://aws.amazon.com/bedrock/", ["aws", "ai"], "Bedrock"),
            ("https://python.org/docs/tutorial", ["python"], "Python guide"),
            ("https://github.com/pytorch/pytorch", ["ml", "pytorch"], "PyTorch"),
        ]
        
        saved = []
        for url, tags, note in urls:
            bm = services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags, note=note, source="manual")
            )
            saved.append(bm)
            print(f"✓ Saved: {bm.title} ({bm.domain})")
        
        assert len(saved) == 4
        assert saved[0].title == "Model Context Protocol"
        assert "mcp" in saved[0].tags
        print(f"✓ All {len(saved)} bookmarks saved successfully")
        
    finally:
        cleanup(services)


def test_search_semantic():
    """Test 2: Semantic search."""
    print("\n=== Test 2: Semantic Search ===")
    services = setup_services()
    
    try:
        # Save bookmarks
        for url, tags, note in [
            ("https://github.com/anthropics/mcp", ["mcp", "ai"], "MCP"),
            ("https://aws.amazon.com/bedrock/", ["aws", "ai"], "Bedrock"),
            ("https://python.org/docs/tutorial", ["python"], "Python"),
            ("https://github.com/pytorch/pytorch", ["ml"], "PyTorch"),
        ]:
            services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags, note=note)
            )
        
        # Search for AI-related content
        results = services["search"].search(
            BookmarkSearchQuery(query="AI assistant protocol", limit=5)
        )
        
        print(f"Query: 'AI assistant protocol'")
        print(f"Found {len(results)} results:")
        for r in results[:3]:
            print(f"  - {r.title} (score: {r.similarity_score:.3f})")
        
        assert len(results) > 0
        assert results[0].similarity_score > 0.2
        print("✓ Semantic search working")
        
    finally:
        cleanup(services)


def test_search_with_filters():
    """Test 3: Search with domain filter."""
    print("\n=== Test 3: Search with Filters ===")
    services = setup_services()
    
    try:
        # Save bookmarks
        for url, tags in [
            ("https://github.com/anthropics/mcp", ["ai"]),
            ("https://github.com/pytorch/pytorch", ["ml"]),
            ("https://aws.amazon.com/bedrock/", ["ai"]),
        ]:
            services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags)
            )
        
        # Search GitHub only
        results = services["search"].search(
            BookmarkSearchQuery(query="AI", domain="github.com", limit=5)
        )
        
        print(f"Query: 'AI' on github.com")
        print(f"Found {len(results)} results:")
        for r in results:
            print(f"  - {r.title} ({r.url})")
        
        assert len(results) > 0
        assert all("github.com" in r.url for r in results)
        print("✓ Domain filter working")
        
    finally:
        cleanup(services)


def test_stats_total():
    """Test 4: Get total bookmark count."""
    print("\n=== Test 4: Stats - Total Count ===")
    services = setup_services()
    
    try:
        # Save 4 bookmarks
        for url in [
            "https://github.com/anthropics/mcp",
            "https://aws.amazon.com/bedrock/",
            "https://python.org/docs/tutorial",
            "https://github.com/pytorch/pytorch",
        ]:
            services["bookmark"].save_bookmark(BookmarkCreate(url=url))
        
        # Get total count
        result = services["duckdb"].conn.execute(
            "SELECT COUNT(*) FROM bookmarks"
        ).fetchone()
        
        print(f"Total bookmarks: {result[0]}")
        assert result[0] == 4
        print("✓ Total count correct")
        
    finally:
        cleanup(services)


def test_stats_by_domain():
    """Test 5: Stats by domain."""
    print("\n=== Test 5: Stats - By Domain ===")
    services = setup_services()
    
    try:
        # Save bookmarks
        for url in [
            "https://github.com/anthropics/mcp",
            "https://github.com/pytorch/pytorch",
            "https://aws.amazon.com/bedrock/",
            "https://python.org/docs/tutorial",
        ]:
            services["bookmark"].save_bookmark(BookmarkCreate(url=url))
        
        # Get domain breakdown
        results = services["duckdb"].conn.execute("""
            SELECT domain, COUNT(*) as count
            FROM bookmarks
            GROUP BY domain
            ORDER BY count DESC
        """).fetchall()
        
        print("Domain breakdown:")
        for domain, count in results:
            print(f"  {domain}: {count}")
        
        assert len(results) == 3
        assert results[0][1] == 2  # github.com has 2
        print("✓ Domain stats correct")
        
    finally:
        cleanup(services)


def test_stats_by_tag():
    """Test 6: Stats by tag."""
    print("\n=== Test 6: Stats - By Tag ===")
    services = setup_services()
    
    try:
        # Save bookmarks with tags
        for url, tags in [
            ("https://github.com/anthropics/mcp", ["ai", "mcp"]),
            ("https://aws.amazon.com/bedrock/", ["ai", "aws"]),
            ("https://python.org/docs/tutorial", ["python"]),
            ("https://github.com/pytorch/pytorch", ["ai", "ml"]),
        ]:
            services["bookmark"].save_bookmark(
                BookmarkCreate(url=url, manual_tags=tags)
            )
        
        # Get tag breakdown
        results = services["duckdb"].conn.execute("""
            SELECT tag, COUNT(*) as count
            FROM bookmark_tags
            GROUP BY tag
            ORDER BY count DESC
        """).fetchall()
        
        print("Tag breakdown:")
        for tag, count in results:
            print(f"  {tag}: {count}")
        
        ai_count = next((c for t, c in results if t == "ai"), 0)
        assert ai_count == 3
        print("✓ Tag stats correct")
        
    finally:
        cleanup(services)


def test_update_and_delete():
    """Test 7: Update and delete bookmarks."""
    print("\n=== Test 7: Update and Delete ===")
    services = setup_services()
    
    try:
        from bookmark_lens.models.bookmark import BookmarkUpdate
        
        # Save bookmark
        saved = services["bookmark"].save_bookmark(
            BookmarkCreate(
                url="https://github.com/anthropics/mcp",
                manual_tags=["old"],
                note="Original"
            )
        )
        print(f"✓ Saved: {saved.title}")
        
        # Update
        updated = services["bookmark"].update_bookmark(
            saved.id,
            BookmarkUpdate(note="Updated", manual_tags=["new"], tag_mode="replace")
        )
        assert updated.user_note == "Updated"
        assert "new" in updated.tags
        print("✓ Updated note and tags")
        
        # Delete
        deleted = services["bookmark"].delete_bookmark(saved.id)
        assert deleted is True
        print("✓ Deleted bookmark")
        
        # Verify gone
        retrieved = services["bookmark"].get_bookmark(saved.id)
        assert retrieved is None
        print("✓ Bookmark no longer exists")
        
    finally:
        cleanup(services)


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("BOOKMARK-LENS INTEGRATION TESTS (Core Mode - No LLM)")
    print("=" * 60)
    
    tests = [
        test_save_bookmarks,
        test_search_semantic,
        test_search_with_filters,
        test_stats_total,
        test_stats_by_domain,
        test_stats_by_tag,
        test_update_and_delete,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
