# Bookmark Lens - Technical Documentation

Deep dive into architecture, implementation details, and performance characteristics.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Hybrid Search System](#hybrid-search-system)
- [Database Design](#database-design)
- [Vector Embeddings](#vector-embeddings)
- [Content Extraction](#content-extraction)
- [Performance Characteristics](#performance-characteristics)
- [Smart Mode Architecture](#smart-mode-architecture)
- [Technology Choices](#technology-choices)

---

## Architecture Overview

### System Components

```
┌──────────────────────────────────────────────────────────┐
│                     MCP Client                            │
│                  (Claude Desktop)                         │
└────────────────────┬─────────────────────────────────────┘
                     │ stdio (JSON-RPC)
┌────────────────────▼─────────────────────────────────────┐
│                  MCP Server                               │
│                 (server.py)                               │
└────────────────────┬─────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
┌───────────┐  ┌──────────┐  ┌──────────────┐
│  Content  │  │ Embedding│  │   Search     │
│  Fetcher  │  │ Service  │  │  Service     │
│           │  │          │  │              │
└─────┬─────┘  └────┬─────┘  └──────┬───────┘
      │             │                │
      │             │         ┌──────┴───────┐
      │             │         │              │
      ▼             ▼         ▼              ▼
┌──────────┐  ┌──────────────────────┐  ┌─────────────┐
│   Web    │  │sentence-transformers │  │  DuckDB     │
│  Pages   │  │ (all-MiniLM-L6-v2)   │  │ (metadata)  │
└──────────┘  └──────────────────────┘  └─────────────┘
                     │                        │
                     ▼                        │
              ┌──────────────┐               │
              │   LanceDB    │◄──────────────┘
              │  (vectors)   │
              └──────────────┘
```

### Data Flow

**Saving a Bookmark:**
1. User provides URL + optional note/tags
2. ContentFetcher downloads and extracts content
3. EmbeddingService generates 384-dim vector
4. BookmarkService orchestrates storage:
   - Metadata → DuckDB
   - Vector → LanceDB
5. Return success + bookmark ID

**Searching Bookmarks:**
1. User provides query + optional filters
2. EmbeddingService converts query to vector
3. SearchService orchestrates:
   - Vector similarity search (LanceDB)
   - Apply SQL filters (DuckDB)
   - Merge and rank results
4. Return top N matches with scores

---

## Hybrid Search System

### Why Hybrid?

Pure vector search is great for semantic similarity but lacks:
- Exact filtering (domain, tags, dates)
- Structured metadata queries
- Join capabilities

Pure SQL is great for structure but lacks:
- Semantic understanding
- Fuzzy matching
- Concept-based search

**Solution:** Combine both.

### Implementation

```python
def search(query, filters):
    # 1. Generate query embedding (384 dimensions)
    query_vector = embedding_service.generate(query)

    # 2. Vector search in LanceDB (over-fetch)
    vector_results = lancedb.search(query_vector, limit=limit * 5)
    candidate_ids = [r.id for r in vector_results]

    # 3. SQL filtering in DuckDB
    sql = """
        SELECT * FROM bookmarks
        WHERE id IN (?)
        AND domain = ? (if domain filter)
        AND tags && ? (if tag filter)
        AND created >= ? (if from_date filter)
        AND created <= ? (if to_date filter)
    """
    filtered = duckdb.execute(sql, filters)

    # 4. Re-rank by vector score
    results = merge_and_rank(filtered, vector_results)

    # 5. Return top N
    return results[:limit]
```

### Why Over-Fetch?

```python
# Over-fetch from vector DB to account for filtering
vector_results = lancedb.search(query_vector, limit=limit * 5)
```

**Reason:** SQL filters might eliminate many vector results.

**Example:**
- Request: 10 results
- Vector search: 50 candidates (5x over-fetch)
- After SQL filters: 12 remaining
- Return: Top 10

If we fetched only 10 from vector DB, filters might leave us with 2-3 results.

### Performance Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Vector-only** | Fast, semantic | No exact filtering |
| **SQL-only** | Precise filters | No semantic understanding |
| **Hybrid (current)** | Best of both | Slightly slower, complex |

Hybrid adds ~50ms latency but provides superior results.

---

## Database Design

### DuckDB Schema

```sql
CREATE TABLE bookmarks (
    id TEXT PRIMARY KEY,              -- bkm_<uuid>
    url TEXT NOT NULL,                -- Original URL
    normalized_url TEXT,              -- Cleaned URL for deduplication
    domain TEXT,                      -- e.g., "github.com"
    title TEXT,                       -- Page title
    description TEXT,                 -- Meta description
    note TEXT,                        -- User's note
    manual_tags TEXT[],               -- User-provided tags
    created TIMESTAMP DEFAULT NOW(),  -- Save time
    updated TIMESTAMP DEFAULT NOW(),  -- Last update

    -- Smart Mode fields (optional)
    content_markdown TEXT,            -- Full content as Markdown
    short_summary TEXT,               -- 1-2 sentence summary
    long_summary TEXT,                -- 1 paragraph summary
    auto_tags TEXT[],                 -- LLM-generated tags
    topic TEXT,                       -- Classification (AI, DevOps, etc.)

    -- Metadata
    fetch_success BOOLEAN,            -- Content fetch status
    error_message TEXT                -- Error if fetch failed
);

CREATE INDEX idx_domain ON bookmarks(domain);
CREATE INDEX idx_created ON bookmarks(created);
CREATE INDEX idx_topic ON bookmarks(topic);
```

**Design Decisions:**

1. **TEXT[] for tags:** PostgreSQL-style arrays (DuckDB supports)
   - Easy to query: `tags && ['python', 'tutorial']`
   - No junction table needed

2. **Normalized URL:** For duplicate detection
   - Removes query params, fragments
   - Lowercased
   - Trailing slash normalized

3. **Separate summaries:** Short vs long
   - Short: Quick reference
   - Long: Detailed context
   - Both indexed for search

4. **Topic as TEXT:** Not foreign key
   - Fixed set of topics
   - Simple, no joins
   - Easy to filter

### LanceDB Schema

```python
# Vector table
{
    "id": "bkm_<uuid>",           # Same as DuckDB
    "vector": [0.123, -0.456, ...], # 384 dimensions
    "text": "concatenated content"  # For reference
}
```

**Why so simple?**
- LanceDB is specialized for vectors
- Metadata stays in DuckDB
- Join on ID when needed

**What gets embedded:**
```python
def generate_embedding_text(bookmark):
    parts = [
        bookmark.title,
        bookmark.description,
        bookmark.note or "",
        bookmark.short_summary or "",  # Smart Mode
        " ".join(bookmark.manual_tags),
        " ".join(bookmark.auto_tags or []),  # Smart Mode
    ]
    return " ".join(p for p in parts if p)
```

All text that describes the bookmark goes into the embedding.

---

## Vector Embeddings

### Model: all-MiniLM-L6-v2

**Specifications:**
- Dimensions: 384
- Model size: ~80MB
- Speed: ~500 sentences/second (CPU)
- Quality: 0.68 on STS benchmark

**Why this model?**

| Model | Dims | Size | Speed | Quality |
|-------|------|------|-------|---------|
| all-MiniLM-L6-v2 | 384 | 80MB | Fast | Good |
| all-mpnet-base-v2 | 768 | 420MB | Slow | Better |
| paraphrase-multilingual | 384 | 135MB | Fast | Good (multilingual) |

**Trade-off:** MiniLM offers best balance of speed/size/quality for most users.

### Embedding Process

```python
from sentence_transformers import SentenceTransformer

# Load model (cached after first use)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embedding
text = "authentication tutorial using OAuth and JWT"
vector = model.encode(text, convert_to_numpy=True)

# Result: numpy array of 384 floats
# vector.shape = (384,)
# Each dimension captures a semantic feature
```

### Similarity Search

```python
# In LanceDB
table.search(query_vector)
    .metric("cosine")  # Cosine similarity
    .limit(50)         # Top 50 results
    .to_list()

# Cosine similarity range: -1 to 1
# Higher = more similar
# Typical thresholds:
# > 0.7 = very similar
# 0.5-0.7 = related
# < 0.5 = different topics
```

### Why Cosine Similarity?

Alternatives:
- **Euclidean distance:** Sensitive to magnitude
- **Dot product:** No normalization
- **Cosine:** Angle-based, normalized ✓

Cosine is standard for text embeddings because:
- Normalized (vectors are length-independent)
- Intuitive (0° = identical, 90° = unrelated)
- Fast to compute

---

## Content Extraction

### Pipeline

```python
URL → HTTP Request → HTML → Readability → Markdown → Storage
```

### Libraries Used

1. **requests:** HTTP fetching
   - Timeout: 30s (configurable)
   - User-Agent: Custom (avoid blocking)
   - SSL verification: Yes

2. **BeautifulSoup4:** HTML parsing
   - Extract `<title>`
   - Extract `<meta name="description">`
   - Find main content

3. **readability-lxml:** Content extraction
   - Removes ads, nav, footer
   - Identifies main article
   - Preserves structure

4. **markdownify:** HTML → Markdown (Smart Mode)
   - Preserves headings, lists, code blocks
   - Removes styling
   - Clean, searchable text

### Example

**Input:** `https://react.dev/learn`

**Extraction:**
```python
{
    "title": "Learn React",
    "description": "A JavaScript library for building user interfaces",
    "domain": "react.dev",
    "content_html": "<div><h1>Learn React</h1><p>Welcome...</p></div>",
    "content_markdown": "# Learn React\n\nWelcome...",
    "word_count": 2847
}
```

### Error Handling

```python
try:
    response = requests.get(url, timeout=30)
except requests.Timeout:
    return ContentResult(fetch_success=False, error="Timeout")
except requests.ConnectionError:
    return ContentResult(fetch_success=False, error="Connection failed")
except Exception as e:
    return ContentResult(fetch_success=False, error=str(e))
```

Bookmark still saves with partial data (title from URL, no content).

---

## Performance Characteristics

### Benchmarks

**Hardware:** MacBook Pro M1, 16GB RAM

#### Save Bookmark

| Mode | Time | Breakdown |
|------|------|-----------|
| **Core Mode** | ~1.5s | Fetch (1s) + Embed (0.3s) + Store (0.2s) |
| **Smart Mode** | ~6s | Fetch (1s) + LLM (4.5s) + Embed (0.3s) + Store (0.2s) |

**Bottleneck:** LLM API call in Smart Mode (network latency + generation).

#### Search

| Collection Size | Time |
|-----------------|------|
| 100 bookmarks | ~80ms |
| 1,000 bookmarks | ~120ms |
| 10,000 bookmarks | ~350ms |
| 100,000 bookmarks | ~2s |

**Breakdown:**
- Query embedding: 50ms (constant)
- Vector search: 30-200ms (scales with size)
- SQL filtering: 10-50ms (indexed)
- Merge/rank: 10ms

#### Memory Usage

| Component | Memory |
|-----------|--------|
| Embedding model | ~250MB |
| DuckDB (1K bookmarks) | ~10MB |
| LanceDB (1K bookmarks) | ~5MB |
| Application overhead | ~50MB |
| **Total (1K bookmarks)** | **~315MB** |

Scales linearly with bookmark count.

#### Disk Usage

| Component | Size (1K bookmarks) |
|-----------|---------------------|
| DuckDB file | ~2MB |
| LanceDB directory | ~1.5MB |
| Model cache | ~80MB (one-time) |
| **Total** | **~83.5MB** |

### Optimization Strategies

**For Large Collections:**
1. **Batch embedding:** Process multiple bookmarks at once
2. **Lazy model loading:** Load on first use
3. **Index caching:** Keep common indexes in memory
4. **Limit results:** Default to top 10, not 100

**For Slow Networks:**
1. **Fetch timeout:** 30s (prevents hanging)
2. **Retry logic:** 2 retries with backoff
3. **Partial saves:** Save without content if fetch fails

**For Smart Mode:**
1. **Stream responses:** Show progress during LLM call
2. **Parallel requests:** Batch multiple bookmarks
3. **Cache model calls:** Reuse for similar content

---

## Smart Mode Architecture

### LLM Integration (litellm)

```python
from litellm import completion

response = completion(
    model="claude-3-haiku-20240307",
    messages=[{
        "role": "user",
        "content": prompt
    }],
    temperature=0.3  # Low for consistency
)
```

**Why litellm?**
- Supports 100+ LLM providers
- Unified interface (OpenAI, Anthropic, etc.)
- Easy model switching
- Good error handling

### Prompt Engineering

**For Summaries:**
```
Summarize this webpage concisely:

Title: {title}
URL: {url}
Content: {content_markdown}

Provide:
1. Short summary (1-2 sentences, max 50 words)
2. Long summary (1 paragraph, max 150 words)

Format as JSON:
{
  "short_summary": "...",
  "long_summary": "..."
}
```

**For Tags:**
```
Extract 3-5 relevant tags for this webpage:

Title: {title}
Content: {content_markdown}

Requirements:
- Lowercase, no spaces
- Technology names, concepts, topics
- Specific (not "interesting" or "cool")

Return as JSON array: ["tag1", "tag2", "tag3"]
```

**For Topics:**
```
Classify this webpage into ONE category:

AI, Cloud, Programming, Data, Security, DevOps, Design, Business, Science, Other

Content: {title} - {short_summary}

Return only the category name.
```

### Cost Analysis

**Claude Haiku (recommended):**
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens

**Typical bookmark:**
- Input: ~1,500 tokens (content)
- Output: ~200 tokens (summary + tags)
- Cost: (1500 × $0.25 + 200 × $1.25) / 1M = $0.0006

**1,000 bookmarks = $0.60** (very affordable)

**GPT-4o-mini:**
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens
- Same bookmark: $0.00034
- 1,000 bookmarks = $0.34

---

## Technology Choices

### Why DuckDB?

**Alternatives considered:**
- SQLite: Good, but DuckDB is faster for analytics
- PostgreSQL: Overkill, requires server
- In-memory dict: No persistence, no SQL

**Why DuckDB won:**
- Embedded (no server)
- Fast analytics (OLAP optimized)
- Full SQL support
- Array types (for tags)
- Small binary (~30MB)

### Why LanceDB?

**Alternatives considered:**
- FAISS: Fast but requires Python bindings
- Chroma: Good but more complex
- Qdrant: Requires server
- pgvector: Requires PostgreSQL

**Why LanceDB won:**
- Serverless (just a directory)
- Built on Apache Arrow (fast)
- Good Python API
- Active development
- MIT license

### Why sentence-transformers?

**Alternatives considered:**
- OpenAI embeddings: Cost per request
- Cohere embeddings: Cost per request
- Custom model: Training complexity

**Why sentence-transformers won:**
- 100% local, free
- Good quality
- Fast inference
- Easy to use
- Large model ecosystem

### Why FastMCP?

**Alternatives:**
- Anthropic MCP SDK (official): More boilerplate
- Custom implementation: Reinvent wheel

**Why FastMCP won:**
- Minimal boilerplate
- Decorator-based (clean)
- Built on official SDK
- Good developer experience

---

## Scalability Considerations

### Current Limits

- **Bookmarks:** 100K+ (tested)
- **Concurrent users:** 1 (stdio transport)
- **Database size:** Limited by disk
- **Memory:** ~250MB + 5KB per bookmark

### Scaling Beyond

**For millions of bookmarks:**
1. Switch to persistent vector DB (Qdrant, Milvus)
2. Partition by time (recent vs archive)
3. Use approximate search (faster, less accurate)

**For multi-user:**
1. Switch to HTTP transport
2. Add authentication
3. Separate databases per user

**For real-time sync:**
1. Add change detection
2. Implement incremental updates
3. Use pub/sub for notifications

Currently optimized for single-user local use case.

---

## Security Considerations

### Threat Model

**In scope:**
- URL validation (prevent SSRF)
- SQL injection (parameterized queries)
- XSS in content (Markdown escaping)
- File path traversal (validated paths)

**Out of scope (by design):**
- Multi-user authentication (single-user)
- Network security (local only)
- Data encryption at rest (local filesystem)

### Mitigations

1. **URL validation:**
   ```python
   if not url.startswith(('http://', 'https://')):
       raise ValueError("Invalid URL scheme")
   ```

2. **Parameterized queries:**
   ```python
   cursor.execute("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
   ```

3. **Content sanitization:**
   - HTML stripped before Markdown conversion
   - Special chars escaped in responses

4. **Path validation:**
   ```python
   db_path.resolve().is_relative_to(base_dir)  # Prevent traversal
   ```

---

## Future Optimizations

### Planned Improvements

1. **Incremental embeddings:** Only re-embed changed text
2. **Batch operations:** Save/search multiple at once
3. **Background processing:** Async content fetch
4. **Smart caching:** LRU cache for frequent queries
5. **Index optimization:** Analyze query patterns

### Research Ideas

1. **Multi-vector search:** Separate embeddings for title/content
2. **Query expansion:** Use LLM to suggest related terms
3. **Personalized ranking:** Learn user preferences over time
4. **Collaborative filtering:** "Users who saved X also saved Y"

---

## Debugging & Profiling

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uvx bookmark-lens
```

### Profile Search Performance

```python
import time

start = time.time()
results = search_service.search(query)
print(f"Search took {time.time() - start:.2f}s")
```

### Check Database Sizes

```bash
# DuckDB
ls -lh data/bookmark_lens.db

# LanceDB
du -sh data/embeddings.lance
```

### Monitor Memory

```bash
# While running
ps aux | grep bookmark-lens

# Or use
htop
```

---

## Contributing to Architecture

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code organization
- Adding new features
- Performance testing
- Documentation standards

---

**Questions?** Open an issue on GitHub or check [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
