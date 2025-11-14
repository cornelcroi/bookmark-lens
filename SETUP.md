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

## Configuration Options

### Environment Variables

You can customize bookmark-lens behavior by setting environment variables in your MCP server configuration:

```json
{
  "mcpServers": {
    "bookmark-lens": {
      "command": "uvx",
      "args": ["bookmark-lens"],
      "env": {
        "BOOKMARK_LENS_HOME": "/custom/path/to/data",
        "EMBEDDING_MODEL_NAME": "all-mpnet-base-v2",
        "EMBEDDING_DIMENSION": "768"
      }
    }
  }
}
```

### Available Environment Variables

#### Data Storage

**`BOOKMARK_LENS_HOME`**
- Override the default data directory location
- Default: Platform-specific directory
  - macOS: `~/Library/Application Support/bookmark-lens`
  - Linux: `~/.local/share/bookmark-lens`
  - Windows: `%LOCALAPPDATA%\bookmark-lens`

**`BOOKMARK_LENS_DB_PATH`**
- Path to DuckDB database file
- Default: `{BOOKMARK_LENS_HOME}/bookmark_lens.db`

**`LANCE_DB_PATH`**
- Path to LanceDB directory (vector embeddings)
- Default: `{BOOKMARK_LENS_HOME}/embeddings.lance`

#### Embedding Configuration

**`EMBEDDING_MODEL_NAME`**
- Sentence-transformers model name
- Options:
  - `all-MiniLM-L6-v2` (default) - 384 dimensions, fast, good quality
  - `all-mpnet-base-v2` - 768 dimensions, better quality, slower
- Default: `all-MiniLM-L6-v2`

**`EMBEDDING_DIMENSION`**
- Vector dimension (must match model)
- Values:
  - `384` for all-MiniLM-L6-v2
  - `768` for all-mpnet-base-v2
- Default: `384`

#### Content Fetching

**`BOOKMARK_LENS_FETCH_TIMEOUT`**
- HTTP fetch timeout in seconds
- Default: `30`

**`BOOKMARK_LENS_USER_AGENT`**
- Custom User-Agent string for HTTP requests
- Default: `bookmark-lens/0.1.0`

**`MAX_CONTENT_LENGTH`**
- Maximum characters to store per bookmark
- Default: `50000`

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
