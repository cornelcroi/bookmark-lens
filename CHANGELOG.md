# Changelog

All notable changes to Bookmark Lens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Browser extension for one-click bookmarking
- Import from browser bookmarks (Chrome, Firefox, Safari)
- Export bookmarks to various formats (JSON, CSV, HTML)
- Duplicate bookmark detection
- Bookmark collections/folders
- Shared bookmarks (multi-user support)

---

## [0.2.0] - 2024-11-15

### Added
- Comprehensive documentation:
  - USAGE_GUIDE.md with 4 detailed workflows
  - TECHNICAL.md with architecture deep-dive
  - TROUBLESHOOTING.md for common issues
- Smart Mode enhancements with better auto-tagging
- Statistics and analytics tools
- Content fetching improvements

### Changed
- Improved README with use-case focus
- Enhanced search relevance scoring
- Updated documentation structure

---

## [0.1.0] - 2024-10-01

### Added
- Initial release of Bookmark Lens
- MCP server for bookmark management
- Hybrid search (DuckDB + LanceDB)
- Semantic search with sentence-transformers
- Core Mode (no LLM):
  - Save bookmarks with metadata
  - Manual tags and notes
  - Semantic search with filters
- Smart Mode (optional LLM):
  - Auto-summarization
  - Auto-tagging
  - Topic classification
- 8 MCP tools for bookmark management
- Local embedding generation (all-MiniLM-L6-v2)
- LLM integration via litellm
- Python 3.10+ support

---

## Versioning Guide

**MAJOR** (x.0.0): Incompatible API changes
**MINOR** (0.x.0): New features (backward compatible)
**PATCH** (0.0.x): Bug fixes (backward compatible)
