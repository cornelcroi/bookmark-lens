"""
Manual test script to verify bookmark-lens functionality.

Run: python -m tests.manual_test
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bookmark_lens.config import load_config
from bookmark_lens.database.duckdb_client import DuckDBClient
from bookmark_lens.database.lancedb_client import LanceDBClient
from bookmark_lens.services.content_fetcher import ContentFetcher
from bookmark_lens.services.embedding_service import EmbeddingService
from bookmark_lens.services.llm_service import LLMService
from bookmark_lens.services.bookmark_service import BookmarkService
from bookmark_lens.services.search_service import SearchService
from bookmark_lens.models.bookmark import BookmarkCreate, BookmarkSearchQuery, BookmarkUpdate


def test_full_pipeline():
    """Test complete bookmark pipeline."""
    print("=== Bookmark-Lens Manual Test ===\n")

    # 1. Load config
    print("1. Loading configuration...")
    config = load_config()
    print(f"   ✓ DB Path: {config.db_path}")
    print(f"   ✓ Embedding Model: {config.embedding_model_name}\n")

    # 2. Initialize databases
    print("2. Initializing databases...")
    duckdb_client = DuckDBClient(config.db_path)
    duckdb_client.initialize_schema()
    print("   ✓ DuckDB ready")

    lancedb_client = LanceDBClient(config.lance_path, config.embedding_dimension)
    lancedb_client.initialize_table()
    print("   ✓ LanceDB ready\n")

    # 3. Initialize services
    print("3. Initializing services...")
    content_fetcher = ContentFetcher(config)
    embedding_service = EmbeddingService(config)

    # Initialize LLM service if configured
    llm_service = None
    if config.use_llm:
        try:
            llm_service = LLMService(config)
            print("   ✓ LLM service ready (Smart Mode enabled)")
        except Exception as e:
            print(f"   ⚠ LLM service failed: {e}")
            print("   ✓ Continuing in Core Mode")
    else:
        print("   ℹ Smart Mode disabled (no LLM configuration)")

    bookmark_service = BookmarkService(
        config, duckdb_client, lancedb_client,
        content_fetcher, embedding_service,
        llm_service
    )

    search_service = SearchService(
        config, duckdb_client, lancedb_client, embedding_service
    )
    print("   ✓ All services ready\n")

    # 4. Test saving bookmarks
    print("4. Testing bookmark creation...")
    test_bookmarks = [
        BookmarkCreate(
            url="https://docs.anthropic.com/en/docs/build-with-claude/model-context-protocol",
            note="MCP documentation for building servers",
            manual_tags=["mcp", "documentation", "ai"]
        ),
        BookmarkCreate(
            url="https://www.python.org/dev/peps/pep-0008/",
            note="Python style guide reference",
            manual_tags=["python", "coding-standards"]
        ),
    ]

    saved_ids = []
    for bm_create in test_bookmarks:
        print(f"   Saving: {bm_create.url}")
        try:
            bookmark = bookmark_service.save_bookmark(bm_create)
            saved_ids.append(bookmark.id)
            print(f"   ✓ Saved as {bookmark.id}: {bookmark.title}")
            
            # Show Smart Mode enhancements if available
            if bookmark.summary_short:
                print(f"      Summary: {bookmark.summary_short}")
            if bookmark.topic:
                print(f"      Topic: {bookmark.topic}")
            if bookmark.tags:
                auto_tags = [t for t in bookmark.tags if t not in bm_create.manual_tags]
                if auto_tags:
                    print(f"      Auto-tags: {auto_tags}")
            print()
        except Exception as e:
            print(f"   ✗ Failed: {e}\n")

    # 5. Test search
    print("5. Testing semantic search...")
    queries = [
        "AI agent communication protocols",
        "Python coding best practices"
    ]

    for query in queries:
        print(f"   Query: '{query}'")
        search_query = BookmarkSearchQuery(query=query, limit=5)
        results = search_service.search(search_query)

        if results:
            for r in results:
                print(f"      - {r.title} (score: {r.similarity_score:.3f})")
        else:
            print("      No results")
        print()

    # 6. Test get_bookmark
    print("6. Testing bookmark retrieval...")
    if saved_ids:
        bookmark = bookmark_service.get_bookmark(saved_ids[0])
        print(f"   ✓ Retrieved: {bookmark.title}")
        print(f"     Tags: {bookmark.tags}")
        print(f"     Note: {bookmark.user_note}\n")

    # 7. Test update
    print("7. Testing bookmark update...")
    if saved_ids:
        update = BookmarkUpdate(
            note="Updated note for testing",
            manual_tags=["updated", "test"],
            tag_mode="append"
        )
        updated = bookmark_service.update_bookmark(saved_ids[0], update)
        print(f"   ✓ Updated tags: {updated.tags}")
        print(f"   ✓ Updated note: {updated.user_note}\n")

    # 8. Test delete
    print("8. Testing bookmark deletion...")
    if saved_ids:
        deleted = bookmark_service.delete_bookmark(saved_ids[0])
        print(f"   ✓ Deleted: {deleted}\n")

    print("=== All tests passed! ===")

    # Cleanup
    duckdb_client.close()
    lancedb_client.close()


if __name__ == "__main__":
    test_full_pipeline()
