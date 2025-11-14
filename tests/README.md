# Tests

## Overview

Two test suites are provided:

1. **test_simple.py** - Standalone tests (no dependencies)
2. **test_integration.py** - Full pytest suite (requires pytest)

Both test Core Mode (no LLM) with mocked URL fetching.

## Quick Start

### Simple Tests (Recommended)

```bash
cd /path/to/bookmark-lens
python3 tests/test_simple.py
```

No dependencies needed beyond the main project requirements.

### Full Test Suite

```bash
pip install pytest
pytest tests/test_integration.py -v
```

## What's Tested

### 1. Save Bookmarks
- Single bookmark save
- Multiple bookmarks
- Metadata extraction (title, description, domain)
- Tag assignment
- Note storage

### 2. Semantic Search
- Basic semantic search
- Domain filtering
- Tag filtering
- Relevance scoring
- No results handling

### 3. Statistics
- Total bookmark count
- Count by domain
- Count by tag
- Count by date range
- Combined filters

### 4. Update Operations
- Update notes
- Replace tags
- Append tags

### 5. Delete Operations
- Delete bookmark
- Verify deletion
- Delete non-existent bookmark

## Mock Data

Tests use mocked URL fetching with predefined content:

```python
MOCK_CONTENT = {
    "https://github.com/anthropics/mcp": {
        "title": "Model Context Protocol",
        "description": "A protocol for connecting AI assistants...",
        "domain": "github.com"
    },
    # ... more URLs
}
```

This allows testing without:
- Network requests
- External dependencies
- Rate limiting
- Content changes

## Test Coverage

- ✅ Save bookmarks (with mocked content)
- ✅ Semantic search
- ✅ Search filters (domain, tags, dates)
- ✅ Get bookmark by ID
- ✅ Update bookmarks
- ✅ Delete bookmarks
- ✅ Statistics queries
- ✅ Core Mode (no LLM)

Not tested (requires real setup):
- ❌ Smart Mode (LLM features)
- ❌ Real URL fetching
- ❌ MCP server integration

## Example Output

```
============================================================
BOOKMARK-LENS INTEGRATION TESTS (Core Mode - No LLM)
============================================================

=== Test 1: Save Bookmarks ===
✓ Saved: Model Context Protocol (github.com)
✓ Saved: Amazon Bedrock - AWS (aws.amazon.com)
✓ Saved: Python Tutorial (python.org)
✓ Saved: PyTorch Deep Learning Framework (github.com)
✓ All 4 bookmarks saved successfully

=== Test 2: Semantic Search ===
Query: 'AI assistant protocol'
Found 4 results:
  - Model Context Protocol (score: 0.654)
  - Amazon Bedrock - AWS (score: 0.521)
  - PyTorch Deep Learning Framework (score: 0.412)
✓ Semantic search working

=== Test 3: Search with Filters ===
Query: 'AI' on github.com
Found 2 results:
  - Model Context Protocol (https://github.com/anthropics/mcp)
  - PyTorch Deep Learning Framework (https://github.com/pytorch/pytorch)
✓ Domain filter working

... (more tests)

============================================================
RESULTS: 7 passed, 0 failed
============================================================
```

## Adding New Tests

### Simple Test Pattern

```python
def test_my_feature():
    """Test description."""
    print("\n=== Test: My Feature ===")
    services = setup_services()
    
    try:
        # Test code here
        assert something is True
        print("✓ Test passed")
    finally:
        cleanup(services)
```

### Pytest Pattern

```python
def test_my_feature(services):
    """Test description."""
    # Test code here
    assert something is True
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run tests
  run: python3 tests/test_simple.py
```

Or with pytest:

```yaml
- name: Run tests
  run: |
    pip install pytest
    pytest tests/test_integration.py -v
```
