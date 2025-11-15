"""Tool handlers for bookmark-lens MCP server."""

from .bookmark_handlers import (
    handle_save_bookmark,
    handle_get_bookmark,
    handle_update_bookmark,
    handle_delete_bookmark,
)
from .search_handlers import (
    handle_search_bookmarks,
    handle_list_tags,
)
from .stats_handlers import (
    handle_get_bookmark_stats,
)
from .content_handlers import (
    handle_get_bookmark_content,
)

__all__ = [
    "handle_save_bookmark",
    "handle_get_bookmark",
    "handle_update_bookmark",
    "handle_delete_bookmark",
    "handle_search_bookmarks",
    "handle_list_tags",
    "handle_get_bookmark_stats",
    "handle_get_bookmark_content",
]
