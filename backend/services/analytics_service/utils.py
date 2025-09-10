"""
Utility functions for analytics service.
"""

import asyncio
from typing import Any, Callable


async def run_sync_in_executor(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Run a synchronous function in an executor with cleaner syntax.
    
    Args:
        func: The synchronous function to run
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function call
    """
    if kwargs:
        # If we have keyword arguments, we need to use a lambda to handle them
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: func(*args, **kwargs)
        )
    else:
        # For positional-only arguments, we can pass directly
        return await asyncio.get_event_loop().run_in_executor(None, func, *args)
