# flake8: noqa
# <AUTO GENERATED>
from typing import Callable, Optional

__all__ = ['func_parameter', 'func_description', 'func_latency_control']

def func_parameter(
    name: str,
    description: str,
) -> Callable:
    """Configure function parameter.

    Args:
        name: Name of the given parameter.
        description: Description of the given parameter (provided to the LLM).
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def func_description(
    description: str,
) -> Callable:
    """Set the description for the target function.

    Args:
        description: Description of the target function (provided to the LLM).
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def func_latency_control(
    delay_before_responses_start: int = 0,
    silence_after_each_response: int = 0,
    delay_responses: Optional[list[tuple[str, int]]] = None,
) -> Callable:
    """Configure latency control for a function.

    Args:
        delay_before_responses_start: Seconds to wait before the first delay
            response is played. Must be between 0 and 10.
        silence_after_each_response: Seconds of silence to insert after each
            delay response. Must be between 0 and 10.
        delay_responses: A list of (message, duration_ms) tuples that are
            played while the function is executing.
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


