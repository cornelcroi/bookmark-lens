# Bookmark Lens

**Your AI assistant remembers everything you've saved.**

[![PyPI version](https://badge.fury.io/py/bookmark-lens.svg)](https://badge.fury.io/py/bookmark-lens)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is Bookmark Lens?

Tired of losing bookmarks in browser folders? Searching for "that article about React hooks" but can't remember if it mentioned "hooks" or "useState" or "functional components"?

**Bookmark Lens** solves this with semantic search. Find bookmarks by what they're *about*, not just exact keywords. Search "authentication tutorials" and get results about login systems, OAuth, JWT - even if they never mention the word "authentication."

**Traditional bookmarks:** Folders → Subfolder → Where did I save it? → Give up, Google it again
**With Bookmark Lens:** "Find that React tutorial from last week" → Found instantly

All processing happens locally on your machine. Your bookmarks stay private.

## See It In Action

*Demo coming soon - intelligent bookmark search in action*

## Why Bookmark Lens?

- **🧠 Semantic Search** - Find by meaning, not keywords
- **🔒 100% Private** - Everything local, nothing sent to cloud
- **⚡ Works Offline** - No internet needed after first setup
- **🆓 Completely Free** - No API keys for core features
- **🤖 AI-Powered** - Optional LLM enhancements (summaries, auto-tags)

## Features

- **Semantic Search** - Find bookmarks by meaning, not just keywords
- **Rich Metadata** - Automatic extraction of titles, descriptions, and content
- **Smart Mode** - LLM-powered summaries, auto-tags, and topic classification (optional)
- **Smart Tagging** - Manual tags + auto-generated tags (Smart Mode)
- **Topic Classification** - Automatic categorization (Smart Mode)
- **Date Filtering** - Search by time ranges (natural language supported via LLM)
- **Domain Filtering** - Filter by website
- **Local-First** - All data stored locally (DuckDB + LanceDB)
- **MCP Native** - Works with Claude Desktop and other MCP clients
- **Fast** - Local embeddings with sentence-transformers

---

## Quick Setup

### Claude Desktop

1. Open your Claude Desktop config file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add bookmark-lens to the `mcpServers` section:

```json
{
  "mcpServers": {
    "bookmark-lens": {
      "command": "uvx",
      "args": ["bookmark-lens"]
    }
  }
}
```

3. Restart Claude Desktop

That's it! No installation, no setup, no configuration needed.

### Other MCP Clients

For other MCP-compatible clients, use:

```bash
uvx bookmark-lens
```

---

## Example Conversations

### Research Workflow

```
You: Save https://arxiv.org/abs/2401.12345 with note "Interesting paper on attention mechanisms"

Claude: Saved! I've extracted:
- Title: "Efficient Attention: A Survey"
- Description: Comprehensive review of attention mechanisms...
- Auto-generated tags: #ai #research #attention #transformers

You: Find papers about attention from this month

Claude: Found 3 bookmarks:
1. "Efficient Attention: A Survey" (arxiv.org) - Today
   Tags: ai, research, attention, transformers

2. "Flash Attention Implementation" (github.com) - 3 days ago
   Tags: pytorch, optimization, gpu

3. "Attention is All You Need - Annotated" (nlp.seas.harvard.edu) - 1 week ago
   Tags: tutorial, transformers, nlp
```

### Learning Path

```
You: I'm learning React. Save good tutorials as I find them with tag #react-learning

Claude: Great! I'll tag them for you.

You: [Later] Show me all my React learning resources

Claude: You have 12 React bookmarks:

**Fundamentals (4 bookmarks):**
- Official React Docs - react.dev
- React Tutorial for Beginners - youtube.com
- Thinking in React - beta.reactjs.org

**Advanced (5 bookmarks):**
- Custom Hooks Patterns - usehooks.com
- React Performance Optimization - web.dev
...

You: Which ones cover hooks?

Claude: 8 of your bookmarks discuss hooks:
[Semantic search finds all hook-related content even without "hooks" in title]
```

### Content Curation

```
You: Show me my GitHub bookmarks by topic

Claude: Here's the breakdown:

**AI/ML (15 bookmarks)**
- Transformer models
- LLM training techniques
- Embedding systems

**Frontend (23 bookmarks)**
- React ecosystem
- Build tools
- State management

**DevOps (8 bookmarks)**
- Kubernetes guides
- CI/CD pipelines

You: What are my top 3 most-saved domains?

Claude:
1. github.com - 47 bookmarks
2. medium.com - 23 bookmarks
3. dev.to - 18 bookmarks
```

> **More examples:** See [USAGE_GUIDE.md](USAGE_GUIDE.md) for detailed workflows and advanced query patterns.

---

## Architecture

```
bookmark-lens/
├── src/bookmark_lens/
│   ├── server.py              # MCP server (stdio transport)
│   ├── config.py              # Configuration management
│   ├── database/
│   │   ├── duckdb_client.py   # Relational data (bookmarks, tags)
│   │   └── lancedb_client.py  # Vector embeddings
│   ├── models/
│   │   └── bookmark.py        # Pydantic models
│   └── services/
│       ├── content_fetcher.py # Web page fetching
│       ├── embedding_service.py # Text → vectors
│       ├── bookmark_service.py # Orchestration
│       └── search_service.py  # Hybrid search
├── data/                      # Local databases (gitignored)
└── tests/
    └── manual_test.py         # End-to-end testing
```

### Technology Stack

- **MCP SDK** - Model Context Protocol for AI integration
- **DuckDB** - Relational database (bookmarks, metadata, tags)
- **LanceDB** - Vector database (embeddings for semantic search)
- **sentence-transformers** - Local embedding model (all-MiniLM-L6-v2)
- **readability-lxml** - Content extraction from web pages
- **Pydantic** - Data validation and serialization

> **Technical deep-dive:** See [TECHNICAL.md](TECHNICAL.md) for hybrid search architecture, performance benchmarks, and implementation details.

---

## FAQ

**How is this different from browser bookmarks?**
Browser bookmarks use folders and exact name matching. Bookmark Lens uses AI to understand meaning. Search "authentication" and find bookmarks about login, OAuth, JWT - even if they never use that word.

**What about Raindrop.io or Pocket?**
They're cloud-based (your data on their servers) and require subscriptions for advanced features. Bookmark Lens is 100% local and free. Your data never leaves your machine.

**Do I need an API key?**
No! Core features (save, search, tag) work completely offline with no API keys. Smart Mode (auto-summaries, auto-tags) is optional and uses your own LLM API key.

**How much does Smart Mode cost?**
With Claude Haiku: ~$0.0005 per bookmark (half a cent). Process 1000 bookmarks for $0.50. It's optional - core features are free.

**Is my data private?**
100% private. Everything runs locally. Core features don't use the internet at all. Smart Mode only sends bookmark content to your chosen LLM (not to us).

**What if I have thousands of bookmarks?**
Bookmark Lens handles thousands easily. Vector search is fast even with large collections. The sentence-transformer model runs locally on your CPU.

**Why semantic search instead of keywords?**
Keywords fail when you don't remember exact words. "Find that authentication tutorial" won't find "OAuth guide for beginners." Semantic search understands they're about the same topic.

**Can I export my bookmarks?**
Not yet (roadmap feature). Currently, data is in local DuckDB + LanceDB databases. You can access them directly if needed.

---

## MCP Tools

### `save_bookmark`
Save a URL with optional note and tags.

**Parameters:**
- `url` (required): URL to bookmark
- `note` (optional): Context or reason for saving
- `tags` (optional): List of tags

**Example:**
```json
{
  "url": "https://example.com/article",
  "note": "Great explanation of embeddings",
  "tags": ["ai", "ml", "tutorial"]
}
```

### `search_bookmarks`
Search bookmarks semantically with optional filters.

**Parameters:**
- `query` (required): What to search for
- `domain` (optional): Filter by domain (e.g., "github.com")
- `tags` (optional): Filter by tags
- `from_date` (optional): ISO 8601 date string
- `to_date` (optional): ISO 8601 date string
- `limit` (optional): Max results (default: 10)

**Example:**
```json
{
  "query": "machine learning tutorials",
  "domain": "github.com",
  "tags": ["python"],
  "from_date": "2024-11-07T00:00:00Z",
  "limit": 5
}
```

### `get_bookmark`
Get full details about a bookmark by ID.

**Parameters:**
- `id` (required): Bookmark ID

### `update_bookmark`
Update note and/or tags for a bookmark.

**Parameters:**
- `id` (required): Bookmark ID
- `note` (optional): New note
- `tags` (optional): Tags to add/replace
- `tag_mode` (optional): "replace" or "append" (default: "replace")

### `delete_bookmark`
Delete a bookmark and all its associated data.

**Parameters:**
- `id` (required): Bookmark ID

**Example:**
```json
{
  "id": "bkm_abc123"
}
```

### `list_tags`
List all tags with their usage counts.

**Parameters:** None

**Example Response:**
```json
{
  "success": true,
  "count": 5,
  "tags": [
    {"tag": "ai", "count": 20},
    {"tag": "python", "count": 15},
    {"tag": "tutorial", "count": 8}
  ]
}
```

### `get_bookmark_stats`
Get statistics about your bookmark collection with optional filters.

**Parameters:**
- `stat_type` (optional): Type of statistics
  - `"total"` - Total count (default)
  - `"by_domain"` - Breakdown by domain
  - `"by_topic"` - Breakdown by topic
  - `"by_tag"` - Breakdown by tag
  - `"by_date"` - Activity over time
- `domain` (optional): Filter by domain
- `topic` (optional): Filter by topic
- `tags` (optional): Filter by tags
- `from_date` (optional): Filter after date (ISO 8601)
- `to_date` (optional): Filter before date (ISO 8601)
- `limit` (optional): For breakdown stats, top N results (default: 10)

**Examples:**

Total bookmarks:
```json
{
  "stat_type": "total"
}
```

Bookmarks saved this week:
```json
{
  "stat_type": "total",
  "from_date": "2024-11-07T00:00:00Z"
}
```

Top domains:
```json
{
  "stat_type": "by_domain",
  "limit": 5
}
```

AI bookmarks by domain:
```json
{
  "stat_type": "by_domain",
  "topic": "AI"
}
```

---

## Configuration

All configuration is via environment variables (`.env` file):

```bash
# Database paths
BOOKMARK_LENS_DUCKDB_PATH=./data/bookmark_lens.db
BOOKMARK_LENS_LANCEDB_PATH=./data/embeddings.lance

# Embedding model
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Content fetching
BOOKMARK_LENS_FETCH_TIMEOUT=30
BOOKMARK_LENS_USER_AGENT=bookmark-lens/0.1.0
MAX_CONTENT_LENGTH=50000
```

---

## Smart Mode (LLM Enhancements)

Enable Smart Mode to get automatic summaries, tags, and topic classification for your bookmarks.

### Setup

1. Choose an LLM model (see [LiteLLM providers](https://docs.litellm.ai/docs/providers))
2. Get an API key from your provider
3. Add to `.env`:
   ```bash
   LLM_MODEL=claude-3-haiku-20240307
   LLM_API_KEY=your-api-key-here
   ```
4. Restart the server

### Recommended Models

- `claude-3-haiku-20240307` - Fast, cheap, good quality (Anthropic) **[Recommended]**
- `gpt-4o-mini` - Fast, cheap (OpenAI)
- `gpt-4o` - Better quality, more expensive (OpenAI)
- `claude-3-5-sonnet-20241022` - Best quality (Anthropic)

See [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for 100+ supported models.

### What Smart Mode Adds

- **Auto-summaries**: Short (1-2 sentences) and long (1 paragraph) summaries
- **Auto-tags**: 3-5 relevant tags automatically generated
- **Topic classification**: High-level category (AI, Cloud, Programming, Data, Security, DevOps, Design, Business, Science, Other)
- **Better search**: Summaries and topics included in embeddings for improved relevance
- **Markdown extraction**: Full content extracted as Markdown (preserves structure)

### Cost Estimate

With `claude-3-haiku-20240307`: **~$0.0005 per bookmark** (very cheap!)

### Performance

- **Core Mode** (no LLM): Fast saves, only title/description extracted
- **Smart Mode** (with LLM): Slower saves (~5-10s), full content + enhancements

**Note:** Smart Mode is completely optional. All core features work without any LLM configuration.

---

### Embedding Models

Default: `all-MiniLM-L6-v2` (384 dimensions, fast, good quality)

Alternatives:
- `all-mpnet-base-v2` (768 dimensions, better quality, slower)
- `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, multilingual)

Change in `.env`:
```bash
EMBEDDING_MODEL_NAME=all-mpnet-base-v2
EMBEDDING_DIMENSION=768
```

---

## How It Works

### Saving a Bookmark

1. **Fetch** - Downloads the web page
2. **Extract** - Pulls out title, description, main content (Markdown in Smart Mode)
3. **Enhance** - Generates summaries, tags, topic (Smart Mode only)
4. **Embed** - Converts text to vector using local model
5. **Store** - Saves to DuckDB (metadata) and LanceDB (vector)

### Searching Bookmarks

1. **Embed Query** - Converts search text to vector
2. **Vector Search** - Finds similar bookmarks (LanceDB)
3. **Filter** - Applies domain/tag/date filters (DuckDB)
4. **Rank** - Sorts by similarity score
5. **Return** - Top N results with relevance scores

### Natural Language Dates

The LLM (via the `bookmark_search_guide` prompt) converts natural language to ISO dates:
- "yesterday" → `2024-11-13T00:00:00Z`
- "last week" → `2024-11-07T00:00:00Z`
- "last month" → `2024-10-14T00:00:00Z`

The server only accepts ISO 8601 format - the LLM does the conversion.

---

## Development

Want to contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions.

### Running Tests

```bash
# Clone the repository
git clone https://github.com/yourusername/bookmark-lens.git
cd bookmark-lens

# Install in development mode
pip install -e ".[dev]"

# Run tests
python tests/test_simple.py
```

---

## Troubleshooting

### "Model not found" error
The first run downloads the embedding model (~80MB). This is normal and happens once.

### "Database locked" error
Close any other processes using the database. DuckDB doesn't support concurrent writes.

### Search returns no results
- Check if bookmarks were saved successfully
- Try a broader query
- Verify embedding model loaded correctly

### Slow first search
The embedding model loads on first use. Subsequent searches are fast.

---

## Roadmap

### Phase 2 (Smart Mode - Future)
- LLM-powered summaries
- Auto-tagging
- Topic classification
- Query expansion

### Future Features
- Browser history import
- Browser extension
- Export/import bookmarks
- Bookmark collections
- Sharing capabilities

---

## License

MIT License - see LICENSE file for details.

---

## Contributing

Contributions welcome! Please:
1. Check `TASKS.md` for current status
2. Follow existing code style (minimal, focused implementations)
3. Add tests for new features
4. Update documentation

---

## Credits

Built with:
- [MCP SDK](https://github.com/anthropics/mcp) by Anthropic
- [DuckDB](https://duckdb.org/) - Fast analytical database
- [LanceDB](https://lancedb.com/) - Vector database
- [sentence-transformers](https://www.sbert.net/) - Embedding models
- [readability-lxml](https://github.com/buriy/python-readability) - Content extraction
