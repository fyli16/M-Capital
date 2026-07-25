"""Custom persistence helpers: UUIDv7 generation and shared column types."""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (RFC 9562): 48-bit Unix-ms timestamp + 74 random bits.

    Time-sortable primary keys avoid the index fragmentation and write hotspots of
    random UUIDv4 while retaining global uniqueness — ideal for high-insert tables
    like ``agent_runs`` and ``debate_turns``.
    """
    unix_ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")  # 80 random bits

    value = unix_ts_ms << 80
    value |= 0x7 << 76                 # version 7
    value |= ((rand >> 62) & 0xFFF) << 64  # rand_a (12 bits)
    value |= 0b10 << 62                # variant (RFC 4122)
    value |= rand & ((1 << 62) - 1)   # rand_b (62 bits)
    return uuid.UUID(int=value)
