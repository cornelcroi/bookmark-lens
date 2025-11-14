"""
Entry point for running bookmark-lens as a module.

Usage: python -m bookmark_lens
"""

from .server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
