"""Handlers for bookmark content operations."""

import json
import logging
from typing import TYPE_CHECKING

from mcp.types import TextContent

if TYPE_CHECKING:
    from ..services.bookmark_service import BookmarkService
    from ..services.content_fetcher import ContentFetcher

logger = logging.getLogger(__name__)


async def handle_get_bookmark_content(
    arguments: dict,
    bookmark_service: "BookmarkService",
    content_fetcher: "ContentFetcher"
) -> list[TextContent]:
    """Handle get_bookmark_content tool call."""
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
        
        if bookmark.content_markdown:
            content = bookmark.content_markdown
        elif bookmark.url:
            logger.info(f"Fetching fresh content for: {bookmark.url}")
            content_result = content_fetcher.fetch(bookmark.url)
            content = content_result.content_markdown or content_result.content_text or ""
        else:
            content = ""
        
        response = {
            "success": True,
            "bookmark": {
                "id": bookmark.id,
                "url": bookmark.url,
                "title": bookmark.title,
                "description": bookmark.description,
                "content": content
            },
            "message": "Content retrieved successfully"
        }
        
        logger.info(f"Retrieved content for bookmark: {bookmark_id}")
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Failed to get bookmark content {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, indent=2)
        )]
