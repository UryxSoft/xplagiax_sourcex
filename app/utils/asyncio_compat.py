"""
Asyncio Compatibility - Helper to run async functions from sync context
"""
import asyncio
import logging
from typing import Any, Coroutine

logger = logging.getLogger(__name__)


def run_async(coro: Coroutine) -> Any:
    """
    Run an async coroutine from sync context
    
    This is a compatibility helper for running async code
    in synchronous Flask routes.
    
    Args:
        coro: Async coroutine
    
    Returns:
        Result of the coroutine
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        
        if loop.is_running():
            # If loop is already running, create new one
            logger.warning("Event loop already running, creating new loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        else:
            return loop.run_until_complete(coro)
    
    except RuntimeError:
        # No event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()