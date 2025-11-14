# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-11-14

### Added
- Initial release
- Core Mode: Local-first bookmark management without LLM
- Smart Mode: Optional LLM-powered enhancements (summaries, auto-tags, topics)
- Semantic search with sentence-transformers embeddings
- MCP server with 7 tools:
  - `save_bookmark` - Save URLs with notes and tags
  - `search_bookmarks` - Semantic search with filters
  - `get_bookmark` - Retrieve bookmark details
  - `update_bookmark` - Update notes and tags
  - `delete_bookmark` - Delete bookmarks
  - `list_tags` - List all tags with counts
  - `get_bookmark_stats` - Flexible statistics queries
- DuckDB for relational data storage
- LanceDB for vector embeddings
- Automatic content extraction from web pages
- Domain and tag filtering
- Date range filtering with natural language support
- Comprehensive test suite with mocked URL fetching

### Features
- Works completely offline in Core Mode
- Optional LLM integration for Smart Mode
- Local embeddings (no API calls for search)
- Fast semantic search
- Flexible statistics and analytics
- Graceful degradation when LLM unavailable

[0.1.0]: https://github.com/yourusername/bookmark-lens/releases/tag/v0.1.0
