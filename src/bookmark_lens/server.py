"""
MCP server for bookmark-lens.

Provides tools for saving, searching, and managing bookmarks with semantic search.
"""

import asyncio
import logging
from typing import Optional

from mcp.server import Server
from mcp.types import Tool, TextContent, Prompt, PromptMessage

from .config import load_config, Config
from .database.duckdb_client import DuckDBClient
from .database.lancedb_client import LanceDBClient
from .services.content_fetcher import ContentFetcher
from .services.embedding_service import EmbeddingService
from .services.bookmark_service import BookmarkService
from .services.search_service import SearchService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create MCP server
app = Server("bookmark-lens")

# Global service instances (initialized in main)
config: Optional[Config] = None
duckdb_client: Optional[DuckDBClient] = None
lancedb_client: Optional[LanceDBClient] = None
bookmark_service: Optional[BookmarkService] = None
search_service: Optional[SearchService] = None


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Register all available MCP tools."""
    return [
        Tool(
            name="save_bookmark",
            description="""Save a bookmark to the user's bookmark collection.

IMPORTANT: Use this tool whenever the user asks to:
- "Save this URL"
- "Bookmark this"
- "Add to bookmarks"
- "Remember this page"
- Or any similar request to save a URL

After saving, consider helping the user by:
1. Calling get_bookmark_content(id) to fetch the article
2. Summarizing the content for them
3. Calling update_bookmark(id, note=summary) to save the summary

This provides a helpful summary without requiring an API key.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to bookmark"
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional note explaining why you saved this or context"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to categorize this bookmark"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="search_bookmarks",
            description="""Search the user's bookmark collection using semantic search.

IMPORTANT: Use this tool whenever the user asks to:
- "Find bookmarks about..."
- "Search my bookmarks for..."
- "Show me bookmarks..."
- "Do I have any bookmarks about..."
- Or any similar request to find saved bookmarks

Supports semantic search (meaning-based) with optional filters for domain, tags, and dates.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (semantic search)"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain (e.g., 'github.com')"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Filter bookmarks after this date (ISO 8601 format: '2024-11-14T00:00:00Z')"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "Filter bookmarks before this date (ISO 8601 format: '2024-11-14T23:59:59Z')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (1-100)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_bookmark",
            description="Get full details about a specific bookmark by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The bookmark ID"
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="update_bookmark",
            description="Update note and/or tags for an existing bookmark",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The bookmark ID"
                    },
                    "note": {
                        "type": "string",
                        "description": "New note (replaces existing)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to add or replace"
                    },
                    "tag_mode": {
                        "type": "string",
                        "enum": ["replace", "append"],
                        "description": "Whether to replace or append tags",
                        "default": "replace"
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="delete_bookmark",
            description="Delete a bookmark and all its associated data",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The bookmark ID to delete"
                    }
                },
                "required": ["id"]
            }
        ),
        Tool(
            name="list_tags",
            description="List all tags with their usage counts",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_bookmark_stats",
            description="Get statistics about your bookmark collection with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "stat_type": {
                        "type": "string",
                        "enum": ["total", "by_domain", "by_topic", "by_tag", "by_date"],
                        "description": "Type of statistics: 'total' (count), 'by_domain' (top domains), 'by_topic' (topic breakdown), 'by_tag' (tag distribution), 'by_date' (activity over time)",
                        "default": "total"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Filter by domain (e.g., 'github.com')"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Filter by topic"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Filter bookmarks after this date (ISO 8601 format)"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "Filter bookmarks before this date (ISO 8601 format)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "For 'by_*' stats, limit to top N results (default: 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_bookmark_content",
            description="""Get the full content of a bookmark in Markdown format.

Use this tool when the user wants to:
- Read the full article content
- Get a summary of the bookmark (you will summarize the returned content)
- Analyze or discuss the bookmark content in detail
- Quote specific parts of the article
- Get fresh content from the URL

After calling this tool, YOU should summarize or analyze the content based on what the user asked.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The bookmark ID"
                    }
                },
                "required": ["id"]
            }
        )
    ]


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="bookmark_search_guide",
            description="Guide for using bookmark-lens effectively, including natural language date parsing"
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> PromptMessage:
    """Get prompt content."""
    if name == "bookmark_search_guide":
        return PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text="""You are a bookmark management assistant with access to the bookmark-lens MCP server.

IMPORTANT: You HAVE the ability to manage bookmarks through the available tools. When users ask to save, search, or manage bookmarks, USE THE TOOLS.

Your capabilities:
1. Save bookmarks - Use save_bookmark when users say "save", "bookmark", "add to bookmarks", "remember this"
2. Search bookmarks - Use search_bookmarks when users say "find", "search", "show me bookmarks"
3. Get bookmark details - Use get_bookmark to retrieve full information
4. Update bookmarks - Use update_bookmark to modify notes or tags
5. Delete bookmarks - Use delete_bookmark to remove bookmarks
6. List tags - Use list_tags to show all available tags
7. Get statistics - Use get_bookmark_stats for analytics
8. Get content - Use get_bookmark_content to fetch and summarize articles

Common User Requests:
- "Save this URL" → Use save_bookmark
- "Bookmark this page" → Use save_bookmark
- "Add to my bookmarks" → Use save_bookmark
- "Find bookmarks about X" → Use search_bookmarks
- "Show me my bookmarks" → Use search_bookmarks with broad query
- "Summarize this bookmark" → Use get_bookmark_content then summarize

Date Conversion Rules:
- "today" → current date at 00:00:00Z
- "yesterday" → current date - 1 day at 00:00:00Z
- "last week" → current date - 7 days at 00:00:00Z
- "last month" → current date - 30 days at 00:00:00Z
- "this week" → 7 days ago to now
- Always use ISO 8601 format: "2024-11-14T00:00:00Z"
- For date ranges, set from_date to the start and to_date to now (or omit to_date)

Search Workflow:
1. Parse user query for filters (dates, domain, tags)
2. Extract semantic search text (the "what" they're looking for)
3. Convert any natural language dates to ISO format
4. Call search_bookmarks with proper parameters
5. Interpret similarity scores (>0.7 = highly relevant, >0.5 = relevant, <0.5 = weak match)
6. Present results clearly with titles and relevance

Filter Extraction Examples:
- "bookmarks from last week" → from_date = 7 days ago
- "find articles about AI from github.com" → query="articles about AI", domain="github.com"
- "show me bookmarks tagged as python" → query="python", tags=["python"]
- "bookmarks I saved yesterday about databases" → query="databases", from_date = yesterday

Rules:
- Always convert natural language dates to ISO format yourself (don't ask the user)
- Use semantic search for "find bookmarks about X" (the query parameter)
- Use domain filter for "from github.com" or "on example.com"
- Use tag filter for "tagged as X" or "with tag Y"
- Combine filters when appropriate
- If search returns no results, suggest a broader query or different filters
- When saving bookmarks, encourage users to add notes (improves search relevance)
- Similarity scores help gauge relevance - mention when results are highly relevant

Workflow Examples:

Example 1 - Save with context:
User: "Save https://example.com/article, this is about machine learning"
You: Call save_bookmark with url and note="this is about machine learning"

Example 2 - Search with date:
User: "Find bookmarks from last week about Python"
You: Calculate from_date (7 days ago), call search_bookmarks with query="Python", from_date="2024-11-07T00:00:00Z"

Example 3 - Search with domain:
User: "Show me GitHub bookmarks about React"
You: Call search_bookmarks with query="React", domain="github.com"

Example 4 - Update bookmark:
User: "Add tag 'tutorial' to bookmark abc123"
You: Call update_bookmark with id="abc123", tags=["tutorial"], tag_mode="append"
"""
            )
        )
    
    raise ValueError(f"Unknown prompt: {name}")


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from MCP clients."""
    try:
        if name == "save_bookmark":
            return await handle_save_bookmark(arguments)
        elif name == "search_bookmarks":
            return await handle_search_bookmarks(arguments)
        elif name == "get_bookmark":
            return await handle_get_bookmark(arguments)
        elif name == "update_bookmark":
            return await handle_update_bookmark(arguments)
        elif name == "delete_bookmark":
            return await handle_delete_bookmark(arguments)
        elif name == "list_tags":
            return await handle_list_tags(arguments)
        elif name == "get_bookmark_stats":
            return await handle_get_bookmark_stats(arguments)
        elif name == "get_bookmark_content":
            return await handle_get_bookmark_content(arguments)
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    except Exception as e:
        logger.error(f"Tool error ({name}): {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def handle_save_bookmark(arguments: dict) -> list[TextContent]:
    """Handle save_bookmark tool call."""
    import json
    from .models.bookmark import BookmarkCreate
    
    # Validate input
    try:
        bookmark_create = BookmarkCreate(
            url=arguments["url"],
            note=arguments.get("note"),
            manual_tags=arguments.get("tags", []),
            source="manual"
        )
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"Invalid input: {str(e)}"
            }, indent=2)
        )]
    
    # Save bookmark
    try:
        logger.info(f"Saving bookmark: {arguments['url']}")
        bookmark = bookmark_service.save_bookmark(bookmark_create)
        
        response = {
            "success": True,
            "bookmark": {
                "id": bookmark.id,
                "url": bookmark.url,
                "title": bookmark.title,
                "description": bookmark.description,
                "tags": bookmark.tags,
                "created_at": bookmark.created_at.isoformat(),
                "note": bookmark.user_note
            },
            "message": f"Bookmark saved: {bookmark.title or bookmark.url}"
        }
        
        logger.info(f"Bookmark saved successfully: {bookmark.id}")
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Failed to save bookmark: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "message": "Failed to save bookmark"
            }, indent=2)
        )]


async def handle_search_bookmarks(arguments: dict) -> list[TextContent]:
    """Handle search_bookmarks tool call."""
    import json
    from datetime import datetime
    from .models.bookmark import BookmarkSearchQuery
    
    # Parse dates if provided
    try:
        from_date = None
        to_date = None
        
        if arguments.get("from_date"):
            from_date = datetime.fromisoformat(
                arguments["from_date"].replace("Z", "+00:00")
            )
        
        if arguments.get("to_date"):
            to_date = datetime.fromisoformat(
                arguments["to_date"].replace("Z", "+00:00")
            )
        
        search_query = BookmarkSearchQuery(
            query=arguments["query"],
            domain=arguments.get("domain"),
            tags=arguments.get("tags", []),
            topic=arguments.get("topic"),
            from_date=from_date,
            to_date=to_date,
            limit=arguments.get("limit", 10)
        )
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"Invalid search query: {str(e)}"
            }, indent=2)
        )]
    
    # Execute search
    try:
        logger.info(f"Searching: '{arguments['query']}'")
        results = search_service.search(search_query)
        
        response = {
            "success": True,
            "query": arguments["query"],
            "count": len(results),
            "results": [
                {
                    "id": r.id,
                    "url": r.url,
                    "title": r.title,
                    "description": r.description,
                    "summary": r.summary_short,
                    "tags": r.tags,
                    "topic": r.topic,
                    "created_at": r.created_at.isoformat(),
                    "relevance_score": round(r.similarity_score, 3)
                }
                for r in results
            ],
            "message": f"Found {len(results)} bookmark(s)" if results else "No bookmarks found"
        }
        
        logger.info(f"Search returned {len(results)} results")
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e),
                "message": "Search failed"
            }, indent=2)
        )]


async def handle_get_bookmark(arguments: dict) -> list[TextContent]:
    """Handle get_bookmark tool call."""
    import json
    
    bookmark_id = arguments.get("id")
    if not bookmark_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Missing required argument 'id'"
            }, indent=2)
        )]
    
    try:
        bookmark = bookmark_service.get_bookmark(bookmark_id)
        
        if not bookmark:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "message": f"Bookmark not found: {bookmark_id}"
                }, indent=2)
            )]
        
        response = {
            "success": True,
            "bookmark": {
                "id": bookmark.id,
                "url": bookmark.url,
                "domain": bookmark.domain,
                "title": bookmark.title,
                "description": bookmark.description,
                "content_text": bookmark.content_text,
                "user_note": bookmark.user_note,
                "summary_short": bookmark.summary_short,
                "summary_long": bookmark.summary_long,
                "topic": bookmark.topic,
                "tags": bookmark.tags,
                "created_at": bookmark.created_at.isoformat(),
                "updated_at": bookmark.updated_at.isoformat(),
                "source": bookmark.source
            }
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Failed to get bookmark {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
        )]


async def handle_update_bookmark(arguments: dict) -> list[TextContent]:
    """Handle update_bookmark tool call."""
    import json
    from .models.bookmark import BookmarkUpdate
    
    bookmark_id = arguments.get("id")
    if not bookmark_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Missing required argument 'id'"
            }, indent=2)
        )]
    
    # Validate update data
    try:
        update = BookmarkUpdate(
            note=arguments.get("note"),
            manual_tags=arguments.get("tags"),
            tag_mode=arguments.get("tag_mode", "replace")
        )
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"Invalid update data: {str(e)}"
            }, indent=2)
        )]
    
    # Perform update
    try:
        updated_bookmark = bookmark_service.update_bookmark(bookmark_id, update)
        
        response = {
            "success": True,
            "message": "Bookmark updated successfully",
            "bookmark": {
                "id": updated_bookmark.id,
                "url": updated_bookmark.url,
                "title": updated_bookmark.title,
                "note": updated_bookmark.user_note,
                "tags": updated_bookmark.tags,
                "updated_at": updated_bookmark.updated_at.isoformat()
            }
        }
        
        logger.info(f"Bookmark updated: {bookmark_id}")
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except ValueError as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "message": str(e)
            }, indent=2)
        )]
    except Exception as e:
        logger.error(f"Failed to update bookmark {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
        )]


async def handle_delete_bookmark(arguments: dict) -> list[TextContent]:
    """Handle delete_bookmark tool call."""
    import json
    
    bookmark_id = arguments.get("id")
    if not bookmark_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Missing required argument 'id'"
            }, indent=2)
        )]
    
    try:
        deleted = bookmark_service.delete_bookmark(bookmark_id)
        
        if deleted:
            response = {
                "success": True,
                "id": bookmark_id,
                "message": "Bookmark deleted successfully"
            }
            logger.info(f"Bookmark deleted: {bookmark_id}")
        else:
            response = {
                "success": False,
                "message": f"Bookmark not found: {bookmark_id}"
            }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Failed to delete bookmark {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
        )]


async def handle_list_tags(arguments: dict) -> list[TextContent]:
    """Handle list_tags tool call."""
    import json
    
    try:
        tags = duckdb_client.conn.execute("""
            SELECT tag, COUNT(*) as count
            FROM bookmark_tags
            GROUP BY tag
            ORDER BY count DESC, tag ASC
        """).fetchall()
        
        response = {
            "success": True,
            "count": len(tags),
            "tags": [
                {"tag": tag, "count": count}
                for tag, count in tags
            ]
        }
        
        logger.info(f"Listed {len(tags)} tags")
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Failed to list tags: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
        )]


async def handle_get_bookmark_stats(arguments: dict) -> list[TextContent]:
    """Handle get_bookmark_stats tool call."""
    import json
    from datetime import datetime
    
    stat_type = arguments.get("stat_type", "total")
    domain = arguments.get("domain")
    topic = arguments.get("topic")
    tags = arguments.get("tags", [])
    limit = arguments.get("limit", 10)
    
    # Parse dates
    from_date = None
    to_date = None
    if arguments.get("from_date"):
        from_date = datetime.fromisoformat(arguments["from_date"].replace("Z", "+00:00"))
    if arguments.get("to_date"):
        to_date = datetime.fromisoformat(arguments["to_date"].replace("Z", "+00:00"))
    
    try:
        # Build WHERE clause for filters
        where_clauses = []
        params = []
        
        if domain:
            where_clauses.append("b.domain = ?")
            params.append(domain)
        if topic:
            where_clauses.append("b.topic = ?")
            params.append(topic)
        if from_date:
            where_clauses.append("b.created_at >= ?")
            params.append(from_date)
        if to_date:
            where_clauses.append("b.created_at <= ?")
            params.append(to_date)
        if tags:
            placeholders = ",".join(["?"] * len(tags))
            where_clauses.append(f"b.id IN (SELECT bookmark_id FROM bookmark_tags WHERE tag IN ({placeholders}))")
            params.extend(tags)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Execute query based on stat_type
        if stat_type == "total":
            sql = f"SELECT COUNT(*) as total FROM bookmarks b {where_sql}"
            result = duckdb_client.conn.execute(sql, params).fetchone()
            
            response = {
                "success": True,
                "stat_type": "total",
                "total": result[0],
                "filters": {k: v for k, v in [
                    ("domain", domain),
                    ("topic", topic),
                    ("tags", tags if tags else None),
                    ("from_date", arguments.get("from_date")),
                    ("to_date", arguments.get("to_date"))
                ] if v}
            }
            
        elif stat_type == "by_domain":
            sql = f"""
                SELECT b.domain, COUNT(*) as count
                FROM bookmarks b
                {where_sql}
                GROUP BY b.domain
                ORDER BY count DESC, b.domain ASC
                LIMIT ?
            """
            results = duckdb_client.conn.execute(sql, params + [limit]).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_domain",
                "total_bookmarks": sum(count for _, count in results),
                "domains": [
                    {"domain": domain, "count": count}
                    for domain, count in results
                ],
                "filters": {k: v for k, v in [
                    ("topic", topic),
                    ("tags", tags if tags else None),
                    ("from_date", arguments.get("from_date")),
                    ("to_date", arguments.get("to_date"))
                ] if v}
            }
            
        elif stat_type == "by_topic":
            sql = f"""
                SELECT b.topic, COUNT(*) as count
                FROM bookmarks b
                {where_sql}
                GROUP BY b.topic
                ORDER BY count DESC, b.topic ASC
                LIMIT ?
            """
            results = duckdb_client.conn.execute(sql, params + [limit]).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_topic",
                "total_bookmarks": sum(count for _, count in results),
                "topics": [
                    {"topic": topic or "None", "count": count}
                    for topic, count in results
                ],
                "filters": {k: v for k, v in [
                    ("domain", domain),
                    ("tags", tags if tags else None),
                    ("from_date", arguments.get("from_date")),
                    ("to_date", arguments.get("to_date"))
                ] if v}
            }
            
        elif stat_type == "by_tag":
            # Need to join with bookmark_tags
            tag_where = where_sql.replace("b.", "bookmarks.")
            sql = f"""
                SELECT bt.tag, COUNT(DISTINCT bt.bookmark_id) as count
                FROM bookmark_tags bt
                JOIN bookmarks ON bt.bookmark_id = bookmarks.id
                {tag_where}
                GROUP BY bt.tag
                ORDER BY count DESC, bt.tag ASC
                LIMIT ?
            """
            results = duckdb_client.conn.execute(sql, params + [limit]).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_tag",
                "total_bookmarks": sum(count for _, count in results),
                "tags": [
                    {"tag": tag, "count": count}
                    for tag, count in results
                ],
                "filters": {k: v for k, v in [
                    ("domain", domain),
                    ("topic", topic),
                    ("from_date", arguments.get("from_date")),
                    ("to_date", arguments.get("to_date"))
                ] if v}
            }
            
        elif stat_type == "by_date":
            sql = f"""
                SELECT DATE_TRUNC('day', b.created_at) as date, COUNT(*) as count
                FROM bookmarks b
                {where_sql}
                GROUP BY date
                ORDER BY date DESC
                LIMIT ?
            """
            results = duckdb_client.conn.execute(sql, params + [limit]).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_date",
                "total_bookmarks": sum(count for _, count in results),
                "dates": [
                    {"date": date.isoformat(), "count": count}
                    for date, count in results
                ],
                "filters": {k: v for k, v in [
                    ("domain", domain),
                    ("topic", topic),
                    ("tags", tags if tags else None),
                    ("from_date", arguments.get("from_date")),
                    ("to_date", arguments.get("to_date"))
                ] if v}
            }
        
        logger.info(f"Stats query: {stat_type} with filters: {response.get('filters', {})}")
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
        )]


async def handle_get_bookmark_content(arguments: dict) -> list[TextContent]:
    """Handle get_bookmark_content tool call."""
    import json
    
    bookmark_id = arguments.get("id")
    if not bookmark_id:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Missing required argument 'id'"
            }, indent=2)
        )]
    
    try:
        bookmark = bookmark_service.get_bookmark(bookmark_id)
        
        if not bookmark:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "message": f"Bookmark not found: {bookmark_id}"
                }, indent=2)
            )]
        
        # Fetch fresh content from URL
        from .services.content_fetcher import ContentFetcher
        fetcher = ContentFetcher(config)
        content_result = fetcher.fetch(bookmark.url, full_content=True)
        
        if not content_result.fetch_success:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "message": f"Failed to fetch content: {content_result.error_message}"
                }, indent=2)
            )]
        
        response = {
            "success": True,
            "bookmark": {
                "id": bookmark.id,
                "url": bookmark.url,
                "title": bookmark.title or content_result.title,
                "note": bookmark.user_note
            },
            "content_markdown": content_result.content_text,
            "message": "Content fetched successfully. You can now summarize or analyze it."
        }
        
        logger.info(f"Fetched content for bookmark: {bookmark_id}")
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Failed to get bookmark content {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            }, indent=2)
        )]


async def main():
    """Initialize services and start MCP server."""
    global config, duckdb_client, lancedb_client, bookmark_service, search_service

    logger.info("Starting bookmark-lens MCP server...")

    config = load_config()
    logger.info(f"Configuration loaded: DB={config.db_path}, Model={config.embedding_model_name}")

    duckdb_client = DuckDBClient(config.db_path)
    duckdb_client.initialize_schema()
    logger.info("DuckDB initialized")

    lancedb_client = LanceDBClient(config.lance_path, config.embedding_dimension)
    lancedb_client.initialize_table()
    logger.info("LanceDB initialized")

    content_fetcher = ContentFetcher(config)
    embedding_service = EmbeddingService(config)
    logger.info("Services initialized")

    bookmark_service = BookmarkService(
        config,
        duckdb_client,
        lancedb_client,
        content_fetcher,
        embedding_service
    )

    search_service = SearchService(
        config,
        duckdb_client,
        lancedb_client,
        embedding_service
    )
    logger.info("Bookmark and search services initialized")

    # Start MCP server with stdio transport
    from mcp.server.stdio import stdio_server

    logger.info("MCP server ready, starting stdio transport...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())


def run():
    """Entry point for console script."""
    asyncio.run(main())

