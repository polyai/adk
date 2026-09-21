"""Builder-facing function decorators and their export into generated projects.

The ``func_*`` decorators are no-op stubs whose source is exported verbatim into
each project's ``_gen/decorators.py`` by :func:`export_decorators`, which looks
the decorators up via ``globals()`` — they must stay in this module.

Copyright PolyAI Limited
"""

import inspect
import os
from typing import Callable, Optional


def func_latency_control(
    delay_before_responses_start: int = 0,
    silence_after_each_response: int = 0,
    delay_responses: Optional[list[tuple[str, int]]] = None,
    randomize: bool = False,
) -> Callable:
    """Configure latency control for a function.

    Args:
        delay_before_responses_start: Seconds to wait before the first delay
            response is played. Must be between 0 and 10.
        silence_after_each_response: Seconds of silence to insert after each
            delay response. Must be between 0 and 10.
        delay_responses: A list of (message, duration_ms) tuples that are
            played while the function is executing.
        randomize: When True, shuffle delay_responses order on each function
            invocation. Timing slots are preserved (first uses
            delay_before_responses_start; later slots use
            silence_after_each_response).
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


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


def export_decorators(decorators: list[str], base_path: str, filepath: str = "_gen/decorators.py"):
    """Export the decorator functions."""
    filepath = os.path.join(base_path, filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(
            "# flake8: noqa\n# <AUTO GENERATED>\n" + "from typing import Callable, Optional\n\n"
        )
        f.write(f"__all__ = {decorators!r}\n\n")

        for decorator in decorators:
            f.write(inspect.getsource(globals()[decorator]))
            f.write("\n\n")
