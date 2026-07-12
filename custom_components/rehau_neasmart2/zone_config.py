"""Zone topology parsing for the Rehau Neasmart 2.0 integration."""

from __future__ import annotations

from .const import MAX_BASES, MAX_ZONES, MAX_ZONES_PER_BASE


def parse_zone_entry(entry: str, position: int) -> tuple[int, int, str]:
    """Parse one legacy name or explicit base.channel:name entry."""
    entry = entry.strip()
    if not entry:
        raise ValueError("zone entries must include a name")

    if ":" not in entry:
        if not 0 <= position < MAX_ZONES:
            raise ValueError(f"zone position must be between 1 and {MAX_ZONES}")
        return (
            (position // MAX_ZONES_PER_BASE) + 1,
            (position % MAX_ZONES_PER_BASE) + 1,
            entry,
        )

    address, name = entry.split(":", 1)
    if not name.strip():
        raise ValueError("explicit zone entries must include a name")

    address_parts = address.strip().split(".")
    if len(address_parts) != 2:
        raise ValueError("explicit zone address must use base.channel:name")

    try:
        base_id, channel_id = (int(part) for part in address_parts)
    except ValueError as err:
        raise ValueError(
            "explicit zone address must contain numeric base and channel"
        ) from err

    if not 1 <= base_id <= MAX_BASES:
        raise ValueError(f"zone base must be between 1 and {MAX_BASES}")
    if not 1 <= channel_id <= MAX_ZONES_PER_BASE:
        raise ValueError(
            f"zone channel must be between 1 and {MAX_ZONES_PER_BASE}"
        )

    return base_id, channel_id, name.strip()


def parse_zone_entries(zones: str) -> list[tuple[int, int, str]]:
    """Parse and validate a comma-separated zone configuration."""
    if not isinstance(zones, str) or not zones.strip():
        raise ValueError("at least one zone is required")

    entries = zones.split(",")
    if len(entries) > MAX_ZONES:
        raise ValueError(f"at most {MAX_ZONES} zones are supported")

    parsed_entries = [
        parse_zone_entry(entry, position)
        for position, entry in enumerate(entries)
    ]
    seen_addresses: set[tuple[int, int]] = set()
    for base_id, channel_id, _ in parsed_entries:
        address = (base_id, channel_id)
        if address in seen_addresses:
            raise ValueError(f"duplicate zone address {base_id}.{channel_id}")
        seen_addresses.add(address)

    return parsed_entries
