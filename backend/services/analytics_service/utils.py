"""
Utility Functions for Analytics Service.

This module provides common utility functions used throughout the analytics service,
including asynchronous execution helpers and shared processing utilities.
"""

import asyncio
from typing import Any, Callable


async def run_sync_in_executor(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Execute synchronous function asynchronously using thread executor.
    
    Provides a cleaner syntax for running CPU-bound or blocking operations
    in a separate thread without blocking the main event loop.
    
    Args:
        func: The synchronous function to execute
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
