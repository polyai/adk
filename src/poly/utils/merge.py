"""3-way merge utilities for pulling remote changes over local edits.

Copyright PolyAI Limited
"""

import difflib

_MISSING = object()


def merge_rtc_dicts(base: dict, local: dict, remote: dict) -> tuple[dict, list[str]]:
    """3-way merge at the dict key level.

    Returns:
        (merged_dict, list_of_conflict_keys). If conflict_keys is empty, the
        merge is clean.
    """
    all_keys = set(base) | set(local) | set(remote)
    merged = {}
    conflicts = []

    for key in sorted(all_keys):
        base_val = base.get(key, _MISSING)
        local_val = local.get(key, _MISSING)
        remote_val = remote.get(key, _MISSING)

        resolved = _MISSING
        if local_val == remote_val:
            resolved = local_val
        elif local_val == base_val:
            resolved = remote_val
        elif remote_val == base_val:
            resolved = local_val
        else:
            if (
                isinstance(base_val, dict)
                and isinstance(local_val, dict)
                and isinstance(remote_val, dict)
            ):
                nested_merged, nested_conflicts = merge_rtc_dicts(base_val, local_val, remote_val)
                conflicts.extend([f"{key}.{c}" for c in nested_conflicts])
                resolved = nested_merged
            else:
                conflicts.append(str(key))
                resolved = local_val

        if resolved is not _MISSING:
            merged[key] = resolved

    return merged, conflicts


def merge_strings(original: str, updated: str, incoming: str) -> str:
    """Merge updated and incoming strings with original as base.

    Performs a 3-way merge using difflib. Changes made only in `updated` or
    only in `incoming` are applied cleanly. Conflicting changes (both sides
    modified the same region differently) produce conflict markers.
    """
    base = original.splitlines(keepends=True)
    a = updated.splitlines(keepends=True)
    b = incoming.splitlines(keepends=True)

    result: list[str] = []
    for region in _merge_regions(base, a, b):
        tag = region[0]
        if tag == "unchanged":
            result.extend(base[region[1] : region[2]])
        elif tag in ("a", "same"):
            result.extend(a[region[1] : region[2]])
        elif tag == "b":
            result.extend(b[region[1] : region[2]])
        elif tag == "conflict":
            _, _, _, a_start, a_end, b_start, b_end = region
            result.append("<<<<<<<\n")
            result.extend(a[a_start:a_end])
            if result and not result[-1].endswith("\n"):
                result[-1] += "\n"
            result.append("=======\n")
            result.extend(b[b_start:b_end])
            if result and not result[-1].endswith("\n"):
                result[-1] += "\n"
            result.append(">>>>>>>\n")
    return "".join(result)


def _find_sync_regions(
    matches_a: list[difflib.Match],
    matches_b: list[difflib.Match],
) -> list[tuple[int, int, int, int, int, int]]:
    """Find regions in base that are matched by both a and b.

    Returns (base_start, base_end, a_start, a_end, b_start, b_end) tuples
    representing synchronisation points where all three texts agree.
    """
    regions: list[tuple[int, int, int, int, int, int]] = []
    ia = ib = 0

    while ia < len(matches_a) and ib < len(matches_b):
        base_a_start, a_start, na = matches_a[ia]
        base_b_start, b_start, nb = matches_b[ib]

        base_a_end = base_a_start + na
        base_b_end = base_b_start + nb

        # Intersect the two matching ranges on the base axis
        inter_start = max(base_a_start, base_b_start)
        inter_end = min(base_a_end, base_b_end)

        if inter_start < inter_end:
            a_inter_start = a_start + (inter_start - base_a_start)
            b_inter_start = b_start + (inter_start - base_b_start)
            length = inter_end - inter_start
            regions.append(
                (
                    inter_start,
                    inter_end,
                    a_inter_start,
                    a_inter_start + length,
                    b_inter_start,
                    b_inter_start + length,
                )
            )

        # Advance whichever matching block ends first
        if base_a_end <= base_b_end:
            ia += 1
        if base_b_end <= base_a_end:
            ib += 1

    return regions


def _classify_gap(
    base: list[str],
    base_start: int,
    base_end: int,
    a: list[str],
    a_start: int,
    a_end: int,
    b: list[str],
    b_start: int,
    b_end: int,
):
    """Classify a gap between sync regions as unchanged, one-sided, same, or conflict."""
    base_chunk = base[base_start:base_end]
    a_chunk = a[a_start:a_end]
    b_chunk = b[b_start:b_end]

    if not base_chunk and not a_chunk and not b_chunk:
        return

    if a_chunk == b_chunk:
        # Both sides agree (either both unchanged or both made the same edit)
        if a_chunk == base_chunk:
            yield ("unchanged", base_start, base_end)
        else:
            yield ("same", a_start, a_end)
    elif a_chunk == base_chunk:
        # Only b changed
        yield ("b", b_start, b_end)
    elif b_chunk == base_chunk:
        # Only a changed
        yield ("a", a_start, a_end)
    else:
        # Both changed differently — conflict
        yield ("conflict", base_start, base_end, a_start, a_end, b_start, b_end)


def _merge_regions(base: list[str], a: list[str], b: list[str]):
    """Compute merge regions for a 3-way merge."""
    sync_regions = _find_sync_regions(
        difflib.SequenceMatcher(None, base, a).get_matching_blocks(),
        difflib.SequenceMatcher(None, base, b).get_matching_blocks(),
    )

    base_pos = a_pos = b_pos = 0

    for base_start, base_end, a_start, a_end, b_start, b_end in sync_regions:
        yield from _classify_gap(
            base,
            base_pos,
            base_start,
            a,
            a_pos,
            a_start,
            b,
            b_pos,
            b_start,
        )

        if base_start < base_end:
            yield ("unchanged", base_start, base_end)

        base_pos = base_end
        a_pos = a_end
        b_pos = b_end

    # Trailing content after the last sync region
    yield from _classify_gap(
        base,
        base_pos,
        len(base),
        a,
        a_pos,
        len(a),
        b,
        b_pos,
        len(b),
    )
