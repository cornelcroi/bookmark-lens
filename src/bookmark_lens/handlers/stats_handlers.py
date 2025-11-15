"""Handlers for bookmark statistics and analytics."""

import json
import logging
from typing import TYPE_CHECKING
from datetime import datetime

from mcp.types import TextContent

if TYPE_CHECKING:
    from ..database.duckdb_client import DuckDBClient

logger = logging.getLogger(__name__)


async def handle_get_bookmark_stats(
    arguments: dict,
    duckdb_client: "DuckDBClient"
) -> list[TextContent]:
    """Handle get_bookmark_stats tool call."""
    stat_type = arguments.get("stat_type", "total")
    domain_filter = arguments.get("domain")
    topic_filter = arguments.get("topic")
    tags_filter = arguments.get("tags", [])
    limit = arguments.get("limit", 10)
    
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
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"Invalid date format: {str(e)}"
            }, indent=2)
        )]
    
    try:
        if stat_type == "total":
            where_clauses = []
            params = []
            
            if domain_filter:
                where_clauses.append("domain = ?")
                params.append(domain_filter)
            
            if topic_filter:
                where_clauses.append("topic = ?")
                params.append(topic_filter)
            
            if from_date:
                where_clauses.append("created_at >= ?")
                params.append(from_date)
            
            if to_date:
                where_clauses.append("created_at <= ?")
                params.append(to_date)
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"SELECT COUNT(*) as count FROM bookmarks WHERE {where_clause}"
            result = duckdb_client.conn.execute(query, params).fetchone()
            count = result[0]
            
            response = {
                "success": True,
                "stat_type": "total",
                "count": count,
                "filters": {
                    "domain": domain_filter,
                    "topic": topic_filter,
                    "from_date": from_date.isoformat() if from_date else None,
                    "to_date": to_date.isoformat() if to_date else None
                }
            }
            
        elif stat_type == "by_domain":
            where_clauses = ["domain IS NOT NULL"]
            params = []
            
            if topic_filter:
                where_clauses.append("topic = ?")
                params.append(topic_filter)
            
            if from_date:
                where_clauses.append("created_at >= ?")
                params.append(from_date)
            
            if to_date:
                where_clauses.append("created_at <= ?")
                params.append(to_date)
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"""
                SELECT domain, COUNT(*) as count
                FROM bookmarks
                WHERE {where_clause}
                GROUP BY domain
                ORDER BY count DESC, domain ASC
                LIMIT ?
            """
            params.append(limit)
            
            results = duckdb_client.conn.execute(query, params).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_domain",
                "count": len(results),
                "domains": [
                    {"domain": domain, "count": count}
                    for domain, count in results
                ]
            }
            
        elif stat_type == "by_topic":
            where_clauses = ["topic IS NOT NULL"]
            params = []
            
            if domain_filter:
                where_clauses.append("domain = ?")
                params.append(domain_filter)
            
            if from_date:
                where_clauses.append("created_at >= ?")
                params.append(from_date)
            
            if to_date:
                where_clauses.append("created_at <= ?")
                params.append(to_date)
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"""
                SELECT topic, COUNT(*) as count
                FROM bookmarks
                WHERE {where_clause}
                GROUP BY topic
                ORDER BY count DESC, topic ASC
                LIMIT ?
            """
            params.append(limit)
            
            results = duckdb_client.conn.execute(query, params).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_topic",
                "count": len(results),
                "topics": [
                    {"topic": topic, "count": count}
                    for topic, count in results
                ]
            }
            
        elif stat_type == "by_tag":
            query = """
                SELECT tag, COUNT(*) as count
                FROM bookmark_tags
                GROUP BY tag
                ORDER BY count DESC, tag ASC
                LIMIT ?
            """
            results = duckdb_client.conn.execute(query, [limit]).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_tag",
                "count": len(results),
                "tags": [
                    {"tag": tag, "count": count}
                    for tag, count in results
                ]
            }
            
        elif stat_type == "by_date":
            where_clauses = []
            params = []
            
            if domain_filter:
                where_clauses.append("domain = ?")
                params.append(domain_filter)
            
            if topic_filter:
                where_clauses.append("topic = ?")
                params.append(topic_filter)
            
            if from_date:
                where_clauses.append("created_at >= ?")
                params.append(from_date)
            
            if to_date:
                where_clauses.append("created_at <= ?")
                params.append(to_date)
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM bookmarks
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date DESC
                LIMIT ?
            """
            params.append(limit)
            
            results = duckdb_client.conn.execute(query, params).fetchall()
            
            response = {
                "success": True,
                "stat_type": "by_date",
                "count": len(results),
                "dates": [
                    {"date": str(date), "count": count}
                    for date, count in results
                ]
            }
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"Unknown stat_type: {stat_type}"
                }, indent=2)
            )]
        
        logger.info(f"Generated stats: {stat_type}")
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, indent=2)
        )]
