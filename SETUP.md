# Setup & Configuration

Complete guide for setting up bookmark-lens with different MCP clients and customizing configuration.

## Quick Setup

### Claude Desktop

**Config file location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Basic configuration:**
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

Restart Claude Desktop and you're ready!

---

## Environment Variables

All configuration can be set via environment variables in your MCP server configuration.

### Complete Example

```json
{
  "mcpServers": {
    "bookmark-lens": {
      "command": "uvx",
      "args": ["bookmark-lens"],
      "env": {
        "BOOKMARK_LENS_HOME": "/path/to/your/data",
        "BOOKMARK_LENS_DUCKDB_PATH": "/custom/bookmarks.db",
        "BOOKMARK_LENS_LANCEDB_PATH": "/custom/embeddings.lance",
        "EMBEDDING_MODEL_NAME": "all-mpnet-base-v2",
        "EMBEDDING_DIMENSION": "768",
        "BOOKMARK_LENS_FETCH_TIMEOUT": "60",
        "BOOKMARK_LENS_USER_AGENT": "MyBookmarkManager/1.0",
        "MAX_CONTENT_LENGTH": "100000"
      }
    }
  }
}
```

### Available Variables

#### `BOOKMARK_LENS_HOME`
**Purpose:** Base directory for all bookmark-lens data  
**Default:** Platform-specific directory
- macOS: `~/Library/Application Support/bookmark-lens`
- Linux: `~/.local/share/bookmark-lens`
- Windows: `%LOCALAPPDATA%\bookmark-lens`

**Example:** `"/Users/you/Documents/bookmarks"`

---

#### `BOOKMARK_LENS_DUCKDB_PATH`
**Purpose:** Path to DuckDB database file (stores bookmark metadata, tags, notes)  
**Default:** `{BOOKMARK_LENS_HOME}/bookmark_lens.db`  
**Example:** `"/data/bookmarks.db"`

---

#### `BOOKMARK_LENS_LANCEDB_PATH`
**Purpose:** Path to LanceDB directory (stores vector embeddings for semantic search)  
**Default:** `{BOOKMARK_LENS_HOME}/embeddings.lance`  
**Example:** `"/fast-ssd/embeddings.lance"`

---

#### `EMBEDDING_MODEL_NAME`
**Purpose:** Sentence-transformers model for generating embeddings  
**Default:** `all-MiniLM-L6-v2`  
**Options:**
- `all-MiniLM-L6-v2` - 384 dimensions, ~90MB, fast, good quality
- `all-mpnet-base-v2` - 768 dimensions, ~420MB, better quality, slower

**Example:** `"all-mpnet-base-v2"`

---

#### `EMBEDDING_DIMENSION`
**Purpose:** Vector dimension (must match the model)  
**Default:** `384`  
**Values:**
- `384` for all-MiniLM-L6-v2
- `768` for all-mpnet-base-v2

**Example:** `"768"`

---

#### `BOOKMARK_LENS_FETCH_TIMEOUT`
**Purpose:** HTTP timeout when fetching web pages (in seconds)  
**Default:** `30`  
**Example:** `"60"` (for slow sites)

---

#### `BOOKMARK_LENS_USER_AGENT`
**Purpose:** Custom User-Agent string for HTTP requests  
**Default:** `bookmark-lens/0.1.0`  
**Example:** `"MyBookmarkManager/1.0"`

---

#### `MAX_CONTENT_LENGTH`
**Purpose:** Maximum characters to extract and store per bookmark  
**Default:** `50000`  
**Example:** `"100000"` (for longer articles)

---

## Example Configurations

### High-Quality Embeddings

Use a better embedding model for improved search quality:

```json
{
  "mcpServers": {
    "bookmark-lens": {
      "command": "uvx",
      "args": ["bookmark-lens"],
      "env": {
        "EMBEDDING_MODEL_NAME": "all-mpnet-base-v2",
        "EMBEDDING_DIMENSION": "768"
      }
    }
  }
}
```

**Note:** First run will download the model (~420MB). Searches will be slightly slower but more accurate.

### Custom Data Location

Store data in a specific directory:

```json
{
  "mcpServers": {
    "bookmark-lens": {
      "command": "uvx",
      "args": ["bookmark-lens"],
      "env": {
        "BOOKMARK_LENS_HOME": "/Users/you/Documents/bookmarks"
      }
    }
  }
}
```

### Longer Timeout for Slow Sites

Increase timeout for sites that take longer to load:

```json
{
  "mcpServers": {
    "bookmark-lens": {
      "command": "uvx",
      "args": ["bookmark-lens"],
      "env": {
        "BOOKMARK_LENS_FETCH_TIMEOUT": "60"
      }
    }
  }
}
```

---

## Data Location

By default, bookmark-lens stores data in platform-specific directories:

- **macOS**: `~/Library/Application Support/bookmark-lens/`
- **Linux**: `~/.local/share/bookmark-lens/`
- **Windows**: `%LOCALAPPDATA%\bookmark-lens\`

Inside this directory:
- `bookmark_lens.db` - DuckDB database (metadata, tags)
- `embeddings.lance/` - LanceDB vector database (embeddings)

### Backup Your Data

To backup your bookmarks:
```bash
# macOS/Linux
cp -r ~/Library/Application\ Support/bookmark-lens ~/bookmarks-backup

# Or just the database
cp ~/Library/Application\ Support/bookmark-lens/bookmark_lens.db ~/bookmarks-backup.db
```

---

## Troubleshooting

### Model Download Issues

First run downloads the embedding model (~90MB for default model). If it fails:

1. Check internet connection
2. Try again (downloads resume automatically)
3. Check disk space

### Database Locked Error

If you see "database is locked":
- Close other instances of bookmark-lens
- Restart Claude Desktop
- Check no other process is using the database

### Slow First Search

The embedding model loads on first use. Subsequent searches are fast.

---

## Other MCP Clients

For other MCP-compatible clients, use:

```bash
uvx bookmark-lens
```

Or if you prefer pip:

```bash
pip install bookmark-lens
bookmark-lens
```

Refer to your client's documentation for MCP server configuration.
