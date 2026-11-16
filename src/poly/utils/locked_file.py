"""Files that one poly process at a time reads or writes.

Copyright PolyAI Limited
"""

import os
from contextlib import contextmanager
from typing import BinaryIO, Iterator


def read_locked(path: str) -> bytes:
    """Read a file once no other poly process holds its lock."""
    with open(path, "rb") as f, _locked(f):
        return f.read()


@contextmanager
def open_locked(path: str) -> Iterator[BinaryIO]:
    """Open a file to read and rewrite, creating it if needed, and hold its lock meanwhile.

    The file isn't truncated on opening, so a caller can read it before rewriting it. Write
    the new content, then call ``truncate()`` to drop any old content past it.
    """
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
    with open(os.open(path, flags), "r+b") as f, _locked(f):
        yield f


@contextmanager
def _locked(f: BinaryIO) -> Iterator[None]:
    """Hold the operating system's lock on an open file, which ends if the process dies."""
    _set_lock(f, True)
    try:
        yield
    finally:
        f.flush()
        _set_lock(f, False)


def _set_lock(f: BinaryIO, locked: bool) -> None:
    if os.name == "nt":
        import msvcrt

        # Windows locks byte ranges from the current position. LK_LOCK retries for 10 seconds.
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK if locked else msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_EX if locked else fcntl.LOCK_UN)
