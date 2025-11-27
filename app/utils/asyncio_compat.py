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
    
    Examples:
        >>> async def fetch_data():
        ...     return "data"
        >>> 
        >>> result = run_async(fetch_data())
        >>> print(result)
        'data'
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
    
    except Exception as e:
        logger.error(f"Error running async coroutine: {e}", exc_info=True)
        raise


async def run_in_executor(func, *args, **kwargs):
    """
    Run synchronous function in executor to avoid blocking
    
    Args:
        func: Synchronous function
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Function result
    
    Examples:
        >>> def blocking_task(x):
        ...     time.sleep(1)
        ...     return x * 2
        >>> 
        >>> result = await run_in_executor(blocking_task, 5)
        >>> print(result)
        10
    """
    loop = asyncio.get_event_loop()
    
    # Use functools.partial for kwargs
    from functools import partial
    
    if kwargs:
        func = partial(func, **kwargs)
    
    return await loop.run_in_executor(None, func, *args)