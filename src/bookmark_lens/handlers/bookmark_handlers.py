"""Handlers for bookmark CRUD operations."""

import json
import logging
from typing import TYPE_CHECKING

from mcp.types import TextContent

if TYPE_CHECKING:
    from ..services.bookmark_service import BookmarkService

logger = logging.getLogger(__name__)


async def handle_save_bookmark(
    arguments: dict,
    bookmark_service: "BookmarkService"
) -> list[TextContent]:
    """Handle save_bookmark tool call."""
    from ..models.bookmark import BookmarkCreate
    
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
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
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


async def handle_get_bookmark(
    arguments: dict,
    bookmark_service: "BookmarkService"
) -> list[TextContent]:
    """Handle get_bookmark tool call."""
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
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Failed to get bookmark {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, indent=2)
        )]


async def handle_update_bookmark(
    arguments: dict,
    bookmark_service: "BookmarkService"
) -> list[TextContent]:
    """Handle update_bookmark tool call."""
    from ..models.bookmark import BookmarkUpdate
    
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
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except ValueError as e:
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "message": str(e)}, indent=2)
        )]
    except Exception as e:
        logger.error(f"Failed to update bookmark {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, indent=2)
        )]


async def handle_delete_bookmark(
    arguments: dict,
    bookmark_service: "BookmarkService"
) -> list[TextContent]:
    """Handle delete_bookmark tool call."""
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
        
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Failed to delete bookmark {bookmark_id}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, indent=2)
        )]
