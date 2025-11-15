# Bookmark Lens - Troubleshooting Guide

Solutions to common issues and error messages.

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Connection Issues](#connection-issues)
- [Content Fetching Errors](#content-fetching-errors)
- [Embedding Model Issues](#embedding-model-issues)
- [Database Errors](#database-errors)
- [Smart Mode Issues](#smart-mode-issues)
- [Performance Problems](#performance-problems)
- [Search Issues](#search-issues)

---

## Installation Issues

### "Command not found: uvx"

**Problem:** `uvx` is not installed.

**Solution:**
```bash
pip install uv
```

Or use pip directly:
```bash
pip install bookmark-lens
```

### "No module named 'bookmark_lens'"

**Problem:** Package not installed correctly.

**Solution:**
```bash
# Uninstall and reinstall
pip uninstall bookmark-lens
pip install bookmark-lens --force-reinstall
```

### Import errors after installation

**Problem:** Dependency conflicts or incomplete installation.

**Solution:**
```bash
# Update all dependencies
pip install --upgrade bookmark-lens

# Or install in isolated environment
python -m venv venv
source venv/bin/activate
pip install bookmark-lens
```

---

## Connection Issues

### "Server not showing in Claude Desktop"

**Problem:** MCP server not configured correctly.

**Solution:**
1. Check config file location:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Verify JSON syntax:
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

3. Restart Claude Desktop completely (quit, not just close window)

4. Check logs:
   ```bash
   # macOS
   tail -f ~/Library/Logs/Claude/mcp*.log
   ```

### "Server crashes on startup"

**Problem:** Corrupted database or missing dependencies.

**Solution:**
1. Test manually:
   ```bash
   uvx bookmark-lens
   ```

2. Check for errors in output

3. If database is corrupted, reset:
   ```bash
   # Backup first!
   mv ~/.local/share/bookmark-lens ~/.local/share/bookmark-lens.backup

   # Restart (creates fresh database)
   uvx bookmark-lens
   ```

### "Tools not available in Claude"

**Problem:** Server connected but tools not registered.

**Solution:**
1. Verify server is listed in Claude Desktop settings

2. Try asking: "What tools do you have access to?"

3. If bookmark-lens tools aren't listed, restart server:
   - Quit Claude Desktop
   - Reopen
   - Try again

---

## Content Fetching Errors

### "Model download timeout" on first run

**Problem:** sentence-transformers model downloading slowly.

**Solution:**
Wait for download to complete (~80MB). This happens once.

Check progress:
```bash
# Model cache location
ls -lh ~/.cache/torch/sentence_transformers/
```

Or download manually:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
# Wait for download, then restart bookmark-lens
```

### "Timeout fetching URL"

**Problem:** Website took too long to respond (>30s).

**Solution:**
1. Check if URL is accessible in browser
2. Increase timeout (environment variable):
   ```bash
   export BOOKMARK_LENS_FETCH_TIMEOUT=60
   uvx bookmark-lens
   ```
3. Save without content (bookmark still created):
   - Title will be extracted from URL
   - Add note manually

### "Failed to fetch content"

**Problem:** Website blocked the request or returned error.

**Solution:**
1. Check if site requires authentication
2. Site might block automated requests
3. Try different URL (e.g., article vs homepage)
4. Manual workaround:
   ```
   You: Save https://example.com with note "Manual description of content"
   ```

### "SSL verification failed"

**Problem:** SSL certificate issue.

**Solution:**
1. Check if site's SSL cert is valid in browser
2. Update system certificates:
   ```bash
   # macOS
   /Applications/Python\ 3.11/Install\ Certificates.command

   # Linux
   sudo update-ca-certificates
   ```

3. Temporarily disable verification (not recommended):
   ```bash
   export BOOKMARK_LENS_SSL_VERIFY=false
   uvx bookmark-lens
   ```

---

## Embedding Model Issues

### "ModuleNotFoundError: No module named 'sentence_transformers'"

**Problem:** sentence-transformers not installed.

**Solution:**
```bash
pip install sentence-transformers
```

Should be installed automatically, but sometimes fails.

### "Model loading is slow"

**Problem:** First load always slow (model initialization).

**Solution:**
Wait for first load (~5-10 seconds). Subsequent uses are instant.

Model is cached at: `~/.cache/torch/sentence_transformers/`

### "CUDA out of memory" (if using GPU)

**Problem:** GPU memory insufficient.

**Solution:**
Force CPU usage:
```bash
export CUDA_VISIBLE_DEVICES=""
uvx bookmark-lens
```

Or use smaller model:
```bash
export EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2  # Default, smallest
```

### "Wrong embedding dimension"

**Problem:** Changed model but dimension doesn't match database.

**Solution:**
1. If you changed `EMBEDDING_MODEL_NAME`, also change `EMBEDDING_DIMENSION`:
   ```bash
   # all-MiniLM-L6-v2
   EMBEDDING_DIMENSION=384

   # all-mpnet-base-v2
   EMBEDDING_DIMENSION=768
   ```

2. If database was created with old model, reset:
   ```bash
   rm -rf ~/.local/share/bookmark-lens/embeddings.lance
   ```

---

## Database Errors

### "Database is locked"

**Problem:** DuckDB doesn't support concurrent writes.

**Solution:**
1. Close other bookmark-lens processes:
   ```bash
   ps aux | grep bookmark-lens
   kill <pid>
   ```

2. Don't run multiple instances

3. If persists, remove lock file:
   ```bash
   rm ~/.local/share/bookmark-lens/*.db.wal
   ```

### "Table does not exist"

**Problem:** Database not initialized or corrupted.

**Solution:**
Reset database (creates fresh schema):
```bash
# Backup first
mv ~/.local/share/bookmark-lens ~/.local/share/bookmark-lens.backup

# Restart server
uvx bookmark-lens
```

### "Disk full"

**Problem:** No space for database.

**Solution:**
1. Check disk space:
   ```bash
   df -h
   ```

2. Clean old data:
   ```bash
   # Check database size
   du -sh ~/.local/share/bookmark-lens
   ```

3. Move to different location:
   ```bash
   export BOOKMARK_LENS_HOME=/path/to/larger/disk
   uvx bookmark-lens
   ```

### "Cannot write to database"

**Problem:** Permission denied.

**Solution:**
```bash
# Fix permissions
chmod -R u+w ~/.local/share/bookmark-lens

# Or run with sudo (not recommended)
sudo uvx bookmark-lens
```

---

## Smart Mode Issues

### "LLM API key not found"

**Problem:** Smart Mode enabled but no API key.

**Solution:**
1. Add to `.env` file:
   ```bash
   LLM_API_KEY=your-key-here
   LLM_MODEL=claude-3-haiku-20240307
   ```

2. Or set environment variable:
   ```bash
   export LLM_API_KEY=your-key-here
   uvx bookmark-lens
   ```

3. To disable Smart Mode, unset LLM_MODEL:
   ```bash
   unset LLM_MODEL
   ```

### "LLM rate limit exceeded"

**Problem:** Too many API calls too quickly.

**Solution:**
1. Wait a moment before next save

2. Batch saves:
   ```
   You: Save these URLs:
   - https://example1.com
   - https://example2.com
   - https://example3.com
   ```

3. Switch to higher-tier plan (if available)

4. Use cheaper model (Haiku instead of Opus)

### "LLM timeout"

**Problem:** LLM took too long to respond.

**Solution:**
1. Retry the save operation

2. Check LLM service status

3. Increase timeout:
   ```bash
   export LLM_TIMEOUT=60
   ```

4. Try different model

### "Invalid JSON from LLM"

**Problem:** LLM returned malformed response.

**Solution:**
Bookmark is saved without Smart Mode enhancements.

If happens repeatedly:
1. Check LLM model (Haiku/GPT-4o-mini are most reliable)
2. Update bookmark-lens to latest version
3. File an issue on GitHub

---

## Performance Problems

### "Searches are slow"

**Problem:** Large bookmark collection or first search after startup.

**Diagnosis:**
```
- First search after startup: Model loading (normal)
- Always slow: Collection size issue
- Specific queries slow: Complex filters
```

**Solutions:**
1. Wait for first search (model loads once)

2. For large collections (>10K bookmarks):
   - Reduce limit: `limit=5` instead of `limit=50`
   - Add specific filters (domain, tags, dates)
   - Consider archiving old bookmarks

3. Check database size:
   ```bash
   du -sh ~/.local/share/bookmark-lens
   ```

### "Saves are very slow"

**Problem:** Content fetching or LLM calls taking time.

**Solutions:**
1. Core Mode (no LLM): ~1-2 seconds (normal)

2. Smart Mode: ~5-10 seconds (normal)

3. If slower:
   - Check internet connection
   - Website might be slow
   - LLM API might be slow
   - Disable Smart Mode for faster saves

### "High memory usage"

**Problem:** Application using too much RAM.

**Diagnosis:**
```bash
ps aux | grep bookmark-lens
```

**Solutions:**
1. Normal usage: ~250-350MB (acceptable)

2. If higher:
   - Large bookmarks with lots of content
   - Many bookmarks in database
   - Model loaded in memory

3. To reduce:
   ```bash
   # Use smaller model
   export EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2

   # Limit content length
   export MAX_CONTENT_LENGTH=10000
   ```

---

## Search Issues

### "Search returns no results"

**Problem:** Query doesn't match any bookmarks.

**Diagnosis:**
1. Check if bookmarks exist:
   ```
   You: How many bookmarks do I have?
   ```

2. Try broader query:
   ```
   ❌ "advanced react server components patterns"
   ✅ "react"
   ```

3. Check filters aren't too restrictive:
   ```
   # Too restrictive
   domain=github.com, tags=[python, ml, advanced]

   # Better
   domain=github.com, tags=[python]
   ```

**Solutions:**
- Start broad, then narrow
- Verify bookmark was saved successfully
- Try searching by domain or tag only
- Check for typos

### "Search returns irrelevant results"

**Problem:** Semantic search found related but not desired content.

**Solutions:**
1. Add specific filters:
   ```
   Query: "authentication"
   Filters: domain = "github.com", tags = ["python"]
   ```

2. Use more specific query:
   ```
   ❌ "frontend"
   ✅ "react hooks tutorial for forms"
   ```

3. Search by exact tag:
   ```
   You: Show me bookmarks tagged #oauth
   ```

### "Can't find bookmark I just saved"

**Problem:** Bookmark not yet indexed or save failed.

**Solutions:**
1. Wait a moment (embedding generation takes 1-2s)

2. Verify save succeeded:
   ```
   You: Show me my most recent bookmark
   ```

3. Search by URL:
   ```
   You: Find bookmark for example.com
   ```

4. Check if save returned error

### "Duplicate bookmarks"

**Problem:** Same URL saved multiple times.

**Cause:** URL normalization doesn't catch all variations.

**Solution:**
1. Search for duplicates:
   ```
   You: Do I have duplicate bookmarks for react.dev?
   ```

2. Delete duplicates:
   ```
   You: Delete bookmark <id>
   ```

3. Prevention (future feature): Auto-detect duplicates on save

---

## Common Error Messages

### "FileNotFoundError: [Errno 2] No such file or directory"

**Problem:** Database path not created.

**Solution:**
```bash
mkdir -p ~/.local/share/bookmark-lens
uvx bookmark-lens
```

### "RuntimeError: No embedding model loaded"

**Problem:** Model failed to load.

**Solution:**
```bash
# Clear cache and reload
rm -rf ~/.cache/torch/sentence_transformers
uvx bookmark-lens
```

### "ValidationError: Invalid bookmark data"

**Problem:** Corrupt bookmark data.

**Solution:**
Check bookmark fields are valid. If persists, file GitHub issue with details.

---

## Getting More Help

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uvx bookmark-lens
```

Save output to file for analysis:
```bash
uvx bookmark-lens 2>&1 | tee debug.log
```

### Check Version

```bash
pip show bookmark-lens
```

Update to latest:
```bash
pip install --upgrade bookmark-lens
```

### Report Issues

When reporting issues, include:
1. Operating system and version
2. Python version
3. bookmark-lens version
4. Full error message
5. Steps to reproduce
6. Debug logs (if possible)

Open issue: https://github.com/yourusername/bookmark-lens/issues

---

## FAQ

**Q: Why is first search slow?**
A: Embedding model loads on first use (~5-10s). Subsequent searches are fast.

**Q: Can I use bookmark-lens offline?**
A: Yes! Core features work offline. Smart Mode requires internet for LLM API.

**Q: How do I backup my bookmarks?**
A: Copy `~/.local/share/bookmark-lens` directory.

**Q: Can I import browser bookmarks?**
A: Not yet (planned feature).

**Q: Is there a browser extension?**
A: Not yet (planned feature).

---

**Still having issues?** Check the [README](README.md) or [TECHNICAL.md](TECHNICAL.md) for more details.
