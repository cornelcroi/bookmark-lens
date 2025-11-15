"""Handlers for search and tag operations."""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from mcp.types import TextContent

if TYPE_CHECKING:
    from ..services.search_service import SearchService
    from ..database.duckdb_client import DuckDBClient

logger = logging.getLogger(__name__)


async def handle_search_bookmarks(
    arguments: dict,
    search_service: "SearchService"
) -> list[TextContent]:
    """Handle search_bookmarks tool call."""
    from ..models.bookmark import BookmarkSearchQuery
    
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
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
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


async def handle_list_tags(
    arguments: dict,
    duckdb_client: "DuckDBClient"
) -> list[TextContent]:
    """Handle list_tags tool call."""
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
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Failed to list tags: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, indent=2)
        )]
